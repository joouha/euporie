"""Various commonly used enums."""

from __future__ import annotations

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        """String enum for Python < 3.11 compatibility."""


class EditingMode(Enum):
    """The set of key bindings that is active."""

    VI = "VI"
    HELIX = "HELIX"
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


class FitMode(StrEnum):
    """Fitting mode for display content scaling.

    Controls how content is scaled relative to available space.
    """

    NONE = "none"  # Use natural size, may overflow
    SHRINK = "shrink"  # Scale down if too large, but never up
    GROW = "grow"  # Scale up if too small, but never down
    SCALE = "scale"  # Scale in either direction to fit
