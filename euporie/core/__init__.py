"""This package defines the euporie application and its components."""

__app_name__ = "euporie"
__version__ = "2.8.1"
__logo__ = "⚈"
__strapline__ = "Jupyter in the terminal"
__author__ = "Josiah Outram Halstead"
__email__ = "josiah@halstead.email"
__copyright__ = f"© 2024, {__author__}"
__license__ = "MIT"


# Register extensions to external packages
from euporie.core import path  # noqa F401
from euporie.core import pygments  # noqa F401

# Monkey-patch prompt_toolkit
from euporie.core.layout import containers  # noqa: F401
