# -*- coding: utf-8 -*-
##
## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007, 2008 CERN.
##
## CDS Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

""" Error handling library """

__revision__ = "$Id$"

import traceback
import os
import sys
import time
import re
from cStringIO import StringIO

from invenio.config import CFG_SITE_LANG, CFG_LOGDIR, \
    CFG_WEBALERT_ALERT_ENGINE_EMAIL, CFG_SITE_ADMIN_EMAIL, \
    CFG_SITE_SUPPORT_EMAIL, CFG_SITE_NAME, CFG_SITE_URL, CFG_VERSION, \
    CFG_CERN_SITE, CFG_SITE_EMERGENCY_EMAIL_ADDRESSES, \
    CFG_SITE_ADMIN_EMAIL_EXCEPTIONS
from invenio.miscutil_config import CFG_MISCUTIL_ERROR_MESSAGES
from invenio.urlutils import wash_url_argument
from invenio.messages import wash_language, gettext_set_language
from invenio.dateutils import convert_datestruct_to_datetext


## Regular expression to match possible password related variable that should
## be disclosed in frame analysis.
RE_PWD = re.compile(r"pwd|pass", re.I)


def get_client_info(req):
    """
    Returns a dictionary with client information
    @param req: mod_python request
    """
    try:
        return {
            'host': req.hostname,
            'url': req.unparsed_uri,
            'time': convert_datestruct_to_datetext(time.localtime()),
            'browser': 'User-Agent' in req.headers_in and \
                          req.headers_in['User-Agent'] or "N/A",
            'client_ip': req.remote_ip}
    except:
        return {}


def get_pretty_wide_client_info(req):
    """Return in a pretty way all the avilable information about the current
    user/client"""
    if req:
        from invenio.webuser import collect_user_info
        user_info = collect_user_info(req)
        keys = user_info.keys()
        keys.sort()
        max_key = max([len(key) for key in keys])
        ret = ""
        fmt = "%% %is: %%s\n" % max_key
        for key in keys:
            if key in ('uri', 'referer'):
                ret += fmt % (key, "<%s>" % user_info[key])
            else:
                ret += fmt % (key, user_info[key])
        if ret.endswith('\n'):
            return ret[:-1]
        else:
            return ret
    else:
        return "No client information available"


def get_tracestack():
    """
    If an exception has been caught, return the system tracestack or else
    return tracestack of what is currently in the stack
    """
    if traceback.format_tb(sys.exc_info()[2]):
        delimiter = "\n"
        tracestack_pretty = "Traceback: \n%s" % \
            delimiter.join(traceback.format_tb(sys.exc_info()[2]))
    else:
        ## force traceback except for this call
        tracestack = traceback.extract_stack()[:-1]
        tracestack_pretty = "%sForced traceback (most recent call last)" % \
                            (' '*4, )
        for trace_tuple in tracestack:
            tracestack_pretty += """
    File "%(file)s", line %(line)s, in %(function)s
        %(text)s""" % {
            'file': trace_tuple[0],
            'line': trace_tuple[1],
            'function': trace_tuple[2],
            'text': trace_tuple[3] is not None and \
                    str(trace_tuple[3]) or ""}
    return tracestack_pretty

def register_emergency(msg, recipients=None):
    """Launch an emergency. This means to send email messages to each
    address in 'recipients'. By default recipients will be obtained via
    get_emergency_recipients() which loads settings from 
    CFG_SITE_EMERGENCY_EMAIL_ADDRESSES
    """
    from invenio.mailutils import send_email
    if not recipients:
        recipients = get_emergency_recipients()
    for address_str in recipients:
        send_email(CFG_SITE_SUPPORT_EMAIL, address_str, "Emergency notification", msg)

def get_emergency_recipients(recipient_cfg=CFG_SITE_EMERGENCY_EMAIL_ADDRESSES):
    """Parse a list of appropriate emergency email recipients from
    CFG_SITE_EMERGENCY_EMAIL_ADDRESSES, or from a provided dictionary 
    comprised of 'time constraint' => 'comma separated list of addresses' 
    
    CFG format example:
        
    CFG_SITE_ADMIN_EMERGENCY_CONTACTS = {
        '06:00-18:00': 'team-in-europe@foo.com,0041762222222@email2sms.foo.com',
        '18:00-06:00': 'team-in-usa@foo.com',
        'Sunday 22:00-06:00': '0041761111111@email2sms.foo.com'
        }
    """
    from invenio.dateutils import parse_runtime_limit
    
    recipients = set()
    for time_condition, address_str in recipient_cfg.items():
        if time_condition and time_condition is not '*':
            (current_range, future_range) = parse_runtime_limit(time_condition)
            time_now = time.time()
            if not current_range[0] <= time_now <= current_range[1]:
                continue
        recipients.update([address_str])
    return list(recipients)

def find_all_values_to_hide(local_variables, analyzed_stack=None):
    """Return all the potential password to hyde."""
    ## Let's add at least the DB password.
    if analyzed_stack is None:
        from invenio.dbquery import CFG_DATABASE_PASS
        ret = set([CFG_DATABASE_PASS])
        analyzed_stack = set()
    else:
        ret = set()
    for key, value in local_variables.iteritems():
        if id(value) in analyzed_stack:
            ## Let's avoid loops
            continue
        analyzed_stack.add(id(value))
        if RE_PWD.search(key):
            ret.add(str(value))
        if isinstance(value, dict):
            ret |= find_all_values_to_hide(value, analyzed_stack)
    return ret

def get_pretty_traceback(req=None, exc_info=None, force_stack=True):
    """
    Given an optional request object and an optional exc_info,
    returns a text string representing many details about an exception.
    """
    if exc_info is None:
        exc_info = sys.exc_info()
    if exc_info[0]:
        ## We found an exception.

        ## We want to extract the name of the Exception
        exc_name = exc_info[0].__name__
        exc_value = str(exc_info[1])

        ## Let's record when and where and what
        www_data = "%(time)s -> %(name)s: %(value)s" % {
            'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'name': exc_name,
            'value': exc_value}

        ## Let's retrieve contextual user related info, if any
        try:
            client_data = get_pretty_wide_client_info(req)
        except Exception, err:
            client_data = "Error in retrieving " \
                "contextual information: %s" % err

        ## Let's extract the traceback:
        if not exc_name.startswith('Invenio') or force_stack:
            tracestack_data_stream = StringIO()
            tb = sys.exc_info()[2]
            while 1:
                if not tb.tb_next:
                    break
                tb = tb.tb_next
            stack = []
            f = tb.tb_frame
            while f:
                stack.append(f)
                f = f.f_back
            stack.reverse()
            stack = stack[-10:] ## Let's just take the last few frames
            traceback.print_exc(file=tracestack_data_stream)
            print >> tracestack_data_stream, \
                    "Locals by frame, innermost last"
            values_to_hide = set()
            for frame in stack:
                print >> tracestack_data_stream
                print >> tracestack_data_stream, \
                        ">>>> Frame %s in %s at line %s" % (
                            frame.f_code.co_name,
                            frame.f_code.co_filename,
                            frame.f_lineno)
                try:
                    values_to_hide |= find_all_values_to_hide(frame.f_locals)

                    code = open(frame.f_code.co_filename).readlines()
                    first_line = max(1, frame.f_lineno-3)
                    last_line = min(len(code), frame.f_lineno+3)
                    print >> tracestack_data_stream, "*" * 79
                    for line in xrange(first_line, last_line+1):
                        code_line = code[line-1].rstrip()
                        for value in values_to_hide:
                            ## Let's hide passwords
                            code_line = code_line.replace(value, '<*****>')
                        if line == frame.f_lineno:
                            print >> tracestack_data_stream, \
                                "----> %4i %s" % (line, code_line)
                        else:
                            print >> tracestack_data_stream, \
                                "      %4i %s" % (line, code_line)
                    print >> tracestack_data_stream, "*" * 79
                except:
                    pass
                for key, value in frame.f_locals.items():
                    print >> tracestack_data_stream, "\t%20s = " % key,
                    for to_hide in values_to_hide:
                        ## Let's hide passwords
                        value = repr(value).replace(to_hide, '<*****>')
                    try:
                        print >> tracestack_data_stream, \
                            _truncate_dynamic_string(value)
                    except:
                        print >> tracestack_data_stream, \
                            "<ERROR WHILE PRINTING VALUE>"
            tracestack_data = tracestack_data_stream.getvalue()
        else:
            tracestack_data = ''

        ## Okay, start printing:
        output = StringIO()

        print >> output, '\n',

        print >> output, "The following problem occurred on <%s>" \
            " (CDS Invenio %s)" % (CFG_SITE_URL, CFG_VERSION)
        print >> output, "\n>> %s" % www_data
        print >> output, "\n>>> User details\n"
        print >> output, client_data

        if tracestack_data:
            print >> output, "\n>>> Traceback details\n"
            print >> output, tracestack_data
        return output.getvalue()
    else:
        return ""


def register_exception(force_stack=False,
                       stream='error',
                       req=None,
                       prefix='',
                       suffix='',
                       alert_admin=False,
                       subject=''):
    """
    Log error exception to invenio.err and warning exception to invenio.log.
    Errors will be logged together with client information (if req is
    given).

    Note:   For sanity reasons, dynamic params such as PREFIX, SUFFIX and
            local stack variables are checked for length, and only first 500
            chars of their values are printed.

    @param force_stack: when True stack is always printed, while when False,
    stack is printed only whenever the Exception type is not containing the
    word Invenio

    @param stream: 'error' or 'warning'

    @param req: mod_python request

    @param prefix: a message to be printed before the exception in
    the log

    @param suffix: a message to be printed before the exception in
    the log

    @param alert_admin: wethever to send the exception to the administrator via
        email. Note this parameter is bypassed when
                CFG_SITE_ADMIN_EMAIL_EXCEPTIONS is set to a value different than 1
    @param subject: overrides the email subject

    @return: 1 if successfully wrote to stream, 0 if not
    """


    try:
        ## Let's extract exception information
        exc_info = sys.exc_info()
        output = get_pretty_traceback(
            req=req, exc_info=exc_info, force_stack=force_stack)
        if output:
            ## Okay, start printing:
            log_stream = StringIO()
            email_stream = StringIO()

            print >> email_stream, '\n',

            ## If a prefix was requested let's print it
            if prefix:
                prefix = _truncate_dynamic_string(prefix)
                print >> log_stream, prefix + '\n'
                print >> email_stream, prefix + '\n'

            print >> log_stream, output
            print >> email_stream, output

            ## If a suffix was requested let's print it
            if suffix:
                suffix = _truncate_dynamic_string(suffix)
                print >> log_stream, suffix
                print >> email_stream, suffix

            log_text = log_stream.getvalue()
            email_text = email_stream.getvalue()

            if email_text.endswith('\n'):
                email_text = email_text[:-1]

            ## Preparing the exception dump
            stream = stream=='error' and 'err' or 'log'

            ## We now have the whole trace
            written_to_log = False
            try:
                ## Let's try to write into the log.
                open(os.path.join(CFG_LOGDIR, 'invenio.' + stream), 'a').write(
                    log_text)
                written_to_log = True
            except:
                written_to_log = False

            if CFG_SITE_ADMIN_EMAIL_EXCEPTIONS > 1 or \
                (alert_admin and CFG_SITE_ADMIN_EMAIL_EXCEPTIONS > 0) or \
                not written_to_log:
                ## If requested or if it's impossible to write in the log
                from invenio.mailutils import send_email
                if not subject:
                    filename, line_no, function_name = _get_filename_and_line(exc_info)
                    subject = 'Exception (%s:%s:%s)' % (filename, line_no, function_name)
                subject = '%s at %s' % (subject, CFG_SITE_URL)
                if not written_to_log:
                        email_text += """\
Note that this email was sent to you because it has been impossible to log
this exception into %s""" % os.path.join(CFG_LOGDIR, 'invenio.' + stream)
                send_email(
                    CFG_SITE_ADMIN_EMAIL,
                    CFG_SITE_ADMIN_EMAIL,
                    subject=subject,
                    content=email_text)
            return 1
        else:
            return 0
    except Exception, err:
        print >> sys.stderr, "Error in registering exception to '%s': '%s'" % (
            CFG_LOGDIR + '/invenio.' + stream, err)
        return 0


def register_errors(errors_or_warnings_list, stream, req=None):
    """
    log errors to invenio.err and warnings to invenio.log
    errors will be logged with client information (if req is given) and a
    tracestack warnings will be logged with just the warning message

    @param errors_or_warnings_list: list of tuples (err_name, err_msg)

    err_name = ERR_ + %(module_directory_name)s + _ + %(error_name)s #ALL CAPS
    err_name must be stored in file:  module_directory_name + _config.py
    as the key for dict with name:  CFG_ + %(module_directory_name)s +
        _ERROR_MESSAGES

    @param stream: 'error' or 'warning'

    @param req: mod_python request
    @return: tuple integer 1 if successfully wrote to stream, integer 0 if not
            will append another error to errors_list if unsuccessful
    """
    client_info_dict = ""
    if stream == "error":
        # call the stack trace now
        tracestack_pretty = get_tracestack()
        # if req is given, get client info
        if req:
            client_info_dict = get_client_info(req)
            if client_info_dict:
                client_info = \
'''URL: http://%(host)s%(url)s
    Browser: %(browser)s
    Client: %(client_ip)s''' % client_info_dict
            else:
                client_info = "No client information available"
        else:
            client_info = "No client information available"
    # check arguments
    errors_or_warnings_list = wash_url_argument(
        errors_or_warnings_list, 'list')
    stream = wash_url_argument(stream, 'str')
    for etuple in errors_or_warnings_list:
        etuple = wash_url_argument(etuple, 'tuple')
    # check stream arg for presence of [error,warning]; when none, add error
    # and default to warning
    if stream == 'error':
        stream = 'err'
    elif stream == 'warning':
        stream = 'log'
    else:
        stream = 'log'
        error = 'ERR_MISCUTIL_BAD_FILE_ARGUMENT_PASSED'
        errors_or_warnings_list.append(
            (error, eval(CFG_MISCUTIL_ERROR_MESSAGES[error])% stream))
    # update log_errors
    stream_location = os.path.join(CFG_LOGDIR, 'invenio.' + stream)
    errors = ''
    for etuple in errors_or_warnings_list:
        try:
            errors += "%s%s : %s \n " % (' '*4*7+' ', etuple[0], etuple[1])
        except:
            errors += "%s%s \n " % (' '*4*7+' ', etuple)
    if errors:
        errors = errors[(4*7+1):-3] # get rid of begining spaces and last '\n'
    msg = """
%(time)s --> %(errors)s%(error_file)s""" % {
        'time': client_info_dict and client_info_dict['time'] or \
                time.strftime("%Y-%m-%d %H:%M:%S"),
        'errors': errors,
        'error_file': stream=='err' and "\n%s%s\n%s\n" % (
            ' '*4, client_info, tracestack_pretty) or ""}
    try:
        stream_to_write = open(stream_location, 'a+')
        stream_to_write.writelines(msg)
        stream_to_write.close()
        return_value = 1
    except:
        error = 'ERR_MISCUTIL_WRITE_FAILED'
        errors_or_warnings_list.append(
            (error, CFG_MISCUTIL_ERROR_MESSAGES[error] % stream_location))
        return_value = 0
    return return_value


def get_msg_associated_to_code(err_code, stream='error'):
    """
    Returns string of code
    @param err_code: error or warning code
    @type err_code: string
    @param stream: 'error' or 'warning'
    @type stream: string
    @return: (err_code, formatted_message)
    @rtype: tuple
    """
    err_code = wash_url_argument(err_code, 'str')
    stream = wash_url_argument(stream, 'str')
    try:
        module_directory_name = err_code.split('_')[1].lower()
        module_config = module_directory_name + '_config'
        module_dict_name = "CFG_" + module_directory_name.upper() + \
                           "_%s_MESSAGES" % stream.upper()
        module = __import__(
            module_config, globals(), locals(), [module_dict_name])
        module_dict = getattr(module, module_dict_name)
        err_msg = module_dict[err_code]
    except ImportError:
        error = 'ERR_MISCUTIL_IMPORT_ERROR'
        err_msg = CFG_MISCUTIL_ERROR_MESSAGES[error] % (err_code,
                                                        module_config)
        err_code = error
    except AttributeError:
        error = 'ERR_MISCUTIL_NO_DICT'
        err_msg = CFG_MISCUTIL_ERROR_MESSAGES[error] % (err_code,
                                                        module_config,
                                                        module_dict_name)
        err_code = error
    except KeyError:
        error = 'ERR_MISCUTIL_NO_MESSAGE_IN_DICT'
        err_msg = CFG_MISCUTIL_ERROR_MESSAGES[error] % (err_code,
                  module_config + '.' + module_dict_name)
        err_code = error
    except:
        error = 'ERR_MISCUTIL_UNDEFINED_ERROR'
        err_msg = CFG_MISCUTIL_ERROR_MESSAGES[error] % err_code
        err_code = error
    return (err_code, err_msg)


def get_msgs_for_code_list(code_list, stream='error', ln=CFG_SITE_LANG):
    """
    @param code_list: list of tuples  [(err_name, arg1, ..., argN), ...]

    err_name = ERR_ + %(module_directory_name)s + _ + %(error_name)s #ALL CAPS
    err_name must be stored in file:  module_directory_name + _config.py
    as the key for dict with name:  CFG_ + %(module_directory_name)s +
    _ERROR_MESSAGES
    For warnings, same thing except:
        err_name can begin with either 'ERR' or 'WRN'
        dict name ends with _warning_messages

    @param stream: 'error' or 'warning'

    @return: list of tuples of length 2 [('ERR_...', err_msg), ...]
        if code_list empty, will return None.
        if errors retrieving error messages, will append an error to the list
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    out = []
    if type(code_list) is None:
        return None
    code_list = wash_url_argument(code_list, 'list')
    stream = wash_url_argument(stream, 'str')
    for code_tuple in code_list:
        if not(type(code_tuple) is tuple):
            code_tuple = (code_tuple, )
        nb_tuple_args = len(code_tuple) - 1
        err_code = code_tuple[0]
        if stream == 'error' and not err_code.startswith('ERR'):
            error = 'ERR_MISCUTIL_NO_ERROR_MESSAGE'
            out.append((error, eval(CFG_MISCUTIL_ERROR_MESSAGES[error])))
            continue
        elif stream == 'warning' and not (err_code.startswith('ERR') or \
                err_code.startswith('WRN')):
            error = 'ERR_MISCUTIL_NO_WARNING_MESSAGE'
            out.append((error, eval(CFG_MISCUTIL_ERROR_MESSAGES[error])))
            continue
        (new_err_code, err_msg) = get_msg_associated_to_code(err_code, stream)
        if err_msg[:2] == '_(' and err_msg[-1] == ')':
            # err_msg is internationalized
            err_msg = eval(err_msg)
        nb_msg_args = err_msg.count('%') - err_msg.count('%%')
        parsing_error = ""
        if new_err_code != err_code or nb_msg_args == 0:
            # undefined_error or immediately displayable error
            out.append((new_err_code, err_msg))
            continue
        try:
            if nb_msg_args == nb_tuple_args:
                err_msg = err_msg % code_tuple[1:]
            elif nb_msg_args < nb_tuple_args:
                err_msg = err_msg % code_tuple[1:nb_msg_args+1]
                parsing_error = 'ERR_MISCUTIL_TOO_MANY_ARGUMENT'
                parsing_error_message = eval(
                    CFG_MISCUTIL_ERROR_MESSAGES[parsing_error])
                parsing_error_message %= code_tuple[0]
            elif nb_msg_args > nb_tuple_args:
                code_tuple = list(code_tuple)
                for dummy in range(nb_msg_args - nb_tuple_args):
                    code_tuple.append('???')
                    code_tuple = tuple(code_tuple)
                err_msg = err_msg % code_tuple[1:]
                parsing_error = 'ERR_MISCUTIL_TOO_FEW_ARGUMENT'
                parsing_error_message = eval(
                    CFG_MISCUTIL_ERROR_MESSAGES[parsing_error])
                parsing_error_message %= code_tuple[0]
        except:
            parsing_error = 'ERR_MISCUTIL_BAD_ARGUMENT_TYPE'
            parsing_error_message = eval(
                CFG_MISCUTIL_ERROR_MESSAGES[parsing_error])
            parsing_error_message %= code_tuple[0]
        out.append((err_code, err_msg))
        if parsing_error:
            out.append((parsing_error, parsing_error_message))
    if not(out):
        out = None
    return out

def send_error_report_to_admin(header, url, time_msg,
                               browser, client, error,
                               sys_error, traceback_msg):
    """
    Sends an email to the admin with client info and tracestack
    """
    from_addr = '%s Alert Engine <%s>' % (
        CFG_SITE_NAME, CFG_WEBALERT_ALERT_ENGINE_EMAIL)
    to_addr = CFG_SITE_ADMIN_EMAIL
    body = """
The following error was seen by a user and sent to you.
%(contact)s

%(header)s

%(url)s
%(time)s
%(browser)s
%(client)s
%(error)s
%(sys_error)s
%(traceback)s

Please see the %(logdir)s/invenio.err for traceback details.""" % {
        'header': header,
        'url': url,
        'time': time_msg,
        'browser': browser,
        'client': client,
        'error': error,
        'sys_error': sys_error,
        'traceback': traceback_msg,
        'logdir': CFG_LOGDIR,
        'contact': "Please contact %s quoting the following information:" %
            (CFG_SITE_SUPPORT_EMAIL, )}
    from invenio.mailutils import send_email
    send_email(from_addr, to_addr, subject="Error notification", content=body)

def _get_filename_and_line(exc_info):
    """
    Return the filename, the line and the function_name where the exception happened.
    """
    tb = exc_info[2]
    exception_info = traceback.extract_tb(tb)[-1]
    filename = os.path.basename(exception_info[0])
    line_no = exception_info[1]
    function_name = exception_info[2]
    return filename, line_no, function_name

def _truncate_dynamic_string(val, maxlength=500):
    """
    Return at most MAXLENGTH characters of VAL.  Useful for
    sanitizing dynamic variable values in the output.
    """
    out = repr(val)
    if len(out) > maxlength:
        out = out[:maxlength] + ' [...]'
    return out
