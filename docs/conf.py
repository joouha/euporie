"""Configuration file for the Sphinx documentation builder."""

# Project information

project = "euporie"
copyright = "2022, Josiah Outram Halstead"
author = "Josiah Outram Halstead"

# General configuration

extensions: "list[str]" = [
    "sphinx.ext.intersphinx",  # Link to other packages
    "sphinx.ext.napoleon",  # Enable google-style docstring parsing
    "sphinx.ext.autodoc",  # Document modules
    "sphinx.ext.autosummary",  # Generate API documentation
    "sphinx_argparse_cli",  # Command line argument documentation
    "sphinxext.opengraph",  # OGP data
    "sphinx_copybutton",  # Copy button
]
templates_path = ["_templates"]
exclude_patterns: "list[str]" = []


# Options for HTML output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_favicon = "_static/favicon.ico"
html_logo = "_static/logo.svg"
html_css_files = ["custom.css"]
html_theme_options = {
    "style_nav_header_background": "#1a1c1e",
}

pygments_style = "native"

# Autosummary options
autosummary_generate = True

# Intersphinx options

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "prompt_toolkit": ("https://python-prompt-toolkit.readthedocs.io/en/master/", None),
    "rich": ("https://rich.readthedocs.io/en/stable/", None),
    "commonmark": ("https://commonmarkpy.readthedocs.io/en/latest/", None),
    "sympy": ("https://docs.sympy.org/latest/", None),
}

# "https://github.com/jb-leger/flatlatex"
#  <https://github.com/phfaist/pylatexenc/>`_
#  <https://github.com/liuyug/mtable>`_
# cairosvg <https://www.courtbouillon.org/cairosvg>`_
#  <https://github.com/adzierzanowski/timg>`_
#  <https://github.com/ar90n/teimpy>`_
#  <https://github.com/davidbrochart/akernel
