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

"""WebDoc module unit tests."""

__revision__ = "$Id$"

import unittest

from invenio.config import CFG_SITE_LANG, \
                           CFG_SITE_LANGS, \
                           CFG_SITE_URL
from invenio.messages import gettext_set_language
from invenio.testutils import make_test_suite, \
                              run_test_suite
from invenio.webdoc import transform

if 'en' in CFG_SITE_LANGS:
    lang_english_configured = True
else:
    lang_english_configured = False

if 'de' in CFG_SITE_LANGS:
    lang_german_configured = True
else:
    lang_german_configured = False

if 'fr' in CFG_SITE_LANGS:
    lang_french_configured = True
else:
    lang_french_configured = False

class WebDocLanguageTest(unittest.TestCase):
    """Check that WebDoc correctly supports <lang> translation
       directives and _()_ syntax"""

    if lang_english_configured and lang_german_configured:
        def test_language_filtering(self):
            """webdoc - language filtering"""
            result = transform('''
            <strong>
            <lang>
                <python>{}</python>
                <en><red>Book</red></en>
                <fr><yellow>Livre</yellow></fr>
                <de><blue>Buch</blue></de>
            </lang>
            </strong>
            ''', languages=['de'])

            # German is kept
            self.assertEqual(result[0][0], 'de')
            self.assert_('<blue>Buch</blue>' in result[0][1])

            # English and French must be filtered out in any case
            self.assert_('Livre' not in result[0][1])
            self.assert_('Book' not in result[0][1])

            # Python is not considered as a language, so the string is
            # kept as it is
            self.assert_('<python>{}</python' in result[0][1])

    if lang_english_configured:
        def test_string_translation(self):
            """webdoc - string translation"""
            result = transform('my_string: _(Search)_ (end)',
                               languages=[CFG_SITE_LANG])
            _ = gettext_set_language(CFG_SITE_LANG)
            self.assertEqual(result[0][1],
                             'my_string: %s (end)' % _("Search"))

class WebDocPartsTest(unittest.TestCase):
    """Check that WebDoc correctly returns values for the different
       parts of webdoc files"""

    if lang_english_configured:
        def test_parts(self):
            """webdoc - retrieving parts of webdoc file (title, navtrail, etc)"""
            _ = gettext_set_language(CFG_SITE_LANG)

            result = transform('''
            <!-- WebDoc-Page-Title: _(Help Central)_  -->
            <!-- WebDoc-Page-Navtrail: <a class="navtrail" href="<CFG_SITE_URL>/help/hacking">Hacking CDS Invenio</a> &gt; <a class="navtrail" href="webstyle-internals">WebStyle Internals</a> -->
            <!-- WebDoc-Page-Revision: $Id: help-central.webdoc,v 1.5 2008/05/26 12:52:41 jerome Exp $ -->
            <!-- WebDoc-Page-Description: A description -->''',
                               languages=[CFG_SITE_LANG])

            # Title
            self.assertEqual(result[0][2], _("Help Central"))

            # Keywords. None in our sample
            self.assertEqual(result[0][3], None)

            # Navtrail
            self.assertEqual(result[0][4], '<a class="navtrail" href="%s/help/hacking">Hacking CDS Invenio</a> &gt; <a class="navtrail" href="webstyle-internals">WebStyle Internals</a>' % CFG_SITE_URL)

            # Revision. Keep date & time only
            self.assertEqual(result[0][5], '2008-05-26 12:52:41')

            # Description
            self.assertEqual(result[0][6], 'A description')

class WebDocVariableReplacementTest(unittest.TestCase):
    """Check that WebDoc correctly replaces variables with their
       values"""

    if lang_english_configured:
        def test_CFG_SITE_URL_variable_replacement(self):
            """webdoc - replacing <CFG_SITE_URL> in webdoc files"""
            result = transform('<CFG_SITE_URL>', languages=[CFG_SITE_LANG])
            self.assertEqual(result[0][1], CFG_SITE_URL)

    if lang_english_configured and lang_french_configured:
        def test_language_tags_replacement(self):
            """webdoc - replacing <lang:link /> and <lang:current /> in
            webdoc files"""
            result = transform('<lang:current />', languages=[CFG_SITE_LANG])
            self.assertEqual(result[0][1], CFG_SITE_LANG)

            # ?ln=.. is returned only if not CFG_SITE_LANG
            result = transform('<lang:link />', languages=[CFG_SITE_LANG])
            self.assertEqual(result[0][1], '')

            result = transform('<lang:link />', languages=['fr'])
            self.assertEqual(result[0][1], '?ln=fr')

class WebDocCommentsFiltering(unittest.TestCase):
    """Check that comments are correctly removed from webdoc files"""

    if lang_english_configured:
        def test_comments_filtering(self):
            """webdoc - removing comments"""
            result = transform('''# -*- coding: utf-8 -*-
    ## $Id$
    ##''',
                               languages=[CFG_SITE_LANG])

            self.assertEqual(result[0][1], '')

TEST_SUITE = make_test_suite(WebDocLanguageTest,
                             WebDocPartsTest,
                             WebDocVariableReplacementTest,
                             WebDocCommentsFiltering,)

if __name__ == "__main__":
    run_test_suite(TEST_SUITE)
