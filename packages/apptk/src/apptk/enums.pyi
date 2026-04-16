from enum import Enum

SEARCH_BUFFER = "SEARCH_BUFFER"
DEFAULT_BUFFER = "DEFAULT_BUFFER"
SYSTEM_BUFFER = "SYSTEM_BUFFER"
COMMAND_BUFFER = "COMMAND_BUFFER"
BAR_BUFFERS = {SEARCH_BUFFER, SYSTEM_BUFFER, COMMAND_BUFFER}

class EditingMode(Enum):
    VI = "VI"
    EMACS = "EMACS"
    HELIX = "HELIX"
    MICRO = "MICRO"

class HorizontalAlign(Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"

class VerticalAlign(Enum):
    TOP = "top"
    MIDDLE = "middle"
    CENTER = "middle"
    BOTTOM = "bottom"
    JUSTIFY = "justify"

class FitMode(StrEnum):
    NONE = "none"  # Use natural size, may overflow
    SHRINK = "shrink"  # Scale down if too large, but never up
    GROW = "grow"  # Scale up if too small, but never down
    SCALE = "scale"  # Scale in either direction to fit
