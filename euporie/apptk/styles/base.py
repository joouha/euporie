"""Contain data reference dictionaries for value lookups."""

from typing import NamedTuple

from prompt_toolkit.styles.base import ANSI_COLOR_NAMES, ANSI_COLOR_NAMES_ALIASES

KNOWN_COLORS = [*ANSI_COLOR_NAMES, *ANSI_COLOR_NAMES_ALIASES.keys()]


class Attrs(NamedTuple):
    """Style attributes."""

    color: str | None
    bgcolor: str | None
    bold: bool | None
    dim: bool | None
    underline: bool | None
    strike: bool | None
    italic: bool | None
    blink: bool | None
    reverse: bool | None
    hidden: bool | None
    blinkfast: bool | None = None
    ulcolor: str | None = None
    doubleunderline: bool | None = None
    curvyunderline: bool | None = None
    dottedunderline: bool | None = None
    dashedunderline: bool | None = None
    overline: bool | None = None


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
)
