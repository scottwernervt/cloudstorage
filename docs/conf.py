#!/usr/bin/env python3
import os

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
]

pygments_style = 'trac'
templates_path = ['.']
source_suffix = '.rst'
master_doc = 'index'

project = 'Cloud Storage'
copyright = 'Copyright 2017-2018 Scott Werner'
author = 'Scott Werner'
version = release = '0.9.0'

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = 'sphinx_rtd_theme'

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_short_title = '%s-%s' % (project, version)
html_theme_options = {
    'collapse_navigation': False,
    'display_version': True,
    'navigation_depth': 4,
}

# Extensions
autodoc_member_order = 'groupwise'
intersphinx_mapping = {
    'python': ('http://python.readthedocs.io/en/latest/', None),
}
todo_include_todos = True
