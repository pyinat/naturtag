"""Config file for Sphinx documentation"""
from importlib.metadata import version as pkg_version
from pathlib import Path

STATIC_DIR = Path('_static')

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
    'sphinx_design',
    'sphinxcontrib.apidoc',
    'myst_parser',
]

# MyST extensions
myst_enable_extensions = ['colon_fence', 'html_image', 'linkify', 'substitution']

# Ignore a subset of auto-generated pages
exclude_patterns = [
    'modules/modules.rst',
    'modules/naturtag.rst',
    'modules/naturtag.constants.rst',
    'modules/naturtag.utils.rst',
]

# Replace '{{version}}' in md files with current version
myst_substitutions = {'version': f'v{version}'}

# Enable automatic links to other projects' Sphinx docs
intersphinx_mapping = {
    'click': ('https://click.palletsprojects.com/en/latest/', None),
    'pillow': ('https://pillow.readthedocs.io/en/stable', None),
    'pyinaturalist': ('https://pyinaturalist.readthedocs.io/en/stable/', None),
    'pyinaturalist_convert': ('https://pyinaturalist-convert.readthedocs.io/en/latest/', None),
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

# Strip prompt text when copying code blocks with copy button
copybutton_prompt_text = r'>>> |\.\.\. |\$ '
copybutton_prompt_is_regexp = True

# Generate labels in the format <page>:<section>
autosectionlabel_prefix_document = True

# HTML general settings
html_static_path = [str(STATIC_DIR)]
html_favicon = str(STATIC_DIR / 'favicon.ico')
html_logo = str(STATIC_DIR / 'logo.png')
html_css_files = ['https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/css/all.min.css']
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
