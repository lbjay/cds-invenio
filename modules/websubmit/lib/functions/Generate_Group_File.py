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


from invenio.errorlib import register_exception
from invenio.websubmit_config import InvenioWebSubmitFunctionError

CFG_WEBSUBMIT_GROUP_FILE_NAME = "Group"

def Generate_Group_File(parameters, curdir, form, user_info=None):
    """
    Generates a group file (stored in 'curdir/Group') for use with
    publiline.

    @param parameters: (dictionary) - must contain:
                      + group_name: (string) - the id of the Group for
                      use in the complex approval refereeing workflow

    @param curdir: (string) - the current submission's working
    directory.

    @param form: (dictionary) - form fields.

    @param user_info: (dictionary) - various information about the
                                     submitting user (includes the
                                     apache req object).

    @return: (string) - empty string.

    @Exceptions raised: InvenioWebSubmitFunctionError when an
                        unexpected error is encountered.
    """
    try:
        group_file = open("%s/%s" % (curdir, CFG_WEBSUBMIT_GROUP_FILE_NAME), "w")
        group_file.write(parameters['group_name'])
        group_file.flush()
        group_file.close()
    except IOError, err:
        ## Unable to write the Group file to curdir.
        err_msg = "Error: Unable to create Group file [%s/%s]. " \
          "Perhaps check directory permissions. " \
          % (curdir, CFG_WEBSUBMIT_GROUP_FILE_NAME)
        register_exception(req=req_obj, prefix=err_msg)
        raise InvenioWebSubmitFunctionError(err_msg)
    ## Return an empty string:
    return ""

