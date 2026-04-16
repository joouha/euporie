import logging
import re
from collections.abc import Hashable
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

from apptk.cache import SimpleCache
from apptk.styles.base import DEFAULT_ATTRS, Attrs, BaseStyle

from .base import (
    DEFAULT_ATTRS,
    Attrs,
    BaseStyle,
)
from .named_colors import NAMED_COLORS

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable

    from apptk.color import ColorPalette

_named_colors_lowercase = {k.lower(): v.lstrip("#") for k, v in NAMED_COLORS.items()}
_EMPTY_ATTRS = Attrs(
    color=None,
    bgcolor=None,
    bold=None,
    dim=None,
    underline=None,
    strike=None,
    italic=None,
    blink=None,
    reverse=None,
    hidden=None,
    ulcolor=None,
    doubleunderline=None,
    curvyunderline=None,
    dottedunderline=None,
    dashedunderline=None,
    blinkfast=None,
    overline=None,
    link=None,
)
CLASS_NAMES_RE = re.compile(r"^[a-z0-9.\s_-]*$")  # This one can't contain a comma!
default_priority = Priority.DICT_KEY_ORDER
_T = TypeVar("_T")
log = logging.getLogger(__name__)

__all__ = [
    "Priority",
    "Style",
    "merge_styles",
    "parse_color",
]

def parse_color(text: str) -> str: ...
def merge_styles(styles: list[BaseStyle]) -> _MergedStyle: ...

class Priority(Enum):
    DICT_KEY_ORDER = "KEY_ORDER"
    MOST_PRECISE = "MOST_PRECISE"

class Style(BaseStyle):
    _style_rules: list[tuple[str, str]]
    class_names_and_attrs = class_names_and_attrs
    def __init__(self, style_rules: list[tuple[str, str]]) -> None: ...
    @property
    def style_rules(self) -> list[tuple[str, str]]: ...
    @classmethod
    def from_dict(
        cls,
        style_dict: dict[str, str],
        priority: Priority = default_priority,
    ) -> Style: ...
    def get_attrs_for_style_str(
        self,
        style_str: str,
        default: Attrs = DEFAULT_ATTRS,
    ) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

class _MergedStyle(BaseStyle):
    styles: list[BaseStyle]
    _style: SimpleCache[Hashable, Style]
    def __init__(self, styles: list[BaseStyle]) -> None: ...
    @property
    def _merged_style(self) -> Style: ...
    @property
    def style_rules(self) -> list[tuple[str, str]]: ...
    def get_attrs_for_style_str(
        self,
        style_str: str,
        default: Attrs = DEFAULT_ATTRS,
    ) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

class PaletteStyle(BaseStyle):
    color_palette: ColorPalette
    _get_style: Callable[[ColorPalette], dict[str, str]]
    _cached_style: BaseStyle | None
    _cached_hash: Hashable | None
    def __init__(
        self,
        color_palette: ColorPalette,
        get_style: Callable[[ColorPalette], dict[str, str]],
    ) -> None: ...
    def _build_style(self) -> BaseStyle: ...
    def _style(self) -> BaseStyle: ...
    def get_attrs_for_style_str(
        self,
        style_str: str,
        default: Attrs = DEFAULT_ATTRS,
    ) -> Attrs: ...
    @property
    def style_rules(self) -> list[tuple[str, str]]: ...
    def invalidation_hash(self) -> Hashable: ...
