# Configuration file for the Sphinx documentation builder.

# -- Custom settings
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))

html_show_sourcelink = False


# -- Project information
project = 'geolayer'
copyright = 'Copyright © European Union 2024'
author = 'Davide De Marchi'

release = '0.0.4'
version = '0.0.4'


# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx_copybutton',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']


# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    'logo_only': True,
    
}

html_logo = 'figures/geolayer_white_400.png'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

numfig = True

# -- Options for EPUB output
epub_show_urls = 'footnote'
