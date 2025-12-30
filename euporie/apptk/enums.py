"""Various commonly used enums."""

from __future__ import annotations

from enum import Enum


class EditingMode(Enum):
    """The set of key bindings that is active."""

    VI = "VI"
    EMACS = "EMACS"
    MICRO = "MICRO"


class HorizontalAlign(Enum):
    """Horizontal alignment."""

    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"


class VerticalAlign(Enum):
    """Vertical alignment."""

    TOP = "top"
    MIDDLE = "middle"
    CENTER = "middle"
    BOTTOM = "bottom"
    JUSTIFY = "justify"
