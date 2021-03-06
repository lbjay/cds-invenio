# -*- coding: utf-8 -*-
## $Id: bfe_webjournal_widget_forTheEyes.py,v 1.7 2008/06/03 10:04:16 jerome Exp $
##
## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 CERN.
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
"""
WebJournal widget - List the featured records
"""
from invenio.bibformat_engine import BibFormatObject
from invenio.config import CFG_SITE_URL
from invenio.webjournal_utils import \
     parse_url_string, \
     get_featured_records

def format(bfo):
    """
    List the 'featured' records
    """
    args = parse_url_string(bfo.user_info['uri'])
    journal_name = args["journal_name"]
    featured_records = get_featured_records(journal_name)
    lines = []
    for (recid, img_url) in featured_records:
        featured_record = BibFormatObject(recid)
        if bfo.lang == 'fr':
            title = featured_record.field('246_1a')
            if title == '':
                # No French translation, get it in English
                title = featured_record.field('245__a')
        else:
            title = featured_record.field('245__a')

        lines.append('''
        <a href="%s/record/%s?ln=%s" style="display:block">
            <img src="%s" alt="" width="100" class="phr" />
            %s
        </a>
        ''' % (CFG_SITE_URL, recid, bfo.lang, img_url, title))

    return  '<br/><br/>'.join(lines)

def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0
