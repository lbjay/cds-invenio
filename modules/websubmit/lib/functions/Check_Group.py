## $Id$

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

__revision__ = "$Id$"

   ## Description:   function Update_Approval_DB
   ##                This function updates the approval database with the
   ##             decision of the referee
   ## Author:         T.Baron
   ## PARAMETERS:    categformatDAM: variable used to compute the category
   ##                                of the document from its reference

import os
import re
import time

from invenio.dbquery import run_sql
from invenio.websubmit_config import InvenioWebSubmitFunctionStop

def Check_Group(parameters,curdir,form):
    #Path of file containing group
    if os.path.exists("%s/%s" % (curdir,'Group')):
        fp = open("%s/%s" % (curdir,'Group'),"r")
        group = fp.read()
        group = group.replace("/","_")
        group = re.sub("[\n\r]+","",group)
        res = run_sql ("""SELECT id FROM usergroup WHERE name = %s""", (group,))
        if len(res) == 0:
            raise InvenioWebSubmitFunctionStop("""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   document.forms[0].submit();
   alert('The given group name (%s) is invalid.');
</SCRIPT>""" % (group,))
    else:
        raise InvenioWebSubmitFunctionStop("""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   document.forms[0].submit();
   alert('The given group name (%s) is invalid.');
</SCRIPT>""" % (group,))

    return ""