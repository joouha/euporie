"""This package defines the euporie application and its components."""

__app_name__ = "euporie"
__version__ = "2.0.0-dev"
__logo__ = "⚈"
__strapline__ = "A TUI editor for Jupyter notebooks"
__author__ = "Josiah Outram Halstead"
__email__ = "josiah@halstead.email"
__copyright__ = f"© 2022, {__author__}"
__license__ = "MIT"


from euporie.renderer import patch_renderer

# Patch the prompt toolkit renderer
patch_renderer()
