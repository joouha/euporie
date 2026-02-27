"""Contain data reference dictionaries for value lookups."""

from __future__ import annotations

from typing import NamedTuple

from prompt_toolkit.styles.base import (
    ANSI_COLOR_NAMES,
    ANSI_COLOR_NAMES_ALIASES,
)

KNOWN_COLORS = [*ANSI_COLOR_NAMES, *ANSI_COLOR_NAMES_ALIASES.keys()]


class Attrs(NamedTuple):
    """Style attributes."""

    # Original prompt_toolkit fields (must match order in PtkAttrs)
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
    # Extended fields (with default values)
    blinkfast: bool | None = False
    ulcolor: str | None = ""
    doubleunderline: bool | None = False
    curvyunderline: bool | None = False
    dottedunderline: bool | None = False
    dashedunderline: bool | None = False
    overline: bool | None = False


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
