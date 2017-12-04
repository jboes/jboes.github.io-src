#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Jacob Boes'
SITENAME = u"Boes' Blog"
SITEURL = ''

PATH = 'content'
# static paths will be copied without parsing their contents
STATIC_PATHS = ['pdfs', 'images', 'scripts']

ARTICLE_PATHS = ['blog']
PAGE_PATHS = ['pages']
ARTICLE_SAVE_AS = '{date:%Y}/{slug}.html'
ARTICLE_URL = '{date:%Y}/{slug}.html'
USE_FOLDER_AS_CATEGORY = True
DEFAULT_CATEGORY = 'Blog'
DEFAULT_DATE = 'fs'

THEME = 'notmyidea'
THEME_STATIC_DIR = 'theme'
SITESUBTITLE = 'Exploration through coding, catalysis, and education'
GITHUB_URL = 'https://github.com/jboes'
GOOGLE_ANALYTICS = 'UA-XXXX-YYYY'

ORG_READER_EMACS_LOCATION = '/usr/bin/emacs'

TIMEZONE = 'US/Pacific'
DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('ORCID', 'https://orcid.org/0000-0002-7303-7782'),)

# Social widget
SOCIAL = (('GitHub', 'https://github.com/jboes'),
          ('Twitter', 'https://twitter.com/jacob_boes'),
          ('Linkedin', 'https://www.linkedin.com/in/jacobboes'),)

PLUGIN_PATHS = ['./pelican-plugins']
PLUGINS = ['org_reader']

DEFAULT_PAGINATION = 10

# Display pages list on the top menu
DISPLAY_PAGES_ON_MENU = True

# Display categories list on the top menu
DISPLAY_CATEGORIES_ON_MENU = False

# Display categories list as a submenu of the top menu
DISPLAY_CATEGORIES_ON_SUBMENU = False

# Display the category in the article's info
DISPLAY_CATEGORIES_ON_POSTINFO = False

# Display the author in the article's info
DISPLAY_AUTHOR_ON_POSTINFO = False

# Display the search form
DISPLAY_SEARCH_FORM = False

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True
