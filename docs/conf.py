"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from intersphinx_registry import get_intersphinx_mapping

# # Add the docs folder to the path for local extensions
sys.path.append(str(Path(__file__).parent.absolute()))

# Project information
project = "euporie"
copyright = "2022, Josiah Outram Halstead"
author = "Josiah Outram Halstead"

# General configuration
extensions: list[str] = [
    # Link to other packages
    "sphinx.ext.intersphinx",
    # Enable google-style docstring parsing
    "sphinx.ext.napoleon",
    # Document modules
    "sphinx.ext.autodoc",
    # Generate API documentation
    "sphinx.ext.autosummary",
    # Automatically label sections
    "sphinx.ext.autosectionlabel",
    # Command line argument documentation
    "sphinx_argparse_cli",
    # OGP data
    "sphinxext.opengraph",
    # Copy button
    "sphinx_copybutton",
    # Used for image grids
    "sphinx_design",
    # Video embedding
    "_extensions.video",
]
templates_path = ["_templates"]
exclude_patterns: list[str] = []

# Make sure the target is unique
autosectionlabel_prefix_document = True

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

# Options for LaTeX output
latex_engine = "lualatex"

# Autosummary options
autosummary_generate = True
autosummary_imported_members = True

# Intersphinx options
intersphinx_mapping = intersphinx_mapping = get_intersphinx_mapping(
    packages={"python", "prompt_toolkit", "sympy", "rich", "commonmark"}
)

# Run scripts to generate rst includes
docs_dir = Path(__file__).parent
inc_dir = docs_dir / "_inc"
script_dir = docs_dir.parent / "scripts"
inc_dir.mkdir(exist_ok=True)
for script in script_dir.glob("document_*.py"):
    name = script.stem.replace("document_", "")
    with (inc_dir / name).with_suffix(".rst").open("w") as f:
        subprocess.call([sys.executable, script], stdout=f)
