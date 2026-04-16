from collections.abc import Generator
from string import Formatter
from typing import TYPE_CHECKING

from apptk.output.vt100 import (
    BG_ANSI_COLORS,
    FG_ANSI_COLORS,
)

from .base import StyleAndTextTuples

if TYPE_CHECKING:
    from collections.abc import Generator

_fg_colors = {v: k for k, v in FG_ANSI_COLORS.items()}
_bg_colors = {v: k for k, v in BG_ANSI_COLORS.items()}
_256_colors = {}
FORMATTER = ANSIFormatter()

__all__ = [
    "ANSI",
    "ansi_escape",
]

def ansi_escape(text: object) -> str: ...

class ANSI:
    value: str
    _formatted_text: StyleAndTextTuples
    _color = _fg_colors[attr]
    _bgcolor = _bg_colors[attr]
    _bold = True
    _dim = True
    _underline = True
    _strike = True
    _italic = True
    _blink = True
    _reverse = True
    _hidden = True
    _ul_color: str | None
    _blinkfast = False
    _overline = False
    _double_underline = False
    _curvy_underline = False
    _dotted_underline = False
    _dashed_underline = False
    def __init__(self, value: str, tab_size: int = 8) -> None: ...
    def _parse_corot(self) -> Generator[None, str]: ...
    def _select_graphic_rendition(self, attrs: list[int]) -> None: ...
    def _create_style_string(self) -> str: ...
    def __repr__(self) -> str: ...
    def __pt_formatted_text__(self) -> StyleAndTextTuples: ...
    def format(self, *args: str, **kwargs: str) -> ANSI: ...
    def __mod__(self, value: object) -> ANSI: ...
    def _parse_sgr_sequence(self, sequence: str) -> None: ...

class ANSIFormatter(Formatter):
    def format_field(self, value: object, format_spec: str) -> str: ...
