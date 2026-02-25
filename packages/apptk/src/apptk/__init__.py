"""Shim package extending apptk."""

from modshim import shim

__version__ = "3.0.0-dev"

shim("prompt_toolkit", extras=["ptterm"])
