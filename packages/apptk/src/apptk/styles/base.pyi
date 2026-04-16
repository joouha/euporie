from abc import abstractmethod
from collections.abc import Callable, Hashable
from typing import NamedTuple

class Attrs(NamedTuple):
    color: str | None
    bgcolor: str | None
    bold: bool | None
    underline: bool | None
    strike: bool | None
    italic: bool | None
    blink: bool | None
    reverse: bool | None
    hidden: bool | None
    dim: bool | None
    blinkfast: bool | None = False
    ulcolor: str | None = ""
    doubleunderline: bool | None = False
    curvyunderline: bool | None = False
    dottedunderline: bool | None = False
    dashedunderline: bool | None = False
    overline: bool | None = False
    link: str | None = ""

DEFAULT_ATTRS = Attrs(
    color="",
    bgcolor="",
    bold=False,
    dim=False,
    underline=False,
    strike=False,
    italic=False,
    blink=False,
    reverse=False,
    hidden=False,
    blinkfast=False,
    ulcolor="",
    doubleunderline=False,
    curvyunderline=False,
    dottedunderline=False,
    dashedunderline=False,
    overline=False,
    link="",
)
ANSI_COLOR_NAMES = [
    "ansidefault",
    # Low intensity, dark.  (One or two components 0x80, the other 0x00.)
    "ansiblack",
    "ansired",
    "ansigreen",
    "ansiyellow",
    "ansiblue",
    "ansimagenta",
    "ansicyan",
    "ansigray",
    # High intensity, bright. (One or two components 0xff, the other 0x00. Not supported everywhere.)
    "ansibrightblack",
    "ansibrightred",
    "ansibrightgreen",
    "ansibrightyellow",
    "ansibrightblue",
    "ansibrightmagenta",
    "ansibrightcyan",
    "ansiwhite",
]
ANSI_COLOR_NAMES_ALIASES: dict[str, str] = {
    "ansidarkgray": "ansibrightblack",
    "ansiteal": "ansicyan",
    "ansiturquoise": "ansibrightcyan",
    "ansibrown": "ansiyellow",
    "ansipurple": "ansimagenta",
    "ansifuchsia": "ansibrightmagenta",
    "ansilightgray": "ansigray",
    "ansidarkred": "ansired",
    "ansidarkgreen": "ansigreen",
    "ansidarkblue": "ansiblue",
}
KNOWN_COLORS = [*ANSI_COLOR_NAMES, *ANSI_COLOR_NAMES_ALIASES.keys()]

__all__ = [
    "ANSI_COLOR_NAMES",
    "ANSI_COLOR_NAMES_ALIASES",
    "DEFAULT_ATTRS",
    "Attrs",
    "BaseStyle",
    "DummyStyle",
    "DynamicStyle",
]

class BaseStyle:
    @abstractmethod
    def get_attrs_for_style_str(
        self,
        style_str: str,
        default: Attrs = DEFAULT_ATTRS,
    ) -> Attrs: ...
    @property
    @abstractmethod
    def style_rules(self) -> list[tuple[str, str]]: ...
    @abstractmethod
    def invalidation_hash(self) -> Hashable: ...

class DummyStyle(BaseStyle):
    def get_attrs_for_style_str(
        self,
        style_str: str,
        default: Attrs = DEFAULT_ATTRS,
    ) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...
    @property
    def style_rules(self) -> list[tuple[str, str]]: ...

class DynamicStyle(BaseStyle):
    get_style: Callable[[], BaseStyle | None]
    _dummy: DummyStyle
    def __init__(self, get_style: Callable[[], BaseStyle | None]) -> None: ...
    def get_attrs_for_style_str(
        self,
        style_str: str,
        default: Attrs = DEFAULT_ATTRS,
    ) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...
    @property
    def style_rules(self) -> list[tuple[str, str]]: ...
