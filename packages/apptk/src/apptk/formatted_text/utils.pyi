from collections.abc import Iterable
from typing import TYPE_CHECKING

from apptk.border import GridStyle, ThinGrid
from apptk.data_structures import DiBool, DiInt, DiStr
from apptk.enums import HorizontalAlign, VerticalAlign

from .base import (
    AnyFormattedText,
    OneStyleAndTextTuple,
    StyleAndTextTuples,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from apptk.formatted_text.base import OneStyleAndTextTuple, StyleAndTextTuples

_ZERO_WIDTH_FRAGMENTS = {"[ZeroWidthEscape]", "[ReverseOverwrite]"}

__all__ = [
    "fragment_list_len",
    "fragment_list_to_text",
    "fragment_list_width",
    "split_lines",
    "to_plain_text",
]

def to_plain_text(value: AnyFormattedText) -> str: ...
def fragment_list_len(fragments: StyleAndTextTuples) -> int: ...
def fragment_list_width(fragments: StyleAndTextTuples) -> int: ...
def fragment_list_to_text(fragments: StyleAndTextTuples) -> str: ...
def split_lines(
    fragments: Iterable[OneStyleAndTextTuple],
) -> Iterable[StyleAndTextTuples]: ...
def max_line_width(ft: StyleAndTextTuples) -> int: ...
def last_char(ft: StyleAndTextTuples) -> str | None: ...
def fragment_list_to_words(
    fragments: StyleAndTextTuples,
    sep: str = " ",
) -> Iterable[StyleAndTextTuples]: ...
def apply_style(ft: StyleAndTextTuples, style: str) -> StyleAndTextTuples: ...
def strip(
    ft: StyleAndTextTuples,
    left: bool = True,
    right: bool = True,
    chars: str | None = None,
    only_unstyled: bool = False,
) -> StyleAndTextTuples: ...
def strip_one_trailing_newline(ft: StyleAndTextTuples) -> StyleAndTextTuples: ...
def truncate(
    ft: StyleAndTextTuples,
    width: int,
    style: str = "",
    placeholder: str = "…",
    ignore_whitespace: bool = False,
) -> StyleAndTextTuples: ...
def substring(
    ft: StyleAndTextTuples,
    start: int | None = None,
    end: int | None = None,
) -> StyleAndTextTuples: ...
def wrap(
    ft: StyleAndTextTuples,
    width: int,
    style: str = "",
    placeholder: str = "…",
    left: int = 0,
    truncate_long_words: bool = True,
    strip_trailing_ws: bool = False,
    margin: str = "",
) -> StyleAndTextTuples: ...
def align(
    ft: StyleAndTextTuples,
    how: HorizontalAlign = HorizontalAlign.LEFT,
    width: int | None = None,
    style: str = "",
    placeholder: str = "…",
    ignore_whitespace: bool = False,
) -> StyleAndTextTuples: ...
def valign(
    ft: StyleAndTextTuples,
    how: VerticalAlign = VerticalAlign.MIDDLE,
    height: int | None = None,
    style: str = "",
) -> StyleAndTextTuples: ...
def join_lines(fragments: list[StyleAndTextTuples]) -> StyleAndTextTuples: ...
def pad(
    ft: StyleAndTextTuples,
    width: int | None = None,
    char: str = " ",
    style: str = "",
) -> StyleAndTextTuples: ...
def paste(
    ft_top: StyleAndTextTuples,
    ft_bottom: StyleAndTextTuples,
    row: int = 0,
    col: int = 0,
    transparent: bool = False,
    expand: bool = False,
) -> StyleAndTextTuples: ...
def concat(
    ft_a: StyleAndTextTuples,
    ft_b: StyleAndTextTuples,
    baseline_a: int = 0,
    baseline_b: int = 0,
    style: str = "",
) -> tuple[StyleAndTextTuples, int]: ...
def indent(
    ft: StyleAndTextTuples,
    margin: str = " ",
    style: str = "",
    skip_first: bool = False,
) -> StyleAndTextTuples: ...
def add_border(
    ft: StyleAndTextTuples,
    width: int | None = None,
    style: str = "",
    border_grid: GridStyle = ThinGrid,
    border_visibility: DiBool | bool = True,
    border_style: DiStr | str = "",
    padding: DiInt | int = 0,
    padding_style: DiStr | str = "",
) -> StyleAndTextTuples: ...
def lex(ft: StyleAndTextTuples, lexer_name: str) -> StyleAndTextTuples: ...
def apply_reverse_overwrites(ft: StyleAndTextTuples) -> StyleAndTextTuples: ...
