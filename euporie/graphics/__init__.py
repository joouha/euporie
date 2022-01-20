"""Defines the terminal graphics display system for euporie."""

from euporie.graphics.base import TerminalGraphic, TerminalGraphicsRenderer
from euporie.graphics.kitty import KittyTerminalGraphic
from euporie.graphics.sixel import SixelTerminalGraphic

__all__ = [
    "TerminalGraphicsRenderer",
    "TerminalGraphic",
    "SixelTerminalGraphic",
    "KittyTerminalGraphic",
]
