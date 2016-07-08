#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pelican configuration for ymir docs
#
from __future__ import unicode_literals
import os

AUTHOR = u'mvr'
SITENAME = u'ymir'
SITEURL = 'https://mattvonrocketstein.github.io/ymir'

PATH = os.path.join(os.path.dirname(__file__), 'content')

TIMEZONE = 'America/New_York'
THEME = "theme"
# STATIC_PATHS = ["images",'js']
DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
DISPLAY_PAGES_ON_MENU = True
MD_EXTENSIONS = [
    'codehilite(css_class=highlight)',
    'admonition',
    'tables', 'toc',
]
PLUGIN_PATHS = ["."]
PLUGINS = ['extract_toc', 'simple_footnotes']

LINKS = (
    ('Source code', 'https://github.com/mattvonrocketstein/ymir/'),
    ('Issues', 'https://github.com/mattvonrocketstein/ymir/issues'),
)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)
IGNORE_FILES = ['.#*']
DEFAULT_PAGINATION = False

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True
LOAD_CONTENT_CACHE = False
