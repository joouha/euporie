from enum import Enum

__all__ = [
    "ColorDepth",
]

class ColorDepth(str, Enum):
    value: str
    DEPTH_1_BIT = "DEPTH_1_BIT"
    DEPTH_4_BIT = "DEPTH_4_BIT"
    DEPTH_8_BIT = "DEPTH_8_BIT"
    DEPTH_24_BIT = "DEPTH_24_BIT"
    MONOCHROME = DEPTH_1_BIT
    ANSI_COLORS_ONLY = DEPTH_4_BIT
    DEFAULT = DEPTH_8_BIT
    TRUE_COLOR = DEPTH_24_BIT
    @classmethod
    def from_env(cls) -> ColorDepth | None: ...
    @classmethod
    def default(cls) -> ColorDepth: ...
