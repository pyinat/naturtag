"""Config file for Sphinx documentation"""
from importlib.metadata import version as pkg_version
from pathlib import Path

ASSETS_DIR = Path('_static')

# Basic config
project = 'Naturtag'
copyright = '2022, Jordan Cook'
author = 'Jordan Cook'
html_static_path = ['_static']
templates_path = ['_templates']
version = release = pkg_version('naturtag')

# Sphinx extension modules
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton',
    'sphinx_inline_tabs',
    'sphinx_panels',
    'sphinxcontrib.apidoc',
    'myst_parser',
]

# MyST extensions
myst_enable_extensions = ['colon_fence', 'html_image', 'linkify']

intersphinx_mapping = {
    'click': ('https://click.palletsprojects.com/en/latest/', None),
    'kivy': ('https://kivy.org/doc/stable', None),
    'kivymd': ('https://kivymd.readthedocs.io/en/latest', None),
    'pillow': ('https://pillow.readthedocs.io/en/stable', None),
    'pyinaturalist': ('https://pyinaturalist.readthedocs.io/en/latest/', None),
}
intersphinx_timeout = 30

# Use apidoc to auto-generate rst sources
apidoc_module_dir = '../naturtag'
apidoc_output_dir = 'modules'
apidoc_module_first = True
apidoc_separate_modules = True

# Enable Google-style docstrings
napoleon_google_docstring = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_param = True

# HTML general settings
html_static_path = [str(ASSETS_DIR)]
html_favicon = str(ASSETS_DIR / 'favicon.ico')
html_logo = str(ASSETS_DIR / 'logo.png')
html_css_files = [
    'https://use.fontawesome.com/releases/v5.15.3/css/all.css',
    'https://use.fontawesome.com/releases/v5.15.3/css/v4-shims.css',
]
html_show_sphinx = False
pygments_style = 'friendly'
pygments_dark_style = 'material'

# HTML theme settings
html_theme = 'furo'
html_theme_options = {
    'light_css_variables': {
        'color-brand-primary': '#00766c',
        'color-brand-content': '#006db3',
    },
    'dark_css_variables': {
        'color-brand-primary': '#64d8cb',
        'color-brand-content': '#63ccff',
    },
    'sidebar_hide_name': True,
}
