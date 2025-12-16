"""Contain a HTML to formatted text parser."""

from __future__ import annotations

import asyncio
import logging
import re
from ast import literal_eval
from bisect import bisect_right
from collections.abc import Mapping
from functools import cached_property, lru_cache, partial
from html.parser import HTMLParser
from itertools import zip_longest
from math import ceil
from operator import eq, ge, gt, le, lt
from typing import TYPE_CHECKING, NamedTuple, cast, overload

from fsspec.core import url_to_fs
from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.data_structures import Size
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.utils import _always as always
from prompt_toolkit.filters.utils import _never as never
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.containers import WindowAlign
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.app.current import get_app
from euporie.core.async_utils import get_or_create_loop, run_coro_sync
from euporie.core.border import (
    DiLineStyle,
    DoubleLine,
    FullDottedLine,
    FullLine,
    GridStyle,
    InvisibleLine,
    LowerLeftEighthLine,
    LowerLeftHalfDottedLine,
    LowerLeftHalfLine,
    NoLine,
    RoundedLine,
    ThickDoubleDashedLine,
    ThickLine,
    ThickQuadrupleDashedLine,
    ThinDoubleDashedLine,
    ThinLine,
    ThinQuadrupleDashedLine,
    UpperRightEighthLine,
    UpperRightHalfDottedLine,
    UpperRightHalfLine,
)
from euporie.core.convert.datum import Datum
from euporie.core.convert.mime import get_format
from euporie.core.data_structures import DiBool, DiInt, DiStr
from euporie.core.ft.table import Cell, Table, compute_padding
from euporie.core.ft.utils import (
    FormattedTextAlign,
    FormattedTextVerticalAlign,
    add_border,
    align,
    apply_reverse_overwrites,
    apply_style,
    concat,
    fragment_list_to_words,
    fragment_list_width,
    join_lines,
    last_char,
    max_line_width,
    pad,
    paste,
    strip,
    truncate,
    valign,
)

sub_trans = str.maketrans(
    "0123456789+-=()aeijoruvxβγρφχ",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑᵢⱼₒᵣᵤᵥₓᵦᵧᵨᵩᵪ",
)

sup_trans = str.maketrans(
    "0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVWαβγδ∊θιΦφχ",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂᵅᵝᵞᵟᵋᶿᶥᶲᵠᵡ",
)


class CssSelector(NamedTuple):
    """A named tuple to hold CSS selector data."""

    comb: str | None = None
    item: str | None = None
    attr: str | None = None
    pseudo: str | None = None

    def __repr__(self) -> str:
        """Return a string representation of the selector."""
        defaults = self._field_defaults
        attrs = ", ".join(
            f"{k}={v!r}" for k, v in self._asdict().items() if v != defaults[k]
        )
        return f"{self.__class__.__name__}({attrs})"


if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator
    from pathlib import Path
    from typing import Any

    from fsspec.spec import AbstractFileSystem
    from prompt_toolkit.filters.base import Filter, FilterOrBool
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.mouse_events import MouseEvent

    CssSelectors = dict[
        Filter, dict[tuple[tuple[CssSelector, ...], ...], dict[str, str]]
    ]

log = logging.getLogger(__name__)


class Direction(NamedTuple):
    """A description of a direction."""

    x: bool = False
    y: bool = False


# Prefer 6-digit hex-colors over 3-digit ones
_COLOR_RE = re.compile(r"#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})")

_SELECTOR_RE = re.compile(
    r"""
        (?:^|\s*(?P<comb>[\s>+~]|(?=::))\s*)
        (?P<item>(?:::)?[^\s>+~:[\]]+)?
        (?P<attr>\[[^\s>+~]+\])?
        (?P<pseudo>\:[^:][^\s>+~]*)?
    """,
    re.VERBOSE,
)

_AT_RULE_RE = re.compile(
    r"""
    (
        @(?:color-profile|container|counter-style|document|font-face|font-feature-values|font-palette-values|keyframes|layer|media|page|supports)
        [^@{]+
        (?:
            {[^{}]*}
            |
            {(?:[^{]+?{(?:[^{}]|{[^}]+?})+?}\s*)*?}
        )
        |
        @(?:charset|import|namespace)[^;]*;
    )
    """,
    re.VERBOSE,
)

_NESTED_AT_RULE_RE = re.compile(
    r"@(?P<identifier>[\w-]+)\s*(?P<rule>[^{]*?)\s*{\s*(?P<part>.*)\s*}"
)

_MEDIA_QUERY_TARGET_RE = re.compile(
    r"""
        (?:
            (?P<invert>not\s+)?
            (?:only\s+)?  # Ignore this
            (?P<type>all|print|screen) |
            (?:\((?P<feature>[^)]+)\))
        )
    """,
    re.VERBOSE,
)

_GRID_TEMPLATE_RE = re.compile(
    r"""
        (
            none|auto|(?:min|max)-content
          | (?<!-)\d+(?:\.\d+)?(?:\w{1,4}|%)
          | minmax\(\s*[^,]+?\s*,\s*[^)]+?\s*\)
          | repeat\(\s*(?:\d+|auto-fill|auto-fit)\s*,\s*[^)]+?\s*\)
          | [^\s]+
        )
        (?=\s+|$)
    """,
    re.MULTILINE | re.VERBOSE,
)

_GRID_TEMPLATE_REPEAT_RE = re.compile(
    r"repeat\(\s*(?P<count>\d+)\s*,\s*(?P<value>[^)]+?)\s*\)"
)

_MATHJAX_TAG_RE = re.compile(
    r"""
        ^(?P<beginning>.*?)
        (?P<middle>
            \\\[(?P<display_bracket>.*?)\\\]
            |
            \\\((?P<inline_bracket>.*?)\\\)
            |
            \$\$(?P<display_dollar>.*?)\$\$
            |
            \$(?P<inline_dollar>.*?)(?: \$(?=\$\$) | (?<!\$)\$(?!\$) )
        )
        (?P<end>.*)$
    """,
    re.MULTILINE | re.VERBOSE,
)

# List of elements which might not have a close tag
_VOID_ELEMENTS = (
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
    # SVG
    "circle",
    "ellipse",
    "use",
    "path",
)

_LIST_STYLE_TYPES = {
    "none": "",
    "disc": "•",
    "circle": "○",
    "square": "■",
    "triangle": "▲",
    "disclosure-open": "▼",
    "disclosure-closed": "▶",
}

_BORDER_WIDTHS = {
    "thin": 0.1,
    "medium": 0.15,
    "thick": 0.3,
}

_BORDER_WIDTH_STYLES = {
    0: (
        _ := {
            "none": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "hidden": DiLineStyle(
                InvisibleLine, InvisibleLine, InvisibleLine, InvisibleLine
            ),
            "dotted": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "dashed": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "solid": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "double": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "groove": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "inset": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "outset": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
            "ridge": DiLineStyle(NoLine, NoLine, NoLine, NoLine),
        }
    ),
    0.00001: (
        _ := {
            **_,
            "dotted": DiLineStyle(
                ThinQuadrupleDashedLine,
                ThinQuadrupleDashedLine,
                ThinQuadrupleDashedLine,
                ThinQuadrupleDashedLine,
            ),
            "dashed": DiLineStyle(
                ThinDoubleDashedLine,
                ThinDoubleDashedLine,
                ThinDoubleDashedLine,
                ThinDoubleDashedLine,
            ),
            "solid": DiLineStyle(ThinLine, ThinLine, ThinLine, ThinLine),
            "double": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "inset": DiLineStyle(
                LowerLeftEighthLine,
                LowerLeftEighthLine,
                UpperRightEighthLine,
                UpperRightEighthLine,
            ),
            "outset": DiLineStyle(
                UpperRightEighthLine,
                UpperRightEighthLine,
                LowerLeftEighthLine,
                LowerLeftEighthLine,
            ),
            "ridge": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "groove": DiLineStyle(ThinLine, ThinLine, ThinLine, ThinLine),
        }
    ),
    0.2: (
        _ := {
            **_,
            "dotted": DiLineStyle(
                ThickQuadrupleDashedLine,
                ThickQuadrupleDashedLine,
                ThickQuadrupleDashedLine,
                ThickQuadrupleDashedLine,
            ),
            "dashed": DiLineStyle(
                ThickDoubleDashedLine,
                ThickDoubleDashedLine,
                ThickDoubleDashedLine,
                ThickDoubleDashedLine,
            ),
            "solid": DiLineStyle(ThickLine, ThickLine, ThickLine, ThickLine),
            "double": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "ridge": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "groove": DiLineStyle(ThickLine, ThickLine, ThickLine, ThickLine),
        }
    ),
    0.5: (
        _ := {
            **_,
            "solid": DiLineStyle(
                UpperRightHalfLine,
                UpperRightHalfLine,
                LowerLeftHalfLine,
                LowerLeftHalfLine,
            ),
        }
    ),
    1: (
        _ := {
            **_,
            "solid": DiLineStyle(
                UpperRightHalfLine, FullLine, LowerLeftHalfLine, FullLine
            ),
            "double": DiLineStyle(DoubleLine, DoubleLine, DoubleLine, DoubleLine),
            "dotted": DiLineStyle(
                UpperRightHalfDottedLine,
                FullDottedLine,
                LowerLeftHalfDottedLine,
                FullDottedLine,
            ),
        }
    ),
    2: (
        _ := {
            **_,
            "solid": DiLineStyle(FullLine, FullLine, FullLine, FullLine),
        }
    ),
}

_TEXT_ALIGNS = {
    "left": FormattedTextAlign.LEFT,
    "center": FormattedTextAlign.CENTER,
    "right": FormattedTextAlign.RIGHT,
}

_VERTICAL_ALIGNS = {
    "top": 0,
    "middle": 0.5,
    "baseline": 1,
}

_HERITABLE_PROPS = {
    "color",
    "font_style",
    "font_size",
    "font_weight",
    "text_transform",
    "text_decoration",
    "text_align",
    "vertical_align",
    "visibility",
    "white_space",
    "list_style_type",
    "list_style_position",
    "_pt_class",
}


@lru_cache(maxsize=500_000)
def match_css_selector(
    selector: str,
    attrs: str,
    pseudo: str,
    element_name: str,
    is_first_child_element: bool,
    is_last_child_element: bool,
    sibling_element_index: int | None,
    **element_attrs: Any,
) -> bool:
    """Determine if a CSS selector matches a particular element."""
    matched = True

    # Check for pseudo classes
    while pseudo and matched:
        if pseudo.startswith(":first-child"):
            matched = is_first_child_element
            pseudo = pseudo[12:]
            continue
        if pseudo.startswith(":last-child"):
            matched = is_last_child_element
            pseudo = pseudo[11:]
            continue
        if pseudo.startswith(":only-child"):
            matched = is_first_child_element and is_last_child_element
            pseudo = pseudo[11:]
            continue
        if pseudo.startswith(":nth-child("):
            pseudo = pseudo[11:]
            end = pseudo.find(")")
            if end > -1:
                rule = pseudo[:end]
                pseudo = pseudo[end + 1 :]
                matched = sibling_element_index is not None and (
                    # n-th child indices start at one
                    (str(sibling_element_index + 1) == rule)
                    or (rule == "odd" and sibling_element_index % 2 == 1)
                    or (rule == "even" and sibling_element_index % 2 == 0)
                )
                continue
        if pseudo.startswith(":link"):
            pseudo = pseudo[5:]
            matched = bool(element_attrs.get("href"))
            continue
        return False

    if not matched:
        return False

    while selector and matched:
        # Universal selector
        if selector == "*" and not element_name.startswith("::"):
            break

        # Element selectors
        if selector[0] not in ".#[":
            if selector.startswith(element_name):
                selector = selector[len(element_name) :]
            else:
                return False

        # ID selectors
        if selector.startswith("#"):
            if id_ := element_attrs.get("id"):
                if selector[1:].startswith(id_):
                    selector = selector[1 + len(id_) :]
                else:
                    return False
            else:
                return False

        # Class selectors
        if selector and selector.startswith("."):
            for class_name in sorted(
                element_attrs.get("class", "").split(), key=len, reverse=True
            ):
                # IF CLASS NAME SUBSTRING
                if selector[1:].startswith(class_name):
                    selector = selector = selector[1 + len(class_name) :]
                    break
            else:
                return False

    # Attribute selectors
    # TODO - chained attribute selectors
    if attrs and matched:
        for test in re.split(r"(?<=\])(?=\[)", attrs):
            test = test[1:-1]
            if (op := "*=") in test:
                attr, _, value = test.partition(op)
                value = value.strip("'\"")
                matched = value in element_attrs.get(attr, "")
            elif (op := "$=") in test:
                attr, _, value = test.partition(op)
                value = value.strip("'\"")
                matched = element_attrs.get(attr, "").endswith(value)
            elif (op := "^=") in test:
                attr, _, value = test.partition(op)
                value = value.strip("'\"")
                matched = element_attrs.get(attr, "").startswith(value)
            elif (op := "|=") in test:
                attr, _, value = test.partition(op)
                value = value.strip("'\"")
                matched = element_attrs.get(attr) in (value, f"{value}-")
            elif (op := "~=") in test:
                attr, _, value = test.partition(op)
                value = value.strip("'\"")
                matched = value in element_attrs.get(attr, "").split()
            elif (op := "=") in test:
                attr, _, value = test.partition(op)
                value = value.strip("'\"")
                matched = element_attrs.get(attr) == value
            else:
                matched = test in element_attrs

            if not matched:
                break

        else:
            selector = selector[2 + len(attrs) :]

    return matched


def try_eval(value: str, default: Any = None) -> Any:
    """Attempt to cast a string to a python type."""
    parsed_value = default or value
    try:
        parsed_value = literal_eval(value)
    except (
        ValueError,
        TypeError,
        SyntaxError,
        MemoryError,
        RecursionError,
    ):
        return parsed_value
    return parsed_value


def get_integer(value: str) -> int | None:
    """Extract the first integer from a string."""
    for word in value.split(" "):
        try:
            output = float(word)
        except ValueError:
            continue
        else:
            return round(output)
    return None


@lru_cache
def get_color(value: str) -> str:
    """Extract a hex color from a string."""
    if match := re.search(_COLOR_RE, value):
        hexes = match.group(1)
        if len(hexes) == 3:
            hexes = "".join(2 * s for s in hexes)
        return f"#{hexes}"
    elif value.startswith("rgb"):
        # Ignore alpha for now - TODO
        color_values = value.strip("rgba()").split(",")[:3]
        hexes = []
        for color_value in color_values:
            if (int_value := get_integer(color_value)) is not None:
                hexes.append(f"{hex(int_value)[2:]:02}")
            else:
                return ""
        return "#" + "".join(hexes)
    else:
        from euporie.core.reference import KNOWN_COLORS

        if value == "transparent" or value in KNOWN_COLORS:
            return value

        from euporie.core.reference import NAMED_COLORS

        if named_color := NAMED_COLORS.get(value.lower()):
            return named_color

    return ""


def css_dimension(
    value: str,
    vertical: bool = False,
    available: float | int | None = None,
) -> float | None:
    """Convert CSS dimensions to terminal cell sizes."""
    # TODO - create a unit class for easy conversion
    # Get digits
    digits = ""
    i = 0
    try:
        while (c := value[i]) in "-0123456789.":
            digits += c
            i += 1
    except IndexError:
        pass
    # Ensure we only have one decimal place
    digits = ".".join(digits.split(".")[:2])
    # Convert to Float
    try:
        number = float(digits)
    except ValueError:
        return None

    if number == 0:
        return 0.0

    # Get units
    units = ""
    i = -1
    try:
        while (c := value[i]) not in "0123456789.":
            units += c
            i -= 1
    except IndexError:
        pass
    units = units[::-1]

    # Calculate size based on units

    # TODO - process view-width units
    # https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Values_and_units

    if units in {"%", "vh", "vw"}:
        assert available is not None
        return number / 100 * available

    # Get cell pixel dimensions
    app = get_app()
    if hasattr(app, "cell_size_px"):
        cell_px, cell_py = get_app().cell_size_px
    else:
        cell_px, cell_py = 10, 20

    if units == "px":
        cols = number / cell_px

        if vertical:
            aspect = cell_py / cell_px
            return cols / aspect
        else:
            return cols

    elif units == "fr":
        return number

    else:  # elif units in {"em", "rem", "lh", "ex", "ch", "rlh"}:
        # one unit = one cell width
        if vertical:
            return number * cell_px / cell_py
        else:
            return number


def parse_css_content(content: str) -> dict[str, str]:
    """Convert CSS declarations into the internals style representation."""
    theme: dict[str, str] = {}

    if not content:
        return theme

    for declaration in content.split(";"):
        name, _, value = declaration.partition(":")
        name = name.strip().lower()
        value = value.strip()

        # Helpers

        def _split_quad(value: str) -> tuple[str, str, str, str]:
            values = value.split()
            if len(values) == 1:
                top = right = bottom = left = values[0]
            elif len(values) == 2:
                top = bottom = values[0]
                left = right = values[1]
            elif len(values) == 3:
                top = values[0]
                right = left = values[1]
                bottom = values[2]
            elif len(values) >= 4:
                top, right, bottom, left, *_ = values
            else:
                top = right = bottom = left = ""
            return top, right, bottom, left

        def _split_pair(value: str) -> tuple[str, str]:
            values = value.split()
            if len(values) == 1:
                x = y = values[0]
            elif len(values) == 2:
                x = values[0]
                y = values[1]
            else:
                x = y = ""
            return x, y

        # Compute values

        if name == "background":
            # TODO - needs work
            for part in value.split():
                if color := get_color(part):
                    theme["background_color"] = color
                    break

        elif name == "padding":
            (
                theme["padding_top"],
                theme["padding_right"],
                theme["padding_bottom"],
                theme["padding_left"],
            ) = _split_quad(value)

        elif name in {
            "border",
            "border-top",
            "border-right",
            "border-bottom",
            "border-left",
        }:
            width_value = style_value = color_value = ""

            for each_value in value.split(maxsplit=2):
                if color := get_color(each_value):
                    color_value = color
                elif (
                    css_dimension(each_value) is not None
                    or each_value in _BORDER_WIDTH_STYLES
                ):
                    width_value = each_value
                elif each_value in _BORDER_WIDTH_STYLES[0]:
                    style_value = each_value

            if name in {"border", "border-top"}:
                theme["border_top_width"] = width_value
                theme["border_top_style"] = style_value
                theme["border_top_color"] = color_value
            if name in {"border", "border-right"}:
                theme["border_right_width"] = width_value
                theme["border_right_style"] = style_value
                theme["border_right_color"] = color_value
            if name in {"border", "border-bottom"}:
                theme["border_bottom_width"] = width_value
                theme["border_bottom_style"] = style_value
                theme["border_bottom_color"] = color_value
            if name in {"border", "border-left"}:
                theme["border_left_width"] = width_value
                theme["border_left_style"] = style_value
                theme["border_left_color"] = color_value

        elif name == "border-width":
            (
                theme["border_top_width"],
                theme["border_right_width"],
                theme["border_bottom_width"],
                theme["border_left_width"],
            ) = _split_quad(value)

        elif name == "border-style":
            (
                theme["border_top_style"],
                theme["border_right_style"],
                theme["border_bottom_style"],
                theme["border_left_style"],
            ) = _split_quad(value)

        elif name == "border-color":
            (
                theme["border_top_color"],
                theme["border_right_color"],
                theme["border_bottom_color"],
                theme["border_left_color"],
            ) = _split_quad(value)

        elif name == "margin":
            (
                theme["margin_top"],
                theme["margin_right"],
                theme["margin_bottom"],
                theme["margin_left"],
            ) = _split_quad(value)

        elif name == "overflow":
            theme["overflow_x"] = theme["overflow_y"] = value

        elif name == "list-style":
            for each_value in value.split():
                if each_value in {"inside", "outside"}:
                    theme["list_style_position"] = each_value
                elif each_value in _LIST_STYLE_TYPES:
                    theme["list_style_type"] = each_value

        elif name == "flex-flow":
            values = set(value.split(" "))
            directions = {"row", "row-reverse", "column", "column-reverse"}
            wraps = {"nowrap", "wrap", "wrap-reverse"}
            for value in values.intersection(directions):
                theme["flex_direction"] = value
            for value in values.intersection(wraps):
                theme["flex_wrap"] = value

        # Grid stuff
        elif name == "grid-template":
            rows, cols = value.split("/")
            theme["grid_template_rows"] = rows.strip()
            theme["grid_template_columns"] = cols.strip()

        elif name == "grid-column":
            start, _, end = value.partition("/")
            theme["grid_column_start"] = start.strip()
            theme["grid_column_end"] = end.strip()

        elif name == "grid-row":
            start, _, end = value.partition("/")
            theme["grid_row_start"] = start.strip()
            theme["grid_row_end"] = end.strip()

        # Gaps
        elif name == "gap":
            theme["column_gap"], theme["row_gap"] = _split_pair(value)
        elif name == "grid-column-gap":
            theme["column_gap"] = value
        elif name == "grid-row-gap":
            theme["row_gap"] = value

        else:
            name = name.replace("-", "_")
            theme[name] = value

    return theme


@lru_cache(maxsize=1024)
def selector_specificity(
    selector_parts: tuple[CssSelector, ...],
) -> tuple[int, int, int]:
    """Calculate the specificity score of a CSS selector."""
    identifiers = classes = elements = 0
    for selector in selector_parts:
        item = selector.item or ""
        identifiers += (ids := item.count("#"))
        classes += (clss := item.count("."))
        if item != "*" and not ids and not clss:
            elements += 1
        classes += (selector.attr or "").count("[")
        classes += (selector.pseudo or "").count(":")
    return (identifiers, classes, elements)


_DEFAULT_ELEMENT_CSS = {
    # Display
    "display": "block",
    "float": "none",
    "visibility": "visible",
    "opacity": "1.0",
    "overflow_x": "visible",
    "overflow_y": "visible",
    "vertical_align": "baseline",
    # Text
    "color": "default",
    "background_color": "default",
    "font_style": "normal",
    "font_size": "1em",
    "font_weight": "normal",
    "text_decoration": "none",
    "text_transform": "none",
    "text_align": "left",
    "white_space": "normal",
    # Box
    "padding_top": "0",
    "padding_left": "0",
    "padding_bottom": "0",
    "padding_right": "0",
    "margin_top": "0",
    "margin_left": "0",
    "margin_bottom": "0",
    "margin_right": "0",
    "border_top_width": "0",
    "border_left_width": "0",
    "border_bottom_width": "0",
    "border_right_width": "0",
    "border_top_style": "none",
    "border_left_style": "none",
    "border_bottom_style": "none",
    "border_right_style": "none",
    "border_top_color": "",
    "border_left_color": "",
    "border_bottom_color": "",
    "border_right_color": "",
    # Flex
    "flex_direction": "row",
    "align_content": "normal",
    # Position
    "position": "static",
    "top": "unset",
    "right": "unset",
    "bottom": "unset",
    "left": "unset",
    "z_index": "0",
    # Lists
    "list_style_type": "none",
    "list_style_position": "inside",
}


class Theme(Mapping):
    """The computed theme of an element."""

    def __init__(
        self,
        element: Node,
        parent_theme: Theme | None,
        available_width: int = 0,
        available_height: int = 0,
    ) -> None:
        """Initialize a new element theme."""
        self.element = element
        self.parent_theme = parent_theme
        self.available_width = available_width
        self.available_height = available_height

    def reset(self) -> None:
        """Reset all cached properties."""
        # Iterate over a copy of keys as dict changes size during loop
        for attr in list(self.__dict__.keys()):
            if isinstance(Theme.__dict__.get(attr), cached_property):
                delattr(self, attr)

    @cached_property
    def theme(self) -> dict[str, str]:
        """Return the combined computed theme."""
        rules = [
            *_DEFAULT_ELEMENT_CSS.items(),
            *self.inherited_browser_css_theme.items(),
            *self.browser_css_theme.items(),
            *self.inherited_theme.items(),
            *self.attributes_theme.items(),
            *self.dom_css_theme.items(),
            *self.style_attribute_theme.items(),
        ]
        theme = {
            **dict(rules),
            # Move !important rules to the end and strip !important string from values
            **{
                k: v.replace("!important", "").strip()
                for k, v in rules
                if "!important" in v
            },
        }
        return theme

    def update_space(
        self,
        available_width: int,
        available_height: int,
    ) -> None:
        """Set the space available to the element for rendering."""
        if self.theme["position"] in {"fixed"}:
            # Space is given by position
            dom = self.element.dom
            assert dom.width is not None
            assert dom.height is not None
            position = self.position
            self.available_width = (dom.width - position.right) - position.left
            self.available_height = (dom.height - position.bottom) - position.top

        else:
            self.available_width = available_width
            self.available_height = available_height

    # Theme calculation methods

    @cached_property
    def inherited_browser_css_theme(self) -> dict[str, str]:
        """Get the inherited parts from the browser CSS."""
        if (parent_theme := self.parent_theme) is not None:
            return {
                k: v
                for k, v in {
                    **parent_theme.inherited_browser_css_theme,
                    **parent_theme.browser_css_theme,
                }.items()
                if k in _HERITABLE_PROPS or k.startswith("__")
            }

        else:
            return {}

    @cached_property
    def inherited_theme(self) -> dict[str, str]:
        """Calculate the theme inherited from the element's parent."""
        theme: dict[str, str] = {}
        parent = self.element.parent

        # Text elements inherit from direct inline parents
        if self.element.name == "::text" and parent is not None:
            inline_parent_themes = []
            while parent.theme.d_inline:
                inline_parent_themes.append(parent.theme.theme)
                parent = parent.parent
                if parent is None:
                    break
            for inherited_theme in inline_parent_themes:
                theme.update(inherited_theme)

        # Inherit heritable properties from the parent element's theme
        # unless the default value is unset
        if (parent_theme := self.parent_theme) is not None:
            browser_css = self.browser_css_theme
            rules = [
                (k, v)
                for part in [
                    parent_theme.inherited_theme,
                    parent_theme.dom_css_theme,
                    parent_theme.attributes_theme,
                    parent_theme.style_attribute_theme,
                ]
                for k, v in part.items()
                if (k in _HERITABLE_PROPS or k.startswith("__"))
                and browser_css.get(k) != "unset"
            ]
            # Keep over-ridden !important items
            theme = {**dict(rules), **{k: v for k, v in rules if "!important" in v}}

        return theme

    @cached_property
    def style_attribute_theme(self) -> dict[str, str]:
        """Calculate the theme defined by the element's style attribute."""
        return parse_css_content(self.element.attrs.get("style", ""))

    @cached_property
    def attributes_theme(self) -> dict[str, str]:
        """Calculate the theme defined by (depreciated) HTML attributes."""
        theme = {}
        # border
        attrs = self.element.attrs
        if border_attr := attrs.get("border"):
            # TODO - this sets all child cell borders
            theme["border_top_width"] = f"{border_attr}px"
            theme["border_right_width"] = f"{border_attr}px"
            theme["border_bottom_width"] = f"{border_attr}px"
            theme["border_left_width"] = f"{border_attr}px"
            theme["border_top_style"] = "solid"
            theme["border_right_style"] = "solid"
            theme["border_bottom_style"] = "solid"
            theme["border_left_style"] = "solid"
        # color
        if (fg := attrs.get("color")) is not None:
            theme["color"] = fg
        # bgcolor
        if (bg := attrs.get("bgcolor")) is not None:
            theme["background_color"] = bg
        # h/valign
        if (align := attrs.get("halign")) is not None:
            theme["text_align"] = align
        if (align := attrs.get("valign")) is not None:
            theme["vertical_align"] = align
        # width/height
        if (value := attrs.get("width")) is not None:
            theme["width"] = f"{value}px"
        if (value := attrs.get("height")) is not None:
            theme["height"] = f"{value}px"
        # cellpadding # TODO
        return theme

    def _css_theme(self, css: CssSelectors) -> dict[str, str]:
        """Calculate the theme defined in CSS."""
        specificity_rules = []
        element = self.element
        # Pre-compute element attributes once
        element_name = element.name
        element_is_first = element.is_first_child_element
        element_is_last = element.is_last_child_element
        element_sibling_idx = element.sibling_element_index
        element_attrs = element.attrs
        element_parent = element.parent
        element_parents_rev = [x for x in element.parents[::-1] if x]

        for condition, css_block in css.items():
            # TODO - cache CSS within condition blocks
            if condition():
                for selectors, rule in css_block.items():
                    for selector_parts in selectors:
                        # Last selector item should match the current element
                        selector = selector_parts[-1]
                        if not match_css_selector(
                            selector.item or "",
                            selector.attr or "",
                            selector.pseudo or "",
                            element_name,
                            element_is_first,
                            element_is_last,
                            element_sibling_idx,
                            **element_attrs,
                        ):
                            continue

                        # All of the parent selectors should match a separate parent in order
                        # TODO - combinators
                        # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Selectors#combinators
                        unmatched_parents: list[Node]
                        if element_parent and (
                            (selector.comb == ">" and element_parent)
                            # Pseudo-element selectors only match direct ancestors
                            or ((item := selector.item) and item.startswith("::"))
                        ):
                            unmatched_parents = [element_parent]
                        else:
                            unmatched_parents = element_parents_rev[:]

                        # TODO investigate caching element / selector chains so we don't have to
                        # iterate through every parent every time

                        # Iterate through selector items in reverse, skipping the last
                        for selector in selector_parts[-2::-1]:
                            # Pre-compute selector attributes
                            item = selector.item or ""
                            attrs = selector.attr or ""
                            pseudo = selector.pseudo or ""
                            parent: Node | None
                            for i, parent in enumerate(unmatched_parents):
                                if parent and match_css_selector(
                                    item,
                                    attrs,
                                    pseudo,
                                    parent.name,
                                    parent.is_first_child_element,
                                    parent.is_last_child_element,
                                    parent.sibling_element_index,
                                    **parent.attrs,
                                ):
                                    if selector.comb == ">" and (
                                        parent := parent.parent
                                    ):
                                        unmatched_parents = [parent]
                                    else:
                                        unmatched_parents = element_parents_rev[i + 1 :]
                                    break
                            else:
                                break

                        else:
                            # Calculate selector specificity score
                            specificity_rules.append(
                                (selector_specificity(selector_parts), rule)
                            )
                            # We have already matched this rule, we don't need to keep checking
                            # the rest of the selectors for this rule
                            break

        # Shortcut in case of no rules
        if not specificity_rules:
            return {}

        # Move !important rules to the end
        rules = [
            (k, v)
            for rule in sorted(specificity_rules, key=lambda x: x[0])
            for k, v in rule[1].items()
        ]
        return {
            **dict(rules),
            **{k: v for k, v in rules if "!important" in v},
        }

    @cached_property
    def browser_css_theme(self) -> dict[str, str]:
        """Calculate the theme defined in the browser CSS."""
        return self._css_theme(css=self.element.dom.browser_css)

    @cached_property
    def dom_css_theme(self) -> dict[str, str]:
        """Calculate the theme defined in CSS in the DOM."""
        return self._css_theme(css=self.element.dom.css)

    # Computed properties

    @cached_property
    def d_block(self) -> bool:
        """If the element a block element."""
        theme = self.theme
        parent_theme = self.parent_theme
        return (
            theme["display"] in {"block", "flex", "grid"}
            and (
                parent_theme is None
                or (self.floated is None and not parent_theme.d_flex)
                or (
                    parent_theme.d_flex
                    and parent_theme["flex_direction"].startswith("col")
                )
            )
        ) or (parent_theme is not None and parent_theme.d_grid)

    @cached_property
    def d_inline(self) -> bool:
        """If the element an inline element."""
        return (
            # Elements in a grid container are not inline
            bool(
                (parent_theme := self.parent_theme) is not None
                and not parent_theme.d_grid
                and not parent_theme.d_flex
            )
            # Floated elements are inline-block
            and self.floated is None
            # Display set to inline
            and self.theme["display"] == "inline"
        )

    @cached_property
    def d_inline_block(self) -> bool:
        """If the element an inline element."""
        theme = self.theme
        parent_theme = self.parent_theme
        return (
            # Is an actual inline block
            theme["display"] == "inline-block"
            # Is floated
            or self.floated is not None
            # If flexed in the row direction
            or (
                parent_theme is not None
                and parent_theme.d_flex
                and parent_theme["flex_direction"].startswith("row")
            )
        )

    @cached_property
    def d_flex(self) -> bool:
        """If the element a block element."""
        return self.theme["display"] == "flex"

    @cached_property
    def d_grid(self) -> bool:
        """If the element a block element."""
        return self.theme["display"] == "grid"

    @cached_property
    def d_image(self) -> bool:
        """If the element is an image."""
        return self.element.name in {"img", "svg"}

    @cached_property
    def d_table(self) -> bool:
        """If the element a block element."""
        return self.theme["display"] == "table"

    @cached_property
    def d_table_cell(self) -> bool:
        """If the element a block element."""
        return self.theme["display"] == "table-cell"

    @cached_property
    def d_list_item(self) -> bool:
        """If the element an inline element."""
        return self.theme["display"] == "list-item" and self.floated is None

    @cached_property
    def d_blocky(self) -> bool:
        """If the element an inline element."""
        return (
            self.d_block
            or self.d_grid
            or self.d_table
            or self.d_table_cell
            or self.d_list_item
        )

    @cached_property
    def floated(self) -> str | None:
        """The float status of the element."""
        # Float property does not apply to flex-level boxes
        value = self.theme["float"]
        if value == "none" or (
            (parent_theme := self.parent_theme) and parent_theme.d_flex
        ):
            return None
        return value

    @property
    def min_width(self) -> int | None:
        """The minimum permitted width."""
        if value := self.get("min_width"):
            theme_width = css_dimension(
                value, vertical=False, available=self.available_width
            )
            if theme_width is not None:
                return round(theme_width)
        return None

    @property
    def width(self) -> int | None:
        """The pescribed width."""
        value = self.theme.get("width")

        theme_width: int | float | None
        if value:
            if value == "min-content":
                theme_width = self.min_content_width
            elif value == "max-content":
                theme_width = self.max_content_width
            else:
                theme_width = css_dimension(
                    value, vertical=False, available=self.available_width
                )
            if theme_width is not None:
                return min(round(theme_width), self.available_width)

        elif (element := self.element).name == "input":
            attrs = element.attrs
            if attrs.get("type") in {
                "text",
                "password",
                "email",
                "number",
                "search",
                "tel",
                "url",
            }:
                return try_eval(size) if (size := attrs.get("size")) else 20

        elif element.name == "::text":
            return len(element.text)

        return None

    @property
    def max_width(self) -> int | None:
        """The maximum permitted width."""
        if value := self.get("max_width"):
            theme_width = css_dimension(
                value, vertical=False, available=self.available_width
            )
            if theme_width is not None:
                return round(theme_width)
        return None

    @cached_property
    def min_content_width(self) -> int:
        """Get maximum absolute child width."""
        if self.element.name == "::text":
            return max([len(x) for x in self.element.text.split()] or [0])
        else:
            return max(
                [child.theme.min_content_width for child in self.element.contents]
                or [0]
            )

    @cached_property
    def max_content_width(self) -> int:
        """Get maximum absolute child width."""
        if self.element.name == "::text":
            return max([len(x) for x in self.element.text.split("\n")] or [0])
        else:
            return sum(
                [child.theme.max_content_width for child in self.element.contents]
                or [0]
            )

    @property
    def content_width(self) -> int:
        """Return the width available for rendering the element's content."""
        value = self.width

        border_box = self.theme.get("box_sizing") == "border-box"

        # Use max-content-width as default for inline-blocks
        if value is None and self.d_inline_block and not self.d_image:
            value = self.max_content_width
            # Do not use border-box for inline-blocks if no width is given
            border_box = False

        # If we do not have a value, use the available space
        if value is None:
            margin = self.margin
            value = (self.available_width or 0) - margin.left - margin.right

            # Blocks without a set with are rendered with border-box box-sizing
            if self.d_blocky or self.d_inline_block:
                border_box = True

        # Ignore box-sizing for table cells, as they include padding and borders
        if self.d_table_cell:
            border_box = False

        # Remove padding and borders from available space if we are using box-sizing
        if border_box:
            padding = self.padding
            border_visibility = self.border_visibility
            value -= padding.left + padding.right
            value -= border_visibility.left + border_visibility.right

        # Apply min / max width constraints
        if (max_width := self.max_width) is not None and max_width < value:
            value = max_width
        elif (min_width := self.min_width) is not None and min_width > value:
            value = min_width

        return round(max(0, value))

    @property
    def min_height(self) -> int | None:
        """The minimum permitted height."""
        if value := self.get("min_height"):
            theme_height = css_dimension(
                value, vertical=True, available=self.available_height
            )
            if theme_height is not None:
                return round(theme_height)
        return None

    @property
    def height(self) -> int | None:
        """The prescribed height."""
        # TODO - process min-/max-height
        if value := self.get("height"):
            theme_height = css_dimension(
                value, vertical=True, available=self.available_height
            )
            if theme_height is not None:
                return round(theme_height)
        return None

    @property
    def max_height(self) -> int | None:
        """The maximum permitted height."""
        if value := self.get("max_height"):
            theme_height = css_dimension(
                value, vertical=True, available=self.available_height
            )
            if theme_height is not None:
                return round(theme_height)
        return None

    @property
    def content_height(self) -> int:
        """Return the height available for rendering the element's content."""
        value = self.height

        border_box = self.theme.get("box_sizing") == "border-box"

        # Use max-content-height as default for inline-blocks
        # if value is None and self.d_inline_block and not self.d_image:
        #     value = self.max_content_height
        #     # Do not use border-box for inline-blocks if no height is given
        #     border_box = False

        # If we do not have a value, use the available space
        if value is None:
            margin = self.margin
            value = (self.available_height or 0) - margin.top - margin.bottom

            # Blocks without a set with are rendered with border-box box-sizing
            # (but not rendered tables as they include padding and borders)
            if self.d_blocky or self.d_inline_block:
                border_box = True

        # Ignore box-sizing for table cells, as they include padding and borders
        if self.d_table_cell:
            border_box = False

        # Remove padding and borders from available space if we are using box-sizing
        if border_box:
            padding = self.padding
            border_visibility = self.border_visibility
            value -= padding.top + padding.bottom
            value -= border_visibility.top + border_visibility.bottom

        # Apply min / max height constraints
        if (max_height := self.max_height) is not None and max_height < value:
            value = max_height
        elif (min_height := self.min_height) is not None and min_height > value:
            value = min_height

        return max(0, value)

    @cached_property
    def padding(self) -> DiInt:
        """Calculate the padding box."""
        output = {}
        a_w = self.available_width
        for direction, vertical in (
            ("top", True),
            ("right", False),
            ("bottom", True),
            ("left", False),
        ):
            value = css_dimension(
                self.theme[f"padding_{direction}"], vertical=vertical, available=a_w
            )
            output[direction] = round(value or 0)

        # Do not render top and bottom padding for inline elements
        if self.d_inline or self.d_inline_block:
            output["top"] = 0
            output["bottom"] = 0

        return DiInt(**output)

    @cached_property
    def base_margin(self) -> DiInt:
        """Calculate the margin box."""
        output = {}
        a_w = self.available_width
        for direction, vertical in (
            ("top", True),
            ("right", False),
            ("bottom", True),
            ("left", False),
        ):
            value = css_dimension(
                self.theme[f"margin_{direction}"], vertical=vertical, available=a_w
            )
            # Round up if <=.4em
            output[direction] = round((value or 0) + 0.2)
        return DiInt(**output)

    @cached_property
    def margin(self) -> DiInt:
        """Calculate the margin box."""
        values = self.base_margin._asdict()
        element = self.element
        if (
            self.d_blocky
            # Margins of the root element's box do not collapse (although we
            # allow it via configuration)
            and (element.name != "::root" or not element.dom.collapse_root_margin)
        ):
            # Collapse margins for empty block elements
            if (
                self.border_visibility.top
                and not self.border_visibility.bottom
                and self.height is None
            ):
                values["top"] = 0
                values["bottom"] = 0

            # Collapse if there is no content separating parent and descendants
            if parent_theme := self.parent_theme:
                parent_padding = parent_theme.padding
                parent_border_visibility = parent_theme.border_visibility

                if (
                    parent_theme.d_blocky
                    and element.prev_node_in_flow is None
                    and not parent_border_visibility.top
                    and not parent_padding.top
                ):
                    values["top"] = 0

                # Remove the margin from the child
                if (
                    parent_theme.d_blocky
                    and element.next_node_in_flow is None
                    and not parent_padding.bottom
                    and not parent_border_visibility.bottom
                ):
                    values["bottom"] = 0

            # Replace the margin on the parent
            if (
                (first_child := element.first_child_element)
                and first_child.theme.in_flow
                and first_child.prev_node_in_flow is None
                and not self.border_visibility.top
                and not self.padding.top
            ):
                child_theme = first_child.theme
                if child_theme.d_blocky:
                    # TODO - check this
                    if child_theme.available_width is None:
                        child_theme.update_space(
                            self.available_width, self.available_height
                        )
                    values["top"] = max(child_theme.base_margin.top, values["top"])
            if (
                (last_child := element.last_child_element)
                and last_child.theme.in_flow
                and last_child.next_node_in_flow is None
                and not self.padding.bottom
                and not self.border_visibility.bottom
            ):
                child_theme = last_child.theme
                if child_theme.d_blocky:
                    # TODO - check this
                    if child_theme.available_width is None:
                        child_theme.update_space(
                            self.available_width, self.available_height
                        )
                    values["bottom"] = max(
                        child_theme.base_margin.bottom, values["bottom"]
                    )

            # Margins of adjacent children in the flow are collapsed
            if (prev_sib := element.prev_node_in_flow) and (prev_sib.theme.d_blocky):
                values["top"] = max(0, values["top"] - prev_sib.theme.margin.bottom)

        # Do not render top and bottom margins for inline elements
        if self.d_inline:
            values["top"] = 0
            values["bottom"] = 0

        # Add gaps
        # TODO - do not add to last item in cols / rows
        if (parent_theme := self.parent_theme) and (
            parent_theme := self.parent_theme
        ).d_flex:
            gap_x, gap_y = parent_theme.gap
            values["right"] += gap_x
            values["bottom"] += gap_y

        return DiInt(**values)

    @cached_property
    def block_align(self) -> FormattedTextAlign:
        """Determine if the left and right margins are set to auto."""
        # Temporarily use "justify_self" until flex / grid are implemented (TODO)
        if (self.theme["margin_left"] == self.theme["margin_right"] == "auto") or (
            self.d_inline_block and self.theme.get("justify_self") == "center"
        ):
            return FormattedTextAlign.CENTER
        elif (self.theme["margin_left"] == "auto") or (
            self.d_inline_block and self.theme.get("justify_self") == "right"
        ):
            return FormattedTextAlign.RIGHT
        return FormattedTextAlign.LEFT

    @cached_property
    def border_style(self) -> DiStr:
        """Calculate the visibility of the element's borders."""
        parent_style = parent_theme.style if (parent_theme := self.parent_theme) else ""

        output = {}
        for direction in ("top", "left", "bottom", "right"):
            style = f"{parent_style}"

            if "_pt_class" in self.theme:
                style += f" class:{self.theme['_pt_class']}"

            color_str = get_color(self.theme[f"border_{direction}_color"])
            if color_str == "transparent" and parent_theme:
                style += f" fg:{parent_theme.background_color}"
            elif border_color := get_color(color_str):
                style += f" fg:{border_color}"

            # if getattr(self.border_line, direction) in {
            #     UpperRightEighthLine,
            #     LowerLeftEighthLine,
            # }:
            if bg := self.background_color:
                style += f" bg:{bg} "

            output[direction] = style

        return DiStr(**output)

    @cached_property
    def border_visibility(self) -> DiBool:
        """Calculate the visibility of the element's borders."""
        theme = self.theme
        output = {
            direction: css_dimension(theme[f"border_{direction}_width"]) != 0
            and theme[f"border_{direction}_style"] != "none"
            for direction in ("top", "left", "bottom", "right")
        }

        # Do not render top and bottom borders for inline elements
        # if there is no top or bottom padding
        if self.d_inline:
            padding = self.padding
            if not padding.top:
                output["top"] = False
            if not padding.bottom:
                output["bottom"] = False

        return DiBool(**output)

    @cached_property
    def border_line(self) -> DiLineStyle:
        """Calculate the line style."""
        a_w = self.available_width
        output = {}
        for direction in ("top", "right", "bottom", "left"):
            border_width = self.theme[f"border_{direction}_width"]
            size = (
                _BORDER_WIDTHS.get(
                    border_width,
                    css_dimension(border_width, vertical=False, available=a_w),
                )
                or 0
            )
            size = max(0, size)

            if size and self.d_inline:
                if direction == "left":
                    output[direction] = LowerLeftEighthLine
                elif direction == "right":
                    output[direction] = UpperRightEighthLine

            else:
                output[direction] = getattr(
                    list(_BORDER_WIDTH_STYLES.values())[
                        bisect_right(list(_BORDER_WIDTH_STYLES.keys()), size) - 1
                    ].get(self.theme[f"border_{direction}_style"]),
                    direction,
                    NoLine,
                )

                # TODO - parse border_radius properly and check for corner radii
                if output[direction] == ThinLine and self.theme.get("border_radius"):
                    output[direction] = RoundedLine

        return DiLineStyle(**output)

    @cached_property
    def border_grid(self) -> GridStyle:
        """Calculate a GridStyle based on the border lines."""
        border_line = self.border_line
        return (
            border_line.top.top_edge
            + border_line.right.right_edge
            + border_line.bottom.bottom_edge
            + border_line.left.left_edge
        )

    @cached_property
    def border_collapse(self) -> bool:
        """Determine if the border is collapsed."""
        return self.theme.get("border_collapse") == "collapse"

    @cached_property
    def color(self) -> str:
        """Get the computed theme foreground color."""
        # TODO - transparency
        color_str = self.theme["color"]
        # Use black as the default color if a bg color is set
        while color_str.startswith("var("):
            var, _, fallback = color_str[4:-1].replace("-", "_").partition(",")
            color_str = self.theme.get(var.strip(), fallback.strip() or "default")
        if color_str == "default" and self.theme["background_color"] != "default":
            color_str = "#000000"
        elif color_str == "transparent":
            return self.background_color
        if fg := get_color(color_str):
            return fg
        elif self.parent_theme:
            return self.parent_theme.color
        else:
            return ""

    @cached_property
    def background_color(self) -> str:
        """Get the computed theme background color."""
        # TODO - transparency
        color_str = self.theme["background_color"]
        # Use white as the default bg color if a fg color is set
        # if color_str == "default" and self.theme["color"] != "default":
        #     color_str = "#ffffff"
        while color_str.startswith("var("):
            var, _, fallback = color_str[4:-1].replace("-", "_").partition(",")
            color_str = self.theme.get(var.strip(), fallback.strip() or "default")
        if color_str == "transparent":
            if parent_theme := self.parent_theme:
                return parent_theme.background_color
            color_str = ""
        if bg := get_color(color_str):
            return bg
        elif self.parent_theme:
            return self.parent_theme.background_color
        else:
            return ""

    @cached_property
    def style(self) -> str:
        """Calculate the output style."""
        theme = self.theme
        style = ""

        if "_pt_class" in self.theme:
            style += f" class:{theme['_pt_class']} "

        if fg := self.color:
            style += f" fg:{fg}"

        if bg := self.background_color:
            style += f" bg:{bg} "

        if "bold" in self.theme["font_weight"] or (
            isinstance((weight := try_eval(theme["font_weight"])), int)
            and weight >= 700
        ):
            style = f"{style} bold"

        if "italic" in theme["font_style"] or "oblique" in theme["font_style"]:
            style = f"{style} italic"

        if "underline" in theme["text_decoration"]:
            style = f"{style} underline"

        if "line-through" in theme["text_decoration"]:
            style = f"{style} strike"

        if "blink" in theme["text_decoration"]:
            style = f"{style} blink"

        if self.hidden:
            style = f"{style} hidden nounderline"

        return style

    async def text_transform(self, value: str) -> str:
        """Return a function which transforms text."""
        transform = self.theme["text_transform"]
        if "uppercase" in transform:
            return value.upper()
        elif "lowercase" in transform:
            return value.lower()
        elif "capitalize" in transform:
            return value.capitalize()
        elif "latex" in transform:
            return await Datum(value, "latex").convert_async("ansi")
        if "sub" in self.theme["vertical_align"]:
            return value.translate(sub_trans)
        elif "super" in self.theme["vertical_align"]:
            return value.translate(sup_trans)
        return value

    @cached_property
    def preformatted(self) -> bool:
        """Determine if the content is pre-formatted."""
        return self.theme["white_space"] in {"pre", "pre-wrap", "pre-line"}

    @cached_property
    def text_align(self) -> FormattedTextAlign:
        """The text alignment direction."""
        alignment = self.theme.get(
            "justify_content", self.theme.get("text_align", "left")
        )
        return _TEXT_ALIGNS.get(alignment, FormattedTextAlign.LEFT)

    @cached_property
    def vertical_align(self) -> float:
        """The vertical alignment direction."""
        if (parent_theme := self.parent_theme) and parent_theme.d_flex:
            if self.theme.get("align_content") in {
                "normal",
                "flex-start",
                "start",
                "baseline",
            }:
                return 0
            elif self.theme.get("align_content") == "center":
                return 0.5
            else:
                return 1

        return _VERTICAL_ALIGNS.get(self.theme["vertical_align"], 1)

    @cached_property
    def list_style_type(self) -> str:
        """The bullet character to use for the list."""
        if self.theme["list_style_type"] == "inherit" and (
            parent_theme := self.parent_theme
        ):
            return parent_theme.list_style_type
        return _LIST_STYLE_TYPES.get(
            style_type := self.theme["list_style_type"], style_type
        )

    @cached_property
    def list_style_position(self) -> str:
        """Where the list bullet should be located."""
        if "outside" in self.theme["list_style_position"]:
            return "outside"
        else:
            return "inside"

    @cached_property
    def font_size(self) -> float | int:
        """Get the computed font size for the current element."""
        available = self.parent_theme.font_size if self.parent_theme else 1
        if (
            result := css_dimension(self.theme["font_size"], available=available)
        ) is not None:
            return result
        else:
            return 1

    @cached_property
    def z_index(self) -> int:
        """The z-index of the element."""
        return get_integer(self.theme["z_index"]) or 0

    @cached_property
    def position(self) -> DiInt:
        """The position of an element with a relative, absolute or fixed position."""
        # TODO - calculate position based on top, left, bottom,right, width, height
        soup_theme = self.element.dom.soup.theme
        position = DiInt(0, 0, 0, 0)
        # if self.parent_theme is not None:
        #     position += self.parent_theme.position
        position += self.base_margin
        position += DiInt(
            top=round(
                css_dimension(
                    self.theme["top"],
                    vertical=True,
                    available=soup_theme.available_height,
                )
                or 0
            ),
            right=round(
                css_dimension(
                    self.theme["right"],
                    vertical=False,
                    available=soup_theme.available_width,
                )
                or 0
            ),
            bottom=round(
                css_dimension(
                    self.theme["bottom"],
                    vertical=True,
                    available=soup_theme.available_height,
                )
                or 0
            ),
            left=round(
                css_dimension(
                    self.theme["left"],
                    vertical=False,
                    available=soup_theme.available_width,
                )
                or 0
            ),
        )
        return position

    @cached_property
    def anchors(self) -> DiBool:
        """Which position directions are set."""
        return DiBool(
            top=self.theme["top"] not in {"unset"},
            right=self.theme["right"] not in {"unset"},
            bottom=self.theme["bottom"] not in {"unset"},
            left=self.theme["left"] not in {"unset"},
        )

    @cached_property
    def skip(self) -> bool:
        """Determine if the element should not be displayed."""
        return (
            (
                (element := self.element).name in ("::before", "::after")
                and self.theme.get("content") in (None, "normal")
            )
            or "none" in self.theme["display"]
            or (element.name == "::text" and not self.preformatted and not element.text)
            or (self.theme["position"] == "absolute" and self.hidden)
        )

    @cached_property
    def hidden(self) -> bool:
        """Determine if the element is hidden."""
        return (
            try_eval(self.theme["opacity"]) == 0 or self.theme["visibility"] == "hidden"
        )

    @cached_property
    def in_flow(self) -> bool:
        """Determine if the element is "in-flow"."""
        return (
            not self.skip
            and self.theme["position"] not in {"absolute", "fixed"}
            and self.element.name != "html"
            and self.floated is None
        )

    @cached_property
    def gap(self) -> tuple[int, int]:
        """Calculate the horizontal & vertical inter-element spacing."""
        return round(
            css_dimension(
                self.theme.get("column_gap", ""),
                vertical=False,
                available=self.available_width,
            )
            or 0
        ), round(
            css_dimension(
                self.theme.get("row_gap", ""),
                vertical=True,
                available=self.available_width,
            )
            or 0
        )

    @cached_property
    def grid_template(self) -> list[list[str]]:
        """Calculate the size of the grid tracks."""

        def _multiply_repeats(m: re.Match) -> str:
            result = m.groupdict()
            return " ".join(int(result["count"]) * [result["value"]])

        template = []
        for css_item in ("grid_template_columns", "grid_template_rows"):
            value = self.theme.get(css_item, "")
            value = _GRID_TEMPLATE_REPEAT_RE.sub(_multiply_repeats, value)
            template.append([m.group() for m in _GRID_TEMPLATE_RE.finditer(value)])
        return template

    @cached_property
    def grid_column_start(self) -> int | None:
        """The index of the first grid column spanned by the grid item."""
        value: int | None = None
        if "span" not in (value_str := self.theme.get("grid_column_start", "")):
            value = get_integer(value_str)
            if isinstance(value, int):
                value -= 1
        return value

    @cached_property
    def grid_column_span(self) -> int:
        """The number of grid columns spanned by the grid item."""
        value_start = self.theme.get("grid_column_start", "")
        value_end = self.theme.get("grid_column_end", "")
        span = 1
        for value in (value_start, value_end):
            if "span" in value:
                span = max(span, get_integer(value) or 1)
        return span

    @cached_property
    def grid_area(self) -> str | None:
        """The name of the grid area assigned to the grid item."""
        return self.theme.get("grid_area")

    @cached_property
    def grid_areas(self) -> dict[int, dict[int, str]]:
        """The layout of grid-areas in the current node's grid layout."""
        areas_str = self.theme.get("grid_template_areas", "")
        return dict(
            enumerate(
                [
                    dict(enumerate(x.split()))
                    for y in re.findall(r"""(?:"([^"]*)"|'([^']*)')""", areas_str)
                    for x in y
                    if x
                ]
            )
        )

    @cached_property
    def order(self) -> tuple[tuple[bool, int], int, tuple[bool, int]]:
        """Items are sorted by ascending order value then their source code order."""
        order = get_integer(self.theme.get("order", "")) or 0
        index = (self.element.sibling_flow_index or 0) + 1
        return (
            # Negative orders first
            (not order < 0, order),
            # Index
            index,
            # Orders
            (order > 0, order),
        )

    @cached_property
    def latex(self) -> bool:
        """If the element should be rendered as LaTeX."""
        return self.theme.get("_format") == "latex"

    # Mapping methods - these are passed on to the underlying theme dictionary

    def __getitem__(self, key: str) -> Any:
        """Get an item."""
        return self.theme.__getitem__(key)

    def __iter__(self) -> Iterator:
        """Iterate over items."""
        return self.theme.__iter__()

    def __len__(self) -> int:
        """Get the length of the mapping."""
        return self.theme.__len__()


_BROWSER_CSS: CssSelectors = {
    always: {
        # Set body background to white
        ((CssSelector(item="body"),),): {"background_color": "#FFFFFF"},
        # Non-rendered elements
        (
            (CssSelector(item="head"),),
            (CssSelector(item="base"),),
            (CssSelector(item="command"),),
            (CssSelector(item="link"),),
            (CssSelector(item="meta"),),
            (CssSelector(item="noscript"),),
            (CssSelector(item="script"),),
            (CssSelector(item="style"),),
            (CssSelector(item="title"),),
            (CssSelector(item="option"),),
            (CssSelector(item="input", attr="[type=hidden]"),),
        ): {"display": "none"},
        # Inline elements
        (
            (CssSelector(item="::before"),),
            (CssSelector(item="::after"),),
            (CssSelector(item="::text"),),
            (CssSelector(item="abbr"),),
            (CssSelector(item="acronym"),),
            (CssSelector(item="audio"),),
            (CssSelector(item="bdi"),),
            (CssSelector(item="bdo"),),
            (CssSelector(item="big"),),
            (CssSelector(item="br"),),
            (CssSelector(item="canvas"),),
            (CssSelector(item="data"),),
            (CssSelector(item="datalist"),),
            (CssSelector(item="embed"),),
            (CssSelector(item="iframe"),),
            (CssSelector(item="label"),),
            (CssSelector(item="map"),),
            (CssSelector(item="meter"),),
            (CssSelector(item="object"),),
            (CssSelector(item="output"),),
            (CssSelector(item="picture"),),
            (CssSelector(item="progress"),),
            (CssSelector(item="q"),),
            (CssSelector(item="ruby"),),
            (CssSelector(item="select"),),
            (CssSelector(item="slot"),),
            (CssSelector(item="small"),),
            (CssSelector(item="span"),),
            (CssSelector(item="template"),),
            (CssSelector(item="textarea"),),
            (CssSelector(item="time"),),
            (CssSelector(item="tt"),),
            (CssSelector(item="video"),),
            (CssSelector(item="wbr"),),
        ): {"display": "inline"},
        # Formatted inlines
        ((CssSelector(item="a"),),): {
            "display": "inline",
            "text_decoration": "underline",
            "color": "#0000FF",
        },
        ((CssSelector(item="b"),), (CssSelector(item="strong"),)): {
            "display": "inline",
            "font_weight": "bold",
        },
        ((CssSelector(item="blink"),),): {
            "display": "inline",
            "text_decoration": "blink",
        },
        (
            (CssSelector(item="cite"),),
            (CssSelector(item="dfn"),),
            (CssSelector(item="em"),),
            (CssSelector(item="i"),),
            (CssSelector(item="var"),),
        ): {"display": "inline", "font_style": "italic"},
        ((CssSelector(item="code"),),): {
            "display": "inline",
        },
        ((CssSelector(item="del"),), (CssSelector(item="s"),)): {
            "display": "inline",
            "text_decoration": "line-through",
        },
        (
            (CssSelector(item="img", attr="[width=0]"),),
            (CssSelector(item="img", attr="[height=0]"),),
            (CssSelector(item="svg", attr="[width=0]"),),
            (CssSelector(item="svg", attr="[height=0]"),),
        ): {"display": "none"},
        ((CssSelector(item="img"),), (CssSelector(item="svg"),)): {
            "display": "inline-block",
            "overflow_x": "hidden",
            "overflow_y": "hidden",
        },
        ((CssSelector(item="ins"),), (CssSelector(item="u"),)): {
            "display": "inline",
            "text_decoration": "underline",
        },
        ((CssSelector(item="kbd"),),): {
            "display": "inline",
            "background_color": "#333344",
            "color": "#FFFFFF",
        },
        ((CssSelector(item="mark"),),): {
            "display": "inline",
            "color": "black",
            "background_color": "#FFFF00",
        },
        ((CssSelector(item="samp"),),): {
            "display": "inline",
            "background_color": "#334433",
            "color": "#FFFFFF",
        },
        ((CssSelector(item="sub"),),): {"display": "inline", "vertical_align": "sub"},
        ((CssSelector(item="sup"),),): {"display": "inline", "vertical_align": "super"},
        (
            (
                CssSelector(item="q"),
                CssSelector(item="::before"),
            ),
        ): {"content": "'“'"},
        (
            (
                CssSelector(item="q"),
                CssSelector(item="::after"),
            ),
        ): {"content": "'”'"},
        # Images
        (
            (CssSelector(item="img", attr="[_missing]"),),
            (CssSelector(item="svg", attr="[_missing]"),),
        ): {
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "1px",
            "border_right_width": "1px",
            "border_bottom_width": "1px",
            "border_left_width": "1px",
            "border_top_color": "#888888",
            "border_right_color": "#888888",
            "border_bottom_color": "#888888",
            "border_left_color": "#888888",
        },
        # Alignment
        ((CssSelector(item="center"),), (CssSelector(item="caption"),)): {
            "text_align": "center",
            "display": "block",
        },
        # Tables
        ((CssSelector(item="table"),),): {
            "display": "table",
            "border_collapse": "collapse",
        },
        (
            (CssSelector(item="td"),),
            (CssSelector(item="th"),),
        ): {
            "border_top_width": "0px",
            "border_right_width": "0px",
            "border_bottom_width": "0px",
            "border_left_width": "0px",
        },
        ((CssSelector(item="td"),),): {"display": "table-cell", "text_align": "unset"},
        ((CssSelector(item="th"),),): {
            "display": "table-cell",
            "font_weight": "bold",
            "text_align": "center",
        },
        # Forms
        ((CssSelector(item="input"),),): {
            "display": "inline-block",
            "white_space": "pre",
            "color": "#000000",
            "border_top_style": "inset",
            "border_right_style": "inset",
            "border_bottom_style": "inset",
            "border_left_style": "inset",
            "border_top_width": "2px",
            "border_right_width": "2px",
            "border_bottom_width": "2px",
            "border_left_width": "2px",
            "vertical_align": "middle",
        },
        ((CssSelector(item="input", attr="[type=text]"),),): {
            "background_color": "#FAFAFA",
            "border_top_color": "#606060",
            "border_right_color": "#E9E7E3",
            "border_bottom_color": "#E9E7E3",
            "border_left_color": "#606060",
            "overflow_x": "hidden",
        },
        (
            (CssSelector(item="input", attr="[type=button]"),),
            (CssSelector(item="input", attr="[type=submit]"),),
            (CssSelector(item="input", attr="[type=reset]"),),
        ): {
            "background_color": "#d4d0c8",
            "border_right": "#606060",
            "border_bottom": "#606060",
            "border_left": "#ffffff",
            "border_top": "#ffffff",
        },
        ((CssSelector(item="button"),),): {
            "display": "inline-block",
            "color": "#000000",
            "border_top_style": "outset",
            "border_right_style": "outset",
            "border_bottom_style": "outset",
            "border_left_style": "outset",
            "border_top_width": "2px",
            "border_right_width": "2px",
            "border_bottom_width": "2px",
            "border_left_width": "2px",
            "background_color": "#d4d0c8",
            "border_right": "#606060",
            "border_bottom": "#606060",
            "border_left": "#ffffff",
            "border_top": "#ffffff",
        },
        # Headings
        ((CssSelector(item="h1"),),): {
            "font_weight": "bold",
            "text_decoration": "underline",
            "border_bottom_style": "solid",
            "border_bottom_width": "thick",
            "padding_bottom": "2rem",
            "margin_top": "2rem",
            "margin_bottom": "2em",
        },
        ((CssSelector(item="h2"),),): {
            "font_weight": "bold",
            "border_bottom_style": "double",
            "border_bottom_width": "thick",
            "padding_bottom": "1.5rem",
            "margin_top": "1.5rem",
            "margin_bottom": "1.5rem",
        },
        ((CssSelector(item="h3"),),): {
            "font_weight": "bold",
            "font_style": "italic",
            "border_bottom_style": ":lower-left",
            "border_bottom_width": "thin",
            "padding_top": "1rem",
            "padding_bottom": "1rem",
            "margin_bottom": "1.5rem",
        },
        ((CssSelector(item="h4"),),): {
            "text_decoration": "underline",
            "border_bottom_style": "solid",
            "border_bottom_width": "thin",
            "padding_top": "1rem",
            "padding_bottom": "1rem",
            "margin_bottom": "1.5rem",
        },
        ((CssSelector(item="h5"),),): {
            "border_bottom_style": "dashed",
            "border_bottom_width": "thin",
            "margin_bottom": "1.5rem",
        },
        ((CssSelector(item="h6"),),): {
            "font_style": "italic",
            "border_bottom_style": "dotted",
            "border_bottom_width": "thin",
            "margin_bottom": "1.5rem",
        },
        # Misc blocks
        ((CssSelector(item="blockquote"),),): {
            "margin_top": "1em",
            "margin_bottom": "1em",
            "margin_right": "2em",
            "margin_left": "2em",
        },
        ((CssSelector(item="hr"),),): {
            "margin_top": "1rem",
            "margin_bottom": "1rem",
            "border_top_width": "thin",
            "border_top_style": "solid",
            "border_top_color": "ansired",
            "width": "100%",
        },
        ((CssSelector(item="p"),),): {"margin_top": "1em", "margin_bottom": "1em"},
        ((CssSelector(item="pre"),),): {
            "margin_top": "1em",
            "margin_bottom": "1em",
            "white_space": "pre",
        },
        # Lists
        ((CssSelector(item="::marker"),),): {
            "display": "inline-block",
            "padding_right": "1em",
            "text_align": "right",
        },
        ((CssSelector(item="ol"),),): {
            "list_style_type": "decimal",
            "list_style_position": "outside",
            "padding_left": "4em",
            "margin_top": "1em",
            "margin_bottom": "1em",
        },
        (
            (CssSelector(item="ul"),),
            (CssSelector(item="menu"),),
            (CssSelector(item="dir"),),
        ): {
            "list_style_type": "disc",
            "list_style_position": "outside",
            "padding_left": "3em",
            "margin_top": "1em",
            "margin_bottom": "1em",
        },
        (
            (CssSelector(item="dir"), CssSelector(item="dir")),
            (CssSelector(item="dir"), CssSelector(item="menu")),
            (CssSelector(item="dir"), CssSelector(item="ul")),
            (CssSelector(item="ol"), CssSelector(item="dir")),
            (CssSelector(item="ol"), CssSelector(item="menu")),
            (CssSelector(item="ol"), CssSelector(item="ul")),
            (CssSelector(item="menu"), CssSelector(item="dir")),
            (CssSelector(item="menu"), CssSelector(item="menu")),
            (CssSelector(item="ul"), CssSelector(item="dir")),
            (CssSelector(item="ul"), CssSelector(item="menu")),
            (CssSelector(item="ul"), CssSelector(item="ul")),
        ): {"margin_top": "0em", "margin_bottom": "0em", "list_style_type": "circle"},
        (
            (CssSelector(item="dir"), CssSelector(item="dl")),
            (CssSelector(item="dir"), CssSelector(item="ol")),
            (CssSelector(item="dl"), CssSelector(item="dir")),
            (CssSelector(item="dl"), CssSelector(item="dl")),
            (CssSelector(item="dl"), CssSelector(item="ol")),
            (CssSelector(item="dl"), CssSelector(item="menu")),
            (CssSelector(item="dl"), CssSelector(item="ul")),
            (CssSelector(item="ol"), CssSelector(item="dl")),
            (CssSelector(item="ol"), CssSelector(item="ol")),
            (CssSelector(item="menu"), CssSelector(item="dl")),
            (CssSelector(item="menu"), CssSelector(item="ol")),
            (CssSelector(item="ul"), CssSelector(item="dl")),
            (CssSelector(item="ul"), CssSelector(item="ol")),
        ): {"margin_top": "0em", "margin_bottom": "0em"},
        ((CssSelector(item="menu"), CssSelector(item="ul")),): {
            "list_style_type": "circle",
            "margin_top": "0em",
            "margin_bottom": "0em",
        },
        (
            (CssSelector(item="dir"), CssSelector(item="dir"), CssSelector(item="dir")),
            (
                CssSelector(item="dir"),
                CssSelector(item="dir"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="dir"), CssSelector(item="dir"), CssSelector(item="ul")),
            (
                CssSelector(item="dir"),
                CssSelector(item="menu"),
                CssSelector(item="dir"),
            ),
            (
                CssSelector(item="dir"),
                CssSelector(item="menu"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="dir"), CssSelector(item="menu"), CssSelector(item="ul")),
            (CssSelector(item="dir"), CssSelector(item="ol"), CssSelector(item="dir")),
            (CssSelector(item="dir"), CssSelector(item="ol"), CssSelector(item="menu")),
            (CssSelector(item="dir"), CssSelector(item="ol"), CssSelector(item="ul")),
            (CssSelector(item="dir"), CssSelector(item="ul"), CssSelector(item="dir")),
            (CssSelector(item="dir"), CssSelector(item="ul"), CssSelector(item="menu")),
            (CssSelector(item="dir"), CssSelector(item="ul"), CssSelector(item="ul")),
            (
                CssSelector(item="menu"),
                CssSelector(item="dir"),
                CssSelector(item="dir"),
            ),
            (
                CssSelector(item="menu"),
                CssSelector(item="dir"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="menu"), CssSelector(item="dir"), CssSelector(item="ul")),
            (
                CssSelector(item="menu"),
                CssSelector(item="menu"),
                CssSelector(item="dir"),
            ),
            (
                CssSelector(item="menu"),
                CssSelector(item="menu"),
                CssSelector(item="menu"),
            ),
            (
                CssSelector(item="menu"),
                CssSelector(item="menu"),
                CssSelector(item="ul"),
            ),
            (CssSelector(item="menu"), CssSelector(item="ol"), CssSelector(item="dir")),
            (
                CssSelector(item="menu"),
                CssSelector(item="ol"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="menu"), CssSelector(item="ol"), CssSelector(item="ul")),
            (CssSelector(item="menu"), CssSelector(item="ul"), CssSelector(item="dir")),
            (
                CssSelector(item="menu"),
                CssSelector(item="ul"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="menu"), CssSelector(item="ul"), CssSelector(item="ul")),
            (CssSelector(item="ol"), CssSelector(item="dir"), CssSelector(item="dir")),
            (CssSelector(item="ol"), CssSelector(item="dir"), CssSelector(item="menu")),
            (CssSelector(item="ol"), CssSelector(item="dir"), CssSelector(item="ul")),
            (CssSelector(item="ol"), CssSelector(item="menu"), CssSelector(item="dir")),
            (
                CssSelector(item="ol"),
                CssSelector(item="menu"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="ol"), CssSelector(item="menu"), CssSelector(item="ul")),
            (CssSelector(item="ol"), CssSelector(item="ol"), CssSelector(item="dir")),
            (CssSelector(item="ol"), CssSelector(item="ol"), CssSelector(item="menu")),
            (CssSelector(item="ol"), CssSelector(item="ol"), CssSelector(item="ul")),
            (CssSelector(item="ol"), CssSelector(item="ul"), CssSelector(item="dir")),
            (CssSelector(item="ol"), CssSelector(item="ul"), CssSelector(item="menu")),
            (CssSelector(item="ol"), CssSelector(item="ul"), CssSelector(item="ul")),
            (CssSelector(item="ul"), CssSelector(item="dir"), CssSelector(item="dir")),
            (CssSelector(item="ul"), CssSelector(item="dir"), CssSelector(item="menu")),
            (CssSelector(item="ul"), CssSelector(item="dir"), CssSelector(item="ul")),
            (CssSelector(item="ul"), CssSelector(item="menu"), CssSelector(item="dir")),
            (
                CssSelector(item="ul"),
                CssSelector(item="menu"),
                CssSelector(item="menu"),
            ),
            (CssSelector(item="ul"), CssSelector(item="menu"), CssSelector(item="ul")),
            (CssSelector(item="ul"), CssSelector(item="ol"), CssSelector(item="dir")),
            (CssSelector(item="ul"), CssSelector(item="ol"), CssSelector(item="menu")),
            (CssSelector(item="ul"), CssSelector(item="ol"), CssSelector(item="ul")),
            (CssSelector(item="ul"), CssSelector(item="ul"), CssSelector(item="dir")),
            (CssSelector(item="ul"), CssSelector(item="ul"), CssSelector(item="menu")),
            (CssSelector(item="ul"), CssSelector(item="ul"), CssSelector(item="ul")),
        ): {"list_style_type": "square"},
        ((CssSelector(item="li"),),): {"display": "list-item"},
        # Details & summary
        ((CssSelector(item="details"), CssSelector(item="summary")),): {
            "display": "list-item",
            "list_style_type": "disclosure-closed",
            "list_style_position": "inside",
        },
        ((CssSelector(item="details", attr="[open]"), CssSelector(item="summary")),): {
            "list_style_type": "disclosure-open",
            "display": "list-item",
        },
        # Dataframes for Jupyter
        ((CssSelector(item="table.dataframe"),),): {
            "border_top_width": "0 !important",
            "border_left_width": "0 !important",
            "border_bottom_width": "0 !important",
            "border_right_width": "0 !important",
            "border_collapse": "collapse",
            "_pt_class": "dataframe",
        },
        (
            (CssSelector(item="table.dataframe"), CssSelector(item="td")),
            (CssSelector(item="table.dataframe"), CssSelector(item="th")),
        ): {
            "border_top_width": "0",
            "border_left_width": "0",
            "border_bottom_width": "0",
            "border_right_width": "0",
            "padding_left": "1em",
        },
        (
            (
                CssSelector(item="table.dataframe"),
                CssSelector(item="th"),
            ),
        ): {
            "_pt_class": "dataframe,th",
        },
        (
            (
                CssSelector(item="table.dataframe"),
                CssSelector(item="th", pseudo=":first-child"),
            ),
            (
                CssSelector(item=".dataframe"),
                CssSelector(item="th", pseudo=":last-child"),
            ),
            (
                CssSelector(item=".dataframe"),
                CssSelector(item="td", pseudo=":last-child"),
            ),
        ): {"padding_right": "1em"},
        ((CssSelector(item="table.dataframe"), CssSelector(item="td")),): {
            "_pt_class": "dataframe,td"
        },
        (
            (
                CssSelector(item="table.dataframe"),
                CssSelector(item="tr", pseudo=":nth-child(odd)"),
                CssSelector(item="td"),
            ),
        ): {"_pt_class": "dataframe,row-odd,td"},
        ## Markdown specific
        # Set page margins only if we are rendering a markdown file
        ((CssSelector(item="::root", attr="[_initial_format=markdown]"),),): {
            "max_width": "100em",
            "margin_left": "auto",
            "margin_right": "auto",
        },
        ((CssSelector(item="::root", attr="[_base=.]"),),): {
            "max_width": "unset",
            "margin_left": "unset",
            "margin_right": "unset",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h1"),
            ),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h2"),
            ),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h3"),
            ),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h4"),
            ),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h5"),
            ),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h6"),
            ),
        ): {
            "text_align": "center",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h1"),
            ),
        ): {
            "font_weight": "bold",
            "text_decoration": "underline",
            "border_top_style": "double",
            "border_right_style": "double",
            "border_bottom_style": "double",
            "border_left_style": "double",
            "border_top_width": "0.34em",
            "border_right_width": "0.34em",
            "border_bottom_width": "0.34em",
            "border_left_width": "0.34em",
            "border_top_color": "ansiyellow",
            "border_right_color": "ansiyellow",
            "border_bottom_color": "ansiyellow",
            "border_left_color": "ansiyellow",
            "padding_bottom": "0",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h2"),
            ),
        ): {
            "font_weight": "bold",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.34em",
            "border_right_width": "0.34em",
            "border_bottom_width": "0.34em",
            "border_left_width": "0.34em",
            "border_top_color": "#888888",
            "border_right_color": "#888888",
            "border_bottom_color": "#888888",
            "border_left_color": "#888888",
            "padding_bottom": "0",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h3"),
            ),
        ): {
            "font_weight": "bold",
            "font_style": "italic",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.1em",
            "border_right_width": "0.1em",
            "border_bottom_width": "0.1em",
            "border_left_width": "0.1em",
            "border_top_color": "#888888",
            "border_right_color": "#888888",
            "border_bottom_color": "#888888",
            "border_left_color": "#888888",
            "margin_left": "auto",
            "margin_right": "auto",
            "padding_top": "0",
            "padding_right": "1em",
            "padding_bottom": "0",
            "padding_left": "1em",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h4"),
            ),
        ): {
            "text_weight": "bold",
            "text_decoration": "underline",
            "border_bottom_color": "#888888",
            "margin_top": "1rem",
            "margin_bottom": "1rem",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h5"),
            ),
        ): {
            "font_weight": "bold",
            "border_bottom_color": "#888888",
            "margin_top": "1rem",
            "margin_bottom": "1rem",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="h6"),
            ),
        ): {
            "font_style": "italic",
            "border_bottom_color": "#888888",
            "margin_top": "1rem",
            "margin_bottom": "1rem",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="ol"),
                CssSelector(item="li"),
                CssSelector(item="::marker"),
            ),
        ): {"color": "ansicyan"},
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="ul"),
                CssSelector(item="li"),
                CssSelector(item="::marker"),
            ),
        ): {"color": "ansiyellow"},
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="blockquote"),
            ),
        ): {
            "margin_top": "1em",
            "margin_bottom": "1em",
            "padding_left": "1em",
            "border_left_width": "thick",
            "border_left_style": "solid",
            "border_left_color": "darkmagenta",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item=".block"),
            ),
        ): {"display": "block"},
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="td"),
            ),
        ): {
            "display": "table-cell",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.1em",
            "border_right_width": "0.1em",
            "border_bottom_width": "0.1em",
            "border_left_width": "0.1em",
            "padding_left": "1em",
            "padding_right": "1em",
            # "_pt_class": "markdown,table,border",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="th"),
            ),
        ): {
            "display": "table-cell",
            "border_top_style": "solid",
            "border_right_style": "solid",
            "border_bottom_style": "solid",
            "border_left_style": "solid",
            "border_top_width": "0.34em",
            "border_right_width": "0.34em",
            "border_bottom_width": "0.34em",
            "border_left_width": "0.34em",
            "padding_left": "1em",
            "padding_right": "1em",
            "font_weight": "bold",
            # "_pt_class": "markdown,table,border",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="code"),
            ),
        ): {
            "display": "inline",
            "_pt_class": "markdown,code",
        },
        (
            (CssSelector(item="::latex"),),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item=".math"),
            ),
        ): {
            "_format": "latex",
            "text_transform": "latex",
            "display": "inline-block",
            "vertical_align": "top",
            "white_space": "pre",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item=".math.block"),
            ),
        ): {
            "text_align": "center",
            "display": "block",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="pre"),
                CssSelector(comb=">", item="code"),
            ),
        ): {
            "display": "block",
            "border_top_style": "solid",
            "border_top_width": "1px",
            "border_right_style": "solid",
            "border_right_width": "1px",
            "border_bottom_style": "solid",
            "border_bottom_width": "1px",
            "border_left_style": "solid",
            "border_left_width": "1px",
            "_pt_class": "markdown,code,block",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="pre"),
                CssSelector(comb=">", item="code"),
                CssSelector(item="*"),
            ),
        ): {
            "_pt_class": "markdown,code,block",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="img"),
            ),
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="svg"),
            ),
        ): {
            "display": "inline-block",
            "overflow_x": "hidden",
            "overflow_y": "hidden",
            "vertical_align": "middle",
        },
    },
    get_app().config.filters.wrap_cell_outputs: {
        ((CssSelector(item="table.dataframe"),),): {
            "max_width": "100%",
        },
        (
            (
                CssSelector(item="::root", attr="[_initial_format=markdown]"),
                CssSelector(item="pre"),
                CssSelector(comb=">", item="code"),
            ),
        ): {
            "max_width": "100%",
            "overflow_x": "auto",
        },
    },
}


class Node:
    """Represent an node in the DOM."""

    theme: Theme

    def __init__(
        self,
        dom: HTML,
        name: str,
        parent: Node | None,
        text: str = "",
        attrs: list[tuple[str, str | None]] | None = None,
        contents: list[Node] | None = None,
    ) -> None:
        """Create a new page element."""
        self.dom = dom
        self.name = name
        self.parent = parent
        self._text = text
        self.attrs: dict[str, Any] = {k: v for k, v in (attrs or []) if v is not None}
        self.contents: list[Node] = contents or []
        self.closed = False
        self.marker: Node | None = None
        self.theme = Theme(self, parent_theme=parent.theme if parent else None)

    def reset(self) -> None:
        """Reset the node and all its children."""
        for attr in list(self.__dict__.keys()):
            if isinstance(Node.__dict__.get(attr), cached_property):
                delattr(self, attr)
        self.theme.reset()
        for child in self.contents:
            child.reset()
        self.marker = None

    def _outer_html(self, d: int = 0, attrs: bool = True) -> str:
        dd = " " * d
        s = ""
        if self.name != "::text":
            s += f"{dd}<{self.name}"
            if attrs:
                for key, value in self.attrs.items():
                    s += f' {key}="{value}"'
            if self.name in _VOID_ELEMENTS:
                s += " />"
            else:
                s += ">"
                if self.contents:
                    for child in self.contents:
                        s += f"\n{dd} {child._outer_html(d + 1, attrs=attrs)}"
                    s += f"\n{dd}{dd}"
                s += f"</{self.name}>"
        else:
            s += f"{dd}{self.text}"
        return s

    def __lt__(self, other: Node) -> bool:
        """Use `order` attribute from theme as default sort parameter."""
        return self.theme.order < other.theme.order

    @cached_property
    def preceding_text(self) -> str:
        """Return the text preceding this element."""
        parent = self.parent
        # Move up to the current block element
        while parent and not (parent.theme.d_blocky or parent.theme.d_inline_block):
            parent = parent.parent
        if not parent:
            return ""

        def _text_descendents(node: Node) -> Generator[Node]:
            for child in node.contents:
                if child.name == "::text":
                    yield child
                elif (
                    child.contents
                    and (child.theme.d_inline or child.theme.d_inline_block)
                    and child.theme.in_flow
                ):
                    yield from _text_descendents(child)

        last_valid_text = ""
        for node in _text_descendents(parent):
            if node is self:
                return last_valid_text
            elif text := node.text:
                last_valid_text = text
        return ""

    @cached_property
    def text(self) -> str:
        """Get the element's computed text."""
        text = self._text

        # Allow replacing context of pseudo-elements
        if (
            (parent := self.parent)
            and parent.name.startswith("::")
            and (_text := parent.theme.theme.get("content", "").strip())
        ):
            if _text.startswith('"') and _text.endswith('"'):
                text = _text.strip('"')
            elif _text.startswith("'") and _text.endswith("'"):
                text = _text.strip("'")

        if text:
            if not (preformatted := self.theme.preformatted):
                # 1. All spaces and tabs immediately before and after a line break are ignored
                text = re.sub(r"(\s+(?=\n)|(?<=\n)\s+)", "", text, flags=re.MULTILINE)
                # 2. All tab characters are handled as space characters
                text = text.replace("\t", " ")
                # 3. Line breaks are converted to spaces
                text = text.replace("\n", " ")
                # 4. any space immediately following another space is ignored
                # (even across two separate inline elements)
                text = re.sub(r"\s\s+", " ", text)
                if not (
                    preceding_text := self.preceding_text
                ) or preceding_text.endswith(" "):
                    text = text.lstrip(" ")
                # 5. Sequences of spaces at the beginning and end of an element are removed
                if text:
                    parent = self.parent
                    while (
                        parent
                        and parent.is_first_child_element
                        and not parent.theme.d_blocky
                    ):
                        parent = parent.parent
                    if (
                        parent
                        and parent.theme.d_blocky
                        and text[0] == " "
                        and (self.is_first_child_node)
                    ):
                        text = text[1:]
                if text:
                    parent = self.parent
                    while (
                        parent
                        and parent.is_last_child_element
                        and not parent.theme.d_blocky
                    ):
                        parent = parent.parent
                    if text[-1] == " " and (self.is_last_child_node):
                        text = text[:-1]

                # Remove space around text in block contexts
                if (
                    text
                    and (node := self.prev_node)
                    and (node.theme.d_blocky or node.name == "br")
                ):
                    text = text.lstrip("\x20\x0a\x09\x0c\x0d")
                if (
                    text
                    and (node := self.next_node)
                    and (node.theme.d_blocky or node.name == "br")
                ):
                    text = text.rstrip(" \t\r\n\x0c")

            elif preformatted and self.is_last_child_node:
                # TODO - align tabstops
                text = text.replace("\t", "    ")
                # Remove one trailing newline
                if text[-1] == "\n":
                    text = text[:-1]

        return text

    def find_all(self, tag: str, recursive: bool = False) -> Iterator[Node]:
        """Find all child elements of a given tag type."""
        for element in self.contents:
            if element.name == tag:
                yield element

    @property
    def descendents(self) -> Generator[Node]:
        """Yield all descendent elements."""
        for child in self.contents:
            yield child
            yield from child.descendents

    @property
    def renderable_descendents(self) -> Generator[Node]:
        """Yield descendent elements with actual text content."""
        for child in self.contents:
            if child.theme.d_inline and child.contents and child.name != "::text":
                yield from child.renderable_descendents
            else:
                yield child

    @cached_property
    def parents(self) -> list[Node]:
        """Yield all parent elements."""
        parents = []
        parent = self.parent
        while parent is not None:
            parents.append(parent)
            parent = parent.parent
        return parents[::-1]

    @cached_property
    def is_first_child_node(self) -> bool:
        """True if the element if the first child node of its parent element."""
        if (parent := self.parent) and (child_nodes := parent.contents):
            return child_nodes[0] == self
        return False

    @cached_property
    def is_last_child_node(self) -> bool:
        """True if the element if the last child node of its parent element."""
        if (parent := self.parent) and (child_nodes := parent.contents):
            return child_nodes[-1] == self
        return False

    @property
    def child_elements(self) -> Generator[Node]:
        """Yield all of the child element nodes."""
        for child in self.contents:
            # Ignore text and comment nodes
            if child.name != "comment" and not child.name.startswith("::"):
                yield child

    @cached_property
    def first_child_element(self) -> Node | None:
        """Return the first child element."""
        try:
            return next(self.child_elements)
        except StopIteration:
            return None

    @cached_property
    def last_child_element(self) -> Node | None:
        """Return the last child element."""
        if child_elements := list(self.child_elements):
            return child_elements[-1]
        return None

    @cached_property
    def is_first_child_element(self) -> bool:
        """True if the element if the first child element of its parent element."""
        if parent := self.parent:
            try:
                return next(parent.child_elements) == self
            except StopIteration:
                pass
        return False

    @cached_property
    def is_last_child_element(self) -> bool:
        """True if the element if the last child element of its parent element."""
        if parent := self.parent:
            for child in reversed(parent.contents):
                # Ignore text and comment nodes
                if child.name != "comment" and not child.name.startswith("::"):
                    return child == self
        return False

    @cached_property
    def sibling_element_index(self) -> int | None:
        """Return the index of this element among its siblings."""
        if self.parent:
            for i, child in enumerate(self.parent.child_elements):
                if child is self:
                    return i
        return None

    @cached_property
    def sibling_flow_index(self) -> int | None:
        """Return the index of this element among its siblings."""
        if self.parent:
            for i, child in enumerate(
                child for child in self.parent.contents if child.theme.in_flow
            ):
                if child is self:
                    return i
        return None

    @cached_property
    def prev_node(self) -> Node | None:
        """Return the previous sibling node."""
        if parent := self.parent:
            prev_node = None
            for child in parent.contents:
                if child == self:
                    return prev_node
                prev_node = child
        return None

    @cached_property
    def next_node(self) -> Node | None:
        """Return the next sibling node."""
        if parent := self.parent:
            prev_child = None
            for child in parent.contents:
                if prev_child == self:
                    return child
                prev_child = child
        return None

    @cached_property
    def prev_node_in_flow(self) -> Node | None:
        """Get the previous node in the current element's flow."""
        prev_node = self.prev_node
        while prev_node and not prev_node.theme.in_flow:
            prev_node = prev_node.prev_node
        return prev_node

    @cached_property
    def next_node_in_flow(self) -> Node | None:
        """Get the next node in the current element's flow."""
        next_node = self.next_node
        while next_node and not next_node.theme.in_flow:
            next_node = next_node.next_node
        return next_node

    @cached_property
    def prev_element(self) -> Node | None:
        """Return the previous sibling element."""
        if parent := self.parent:
            prev_element = None
            for child in parent.child_elements:
                if child == self:
                    return prev_element
                prev_element = child
        return None

    @cached_property
    def next_element(self) -> Node | None:
        """Return the next sibling element."""
        if parent := self.parent:
            child_elements = parent.child_elements
            for child in child_elements:
                if child == self:
                    try:
                        return next(child_elements)
                    except StopIteration:
                        return None
        return None

    def __repr__(self, d: int = 0) -> str:
        """Return a string representation of the element."""
        parts = [
            self.name,
            *[f'{k}="{v}"' for k, v in self.attrs.items() if not k.startswith("_")],
        ]
        return f"<{' '.join(parts)}>"


class CustomHTMLParser(HTMLParser):
    """An HTML parser."""

    soup: Node
    curr: Node

    def __init__(self, dom: HTML) -> None:
        """Create a new parser instance."""
        super().__init__()
        self.dom = dom

    def parse(self, markup: str) -> Node:
        """Pare HTML markup."""
        # Ignore self-closing syntax - HTML5!
        markup = markup.replace("/>", ">")
        # Remove comments as they can confuse the parser if they contain close tags
        # markup = re.sub(r"<!--.*?-->", "", markup)
        soup = Node(
            name="::root",
            dom=self.dom,
            parent=None,
            attrs=[
                ("_initial_format", self.dom._initial_format),
                ("_base", str(self.dom.base)),
            ],
        )
        self.curr = soup
        self.feed(markup)
        return soup

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Open a new element."""
        self.autoclose()
        element = Node(dom=self.dom, name=tag, parent=self.curr, attrs=attrs)
        self.curr.contents.append(element)
        self.curr = element

    def autoclose(self) -> None:
        """Automatically close void elements."""
        if not self.curr.closed and self.curr.name in _VOID_ELEMENTS:
            self.curr.closed = True
            if self.curr.parent:
                self.curr = self.curr.parent

    def handle_data(self, data: str) -> None:
        """Create data (text) elements."""
        self.autoclose()
        self.curr.contents.append(
            Node(dom=self.dom, name="::text", text=data, parent=self.curr, attrs=[])
        )

    def handle_endtag(self, tag: str) -> None:
        """Handle end tags: close the currently opened element."""
        if tag != self.curr.name:
            self.autoclose()
        self.curr.closed = True
        if self.curr.parent:
            self.curr = self.curr.parent


def parse_style_sheet(css_str: str, dom: HTML, condition: Filter = always) -> None:
    """Collect all CSS styles from style tags."""
    dom_css = dom.css
    # Remove whitespace and newlines
    css_str = re.sub(r"\s*\n\s*", " ", css_str)
    # Remove comments
    css_str = re.sub(r"\/\*[^\*]+\*\/", "", css_str)
    # Replace ':before' and ':after' with '::before' and '::after'
    # for compatibility with old CSS and to make root selector work
    css_str = re.sub("(?<!:):(?=before|after|root)", "::", css_str)

    def parse_part(part_condition: Filter, css_str: str) -> None:
        """Parse a group of CSS rules."""
        if css_str:
            css_str = css_str.replace("\n", "").strip()
            if css_str:
                for rule in css_str.rstrip("}").split("}"):
                    selectors, _, content = rule.partition("{")
                    content = content.strip().rstrip(";")
                    rule_content = parse_css_content(content)
                    if rule_content:
                        parsed_selectors = tuple(
                            tuple(
                                CssSelector(**m.groupdict())
                                for m in _SELECTOR_RE.finditer(selector.strip())
                            )
                            for selector in map(str.strip, selectors.split(","))
                        )
                        rules = dom_css.setdefault(part_condition, {})
                        if parsed_selectors in rules:
                            rules[parsed_selectors].update(rule_content)
                        else:
                            rules[parsed_selectors] = rule_content

    # Split out nested at-rules - we need to process them separately
    for part in _AT_RULE_RE.split(css_str):
        if (
            part
            and part[0] == "@"
            and (m := _NESTED_AT_RULE_RE.match(part)) is not None
        ):
            m_dict = m.groupdict()
            # Process '@media' queries
            if m_dict["identifier"] == "media":
                # Split each query - separated by "or" or ","
                queries = re.split("(?: or |,)", m_dict["rule"])
                query_conditions: Filter = never
                for query in queries:
                    # Each query can be the logical sum of multiple targets
                    target_conditions: Filter = always
                    for target in query.split(" and "):
                        if (
                            target_m := _MEDIA_QUERY_TARGET_RE.match(target)
                        ) is not None:
                            target_m_dict = target_m.groupdict()
                            # Check for media type conditions
                            if (media_type := target_m_dict["type"]) is not None:
                                target_conditions &= (
                                    always if media_type in {"all", "screen"} else never
                                )
                            # Check for media feature conditions
                            elif (
                                media_feature := target_m_dict["feature"]
                            ) is not None:
                                target_conditions &= parse_media_condition(
                                    media_feature, dom
                                )
                            # Check for logical 'NOT' inverting the target condition
                            if target_m_dict["invert"]:
                                target_conditions = ~target_conditions
                    # Logical OR of all media queries
                    query_conditions |= target_conditions
                # Parse the @media CSS block (may contain nested at-rules)
                parse_style_sheet(m_dict["part"], dom, condition & query_conditions)
        # Parse the CSS and always use it
        else:
            parse_part(condition, part)


def parse_media_condition(condition: str, dom: HTML) -> Filter:
    """Convert media rules to conditions."""
    condition = condition.replace(" ", "")
    result: Filter

    for op_str, op_func in (("<=", le), (">=", ge), ("<", lt), (">", gt), ("=", eq)):
        if op_str in condition:
            operator = op_func
            feature, _, value = condition.partition(op_str)
            break
    else:
        feature, _, value = condition.partition(":")
        if feature.startswith("max-"):
            operator = le
            feature = feature[4:]
        elif feature.startswith("min-"):
            operator = ge
            feature = feature[4:]
        else:
            operator = eq

    if feature == "width":
        result = Condition(
            lambda: operator(
                width := dom.width or 80,
                css_dimension(value, vertical=False, available=width) or 80,
            )
        )
    elif feature == "height":
        result = Condition(
            lambda: operator(
                height := dom.height or 24,
                css_dimension(value, vertical=True, available=height) or 24,
            )
        )
    elif feature == "aspect":
        result = Condition(
            lambda: operator(
                (width := (dom.width or 80)) / (height := (dom.height or 24)),
                (
                    80
                    if (dim := css_dimension(value, vertical=False, available=width))
                    is None
                    else dim
                )
                / (
                    24
                    if (dim := css_dimension(value, vertical=True, available=height))
                    is None
                    else dim
                ),
            )
        )

    elif feature == "device-width":
        result = Condition(
            lambda: operator(
                (
                    output.get_size()
                    if (output := get_app_session()._output)
                    else Size(24, 80)
                ).columns,
                css_dimension(value, vertical=False, available=dom.width) or 80,
            )
        )
    elif feature == "device-height":
        result = Condition(
            lambda: operator(
                (
                    output.get_size()
                    if (output := get_app_session()._output)
                    else Size(24, 80)
                ).rows,
                css_dimension(value, vertical=True, available=dom.height) or 24,
            )
        )
    elif feature == "device-aspect":
        result = Condition(
            lambda: operator(
                (
                    size := (
                        output.get_size()
                        if (output := get_app_session()._output)
                        else Size(24, 80)
                    )
                ).columns
                / size.rows,
                (css_dimension(value, vertical=False, available=dom.width) or 1)
                / (css_dimension(value, vertical=True, available=dom.height) or 1),
            )
        )

    # elif feature == "color":
    #     Check output color depth

    else:
        result = always

    return result


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    def __init__(
        self,
        markup: str,
        base: Path | str | None = None,
        width: int | None = None,
        height: int | None = None,
        collapse_root_margin: bool = False,
        fill: bool = True,
        css: CssSelectors | None = None,
        browser_css: CssSelectors | None = None,
        mathjax: FilterOrBool = True,
        mouse_handler: Callable[[Node, MouseEvent], NotImplementedOrNone] | None = None,
        paste_fixed: bool = True,
        defer_assets: bool = False,
        on_update: Callable[[HTML], None] | None = None,
        on_change: Callable[[HTML], None] | None = None,
        _initial_format: str = "",
    ) -> None:
        """Initialize the markdown formatter.

        Args:
            markup: The markdown text to render
            base: The base url for the HTML dom
            width: The width in characters available for rendering. If :py:const:`None`
                the terminal width will be used
            height: The width in characters available for rendering. If :py:const:`None`
                the terminal height will be used
            collapse_root_margin: If :py:const:`True`, margins of the root element will
                be collapsed
            fill: Whether remaining space in block elements should be filled
            css: Base CSS to apply when rendering the HTML
            browser_css: The browser CSS to use
            mathjax: Whether to search for LaTeX in MathJax tags
            mouse_handler: A mouse handler function to use when links are clicked
            paste_fixed: Whether fixed elements should be pasted over the output
            defer_assets: Whether to render the page before remote assets are loaded
            on_update: An optional callback triggered when the DOM updates
            on_change: An optional callback triggered when the DOM changes
            _initial_format: The initial format of the data being displayed

        """
        self.markup = markup.strip()
        self.base = UPath(base or ".")
        self.title = ""

        self.browser_css = browser_css or _BROWSER_CSS
        self.css: CssSelectors = css or {}
        self.mathjax = to_filter(mathjax)
        self.defer_assets = defer_assets

        self.render_count = 0
        self.width = width
        self.height = height

        self.fill = fill
        self.collapse_root_margin = collapse_root_margin
        self.paste_fixed = paste_fixed
        self._initial_format = _initial_format

        self.graphic_data: set[Datum] = set()
        self.mouse_handler = mouse_handler

        self.formatted_text: StyleAndTextTuples = []
        self.floats: dict[tuple[int, DiBool, DiInt], StyleAndTextTuples] = {}
        self.fixed: dict[tuple[int, DiBool, DiInt], StyleAndTextTuples] = {}
        self.fixed_mask: StyleAndTextTuples = []
        # self.anchors = []
        self.on_update = Event(self, on_update)
        self.on_change = Event(self, on_change)

        self._dom_processed = False
        self._assets_loaded = False
        self._url_cbs: dict[Path, Callable[[Any], None]] = {}
        self._url_fs_map: dict[Path, AbstractFileSystem] = {}

    # Lazily load attributes

    @cached_property
    def parser(self) -> CustomHTMLParser:
        """Load the HTML parser."""
        return CustomHTMLParser(self)

    @cached_property
    def soup(self) -> Node:
        """Parse the markup."""
        return self.parser.parse(self.markup)

    def process_dom(self) -> None:
        """Load CSS styles and image resources.

        Do not touch element's themes!
        """
        mathjax = self.mathjax()

        def _process_css(data: bytes) -> None:
            try:
                css_str = data.decode()
            except Exception:
                log.warning("Error decoding stylesheet '%s...'", data[:20])
            else:
                parse_style_sheet(css_str, self)

        def _process_img(child: Node, data: bytes) -> None:
            child.attrs["_data"] = data
            del child.attrs["_missing"]

        for child in self.soup.descendents:
            # Set base
            if child.name == "base":
                if href := child.attrs.get("href"):
                    self.base = self.base.joinuri(href)

            # Set title
            elif child.name == "title":
                if contents := child.contents:
                    self.title = contents[0]._text.strip()
                    self.on_update.fire()

            # In case of a <link> style, load the url
            elif (
                child.name == "link"
                and (
                    (attrs := child.attrs).get("rel") == "stylesheet"
                    or (attrs.get("rel") == "preload" and attrs.get("as") == "style")
                )
                and (href := attrs.get("href", ""))
            ):
                url = self.base.joinuri(href)
                fs, url = url_to_fs(str(url))
                self._url_fs_map[url] = fs
                self._url_cbs[url] = _process_css

            # In case of a <style> tab, load first child's text
            elif child.name == "style":
                if child.contents:
                    # Use unprocessed text attribute to avoid loading the element's theme
                    css_str = child.contents[0]._text
                    parse_style_sheet(css_str, self)

            # Load images
            elif child.name == "img" and (src := child.attrs.get("src")):
                child.attrs["_missing"] = "true"
                url = self.base.joinuri(src)
                fs, url = url_to_fs(str(url))
                self._url_fs_map[url] = fs
                self._url_cbs[url] = partial(_process_img, child)

            # Convert non-HTML MathJax tags in texts to <::latex> special tags
            elif mathjax and child.name == "::text":
                text = child._text
                nodes = []
                while text:
                    # Split out MathJax parts
                    if (match := re.match(_MATHJAX_TAG_RE, text)) is not None:
                        groups = match.groupdict()
                        before = groups["beginning"]
                        latex = groups["display_bracket"] or groups["display_dollar"]
                        b_attrs: list[tuple[str, str | None]] | None
                        if latex:
                            b_attrs = [("style", "display: block")]
                        else:
                            latex = groups["inline_bracket"] or groups["inline_dollar"]
                            b_attrs = []
                        text = groups["end"]
                    else:
                        break
                    # Add the text before the MathJax tag
                    if before:
                        nodes.append(
                            Node(
                                dom=self,
                                name="::text",
                                parent=child.parent,
                                text=before,
                            )
                        )
                    # Add the LaTeX node
                    if latex:
                        latex_node = Node(
                            dom=self, name="::latex", parent=child.parent, attrs=b_attrs
                        )
                        latex_node.contents = [
                            Node(dom=self, name="::text", parent=latex_node, text=latex)
                        ]
                        nodes.append(latex_node)
                if nodes:
                    parent = child.parent
                    # Add a text node for any remaining text
                    if text:
                        nodes.append(
                            Node(dom=self, name="::text", parent=parent, text=text)
                        )
                    # Replace the original text node with the new nodes
                    if parent is not None:
                        index = parent.contents.index(child)
                        parent.contents[index : index + 1] = nodes

            # Add pseudo-elements just before rendering
            if child.name not in _VOID_ELEMENTS and not child.name.startswith("::"):
                before_node = Node(dom=self, name="::before", parent=child)
                before_node.contents.append(
                    Node(dom=self, name="::text", parent=before_node)
                )
                after_node = Node(dom=self, name="::after", parent=child)
                after_node.contents.append(
                    Node(dom=self, name="::text", parent=after_node)
                )
                child.contents = [before_node, *child.contents, after_node]

        self._dom_processed = True

    async def load_assets(self) -> None:
        """Load remote assets asynchronously."""
        self._assets_loaded = True

        # Load all remote assets for each protocol using fsspec (where they are loaded
        # asynchronously in their own thread) and trigger callbacks if the file is
        # loaded successfully
        fs_url_map = {
            fs: [url for url, f in self._url_fs_map.items() if f == fs]
            for fs in set(self._url_fs_map.values())
        }
        for fs, urls in fs_url_map.items():
            try:
                results = fs.cat(urls, recursive=False, on_error="return")
            except Exception:
                log.warning("Error connecting to %s", fs)
            else:
                # for url, result in zip(urls, results.values()):
                for url, result in results.items():
                    if not isinstance(result, Exception):
                        log.debug("File %s loaded", url)
                        self._url_cbs[url](result)
                    else:
                        log.warning("Error loading %s", url)

        # Reset all nodes so they will update with the new CSS from assets
        if self.defer_assets:
            self.soup.reset()

    def render(self, width: int | None, height: int | None) -> StyleAndTextTuples:
        """Render the current markup at a given size."""
        loop = get_or_create_loop("convert")
        return run_coro_sync(self._render(width, height), loop)

    async def _render(
        self, width: int | None, height: int | None
    ) -> StyleAndTextTuples:
        """Render the current markup at a given size, asynchronously."""
        # log.debug("Rendering at (%r, %r)", width, height)
        no_w = width is None and self.width is None
        no_h = height is None and self.height is None
        if no_w or no_h:
            size = get_app_session().output.get_size()
            if no_w:
                width = size.columns
            if no_h:
                height = size.rows
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        assert self.width is not None
        assert self.height is not None

        # The soup gets parsed when we load assets, and asset data gets attached to it
        if not self._dom_processed:
            self.process_dom()
        if not self.defer_assets and not self._assets_loaded:
            await self.load_assets()

        ft = await self.render_element(
            self.soup,
            available_width=self.width,
            available_height=self.height,
            fill=self.fill,
        )

        # Apply "ReverseOverwrite"s
        ft = apply_reverse_overwrites(ft)

        # Apply floats and fixed elements

        def _paste_floats(
            floats: dict[tuple[int, DiBool, DiInt], StyleAndTextTuples],
            lower_ft: StyleAndTextTuples,
        ) -> StyleAndTextTuples:
            """Paste floats on top of rendering."""
            lower_ft_height = None
            for (_, anchors, position), float_ft in sorted(floats.items()):
                row = col = 0
                if anchors.top:
                    row = position.top
                elif anchors.bottom:
                    if lower_ft_height is None:
                        lower_ft_height = sum(1 for _ in split_lines(lower_ft))
                    row = (
                        lower_ft_height
                        - sum(1 for _ in split_lines(float_ft))
                        - position.bottom
                    )
                if anchors.left:
                    col = position.left
                elif anchors.right:
                    row = (
                        max_line_width(lower_ft)
                        - max_line_width(float_ft)
                        - position.right
                    )
                lower_ft = paste(float_ft, lower_ft, row, col)
            return lower_ft

        # Draw floats
        if self.floats:
            ft = _paste_floats(self.floats, ft)

        # Paste floats onto a mask, then onto the rendering if required
        if self.fixed:
            assert self.width is not None
            assert self.height is not None
            fixed_mask = cast(
                "StyleAndTextTuples", [("", (" " * self.width) + "\n")] * self.height
            )
            fixed_mask = _paste_floats(self.fixed, fixed_mask)
            fixed_mask = apply_reverse_overwrites(fixed_mask)
            if self.paste_fixed:
                ft = paste(fixed_mask, ft, 0, 0, transparent=True)
            self.fixed_mask = fixed_mask
        else:
            self.fixed_mask = []

        self.render_count += 1
        self.formatted_text = ft

        # Load assets after initial render and request a re-render when loaded
        if self.defer_assets and not self._assets_loaded:
            loop = asyncio.get_event_loop()
            task = loop.create_task(self.load_assets())
            task.add_done_callback(lambda fut: self.on_change.fire())

        return ft

    async def render_element(
        self,
        element: Node,
        available_width: int,
        available_height: int,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render a Node."""
        # Update the element theme with the available space
        theme = element.theme
        theme.update_space(available_width, available_height)

        # Render the contents
        if theme.d_table:
            render_func = self.render_table_content

        elif theme.d_list_item:
            render_func = self.render_list_item_content

        elif theme.d_grid:
            render_func = self.render_grid_content

        elif theme.latex:
            render_func = self.render_latex_content

        else:
            name = element.name.lstrip(":")
            render_func = getattr(
                self, f"render_{name}_content", self.render_node_content
            )

        # Render the element
        ft = await render_func(element, left, fill, align_content)

        # Format the contents
        ft = await self.format_element(ft, element, left, fill, align_content)

        return ft

    async def render_text_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render a text element.

        Args:
            element: The page element to render
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            fill: Whether to fill the remainder of the rendered space with whitespace
            align_content: Whether to align the element's content

        Returns:
            Formatted text

        """
        ft: StyleAndTextTuples = []

        text = await element.theme.text_transform(element.text)

        if parent_theme := element.theme.parent_theme:
            style = parent_theme.style
        else:
            style = ""

        ft.append((style, text))
        return ft

    async def render_details_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render details, showing summary at the top and hiding contents if closed."""
        ft = []
        theme = element.theme
        summary = None
        contents = []
        for child in element.contents:
            if not summary and child.name == "summary":
                summary = child
            else:
                contents.append(child)
        if summary:
            ft += await self.render_element(
                summary,
                available_width=theme.content_width,
                available_height=theme.content_height,
                left=left,
                fill=fill,
            )
        if "open" in element.attrs and contents:
            # Create a dummy node with non-summary children and render it
            node = Node(dom=self, name="::content", parent=element, contents=contents)
            ft += [("", "\n")]
            ft += await self.render_element(
                node,
                available_width=theme.content_width,
                available_height=theme.content_height,
                left=left,
                fill=fill,
            )
        return ft

    async def render_ol_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render lists, adding item numbers to child <li> elements."""
        # Assign a list index to each item. This can be set via the 'value' attributed
        _curr = 0
        for item in element.find_all("li"):
            _curr += 1
            _curr = int(item.attrs.setdefault("value", str(_curr)))
        # Render list as normal
        return await self.render_node_content(
            element=element,
            left=left,
            fill=fill,
            align_content=align_content,
        )

    render_ul_content = render_ol_content

    async def render_list_item_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render a list item."""
        # Get element theme
        theme = element.theme
        # Get the bullet style
        list_style = theme.list_style_type
        bullet = list_style
        if list_style == "decimal":
            bullet = f"{element.attrs['value']}."
        # Add bullet element
        if bullet:
            bullet_element = Node(dom=self, name="::marker", parent=element)
            bullet_element.contents.append(
                Node(dom=self, name="::text", parent=bullet_element, text=bullet)
            )
            if theme.list_style_position == "inside":
                element.contents.insert(0, bullet_element)
            else:
                element.marker = bullet_element
        # Render the list item
        ft = await self.render_node_content(
            element,
            left=left,
            fill=fill,
            align_content=align_content,
        )
        return ft

    async def render_table_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render a HTML table element.

        Args:
            element: The list of parsed elements to render
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            fill: Whether to fill the remainder of the rendered space with whitespace
            align_content: Whether to align the element's content

        Returns:
            Formatted text

        """
        ft = []

        table_theme = element.theme
        table_x_dim = Dimension(
            min=table_theme.min_width,
            preferred=table_theme.content_width if "width" in table_theme else None,
            max=table_theme.max_width,
        )

        table = Table(
            width=table_x_dim,
            expand="width" in table_theme,
            align=table_theme.text_align,
            style=table_theme.style,
            padding=DiInt(0, 0, 0, 0),
            border_line=table_theme.border_line,
            border_style=table_theme.border_style,
            border_visibility=table_theme.border_visibility,
        )

        td_map = {}

        # Stack the elements in the shape of the table
        async def render_rows(elements: list[Node]) -> None:
            for tr in elements:
                if tr.name == "tr":
                    tr_theme = tr.theme
                    # tr_theme.update_space(available_width, available_height)
                    row = table.new_row(
                        align=tr_theme.text_align,
                        style=tr_theme.style,
                        border_line=tr_theme.border_line,
                        border_style=tr_theme.border_style,
                        border_visibility=tr_theme.border_visibility,
                    )
                    for td in tr.contents:
                        if td.name in ("th", "td"):
                            td_theme = td.theme
                            td_theme.update_space(
                                table_theme.content_width
                                or table_theme.available_width,
                                table_theme.content_height
                                or table_theme.available_width,
                            )
                            cell = row.new_cell(
                                text=await self.render_node_content(
                                    td,
                                    left=0,
                                    align_content=False,
                                    fill=False,
                                ),
                                padding=td_theme.padding,
                                border_line=td_theme.border_line,
                                border_style=td_theme.border_style,
                                align=td_theme.text_align,
                                colspan=try_eval(td.attrs.get("colspan", 1)),
                                rowspan=try_eval(td.attrs.get("rowspan", 1)),
                                style=td_theme.style + " nounderline",
                                width=td_theme.width if "width" in td_theme else None,
                                border_visibility=td_theme.border_visibility,
                            )
                            # Save for later so we can add the contents once all the
                            # cells are created and we can calculate the cell widths
                            td_map[cell] = td

        # Render the table head
        for child in element.find_all("thead", recursive=False):
            await render_rows(child.contents)
        # Render the table body
        for child in element.find_all("tbody", recursive=False):
            await render_rows(child.contents)
        # Render rows not in a head / body / foot as part of the body
        await render_rows(element.contents)
        for child in element.find_all("tfoot", recursive=False):
            await render_rows(child.contents)

        # TODO - process <colgroup> elements

        # Add cell contents
        if td_map:
            col_widths = table.calculate_col_widths()
            for row in table.rows:
                for col_width, cell in zip(col_widths, row.cells):
                    if td := td_map.get(cell):
                        cell_padding = compute_padding(cell)
                        available_width = (
                            table_x_dim.max
                            if cell.colspan > 1
                            else col_width - cell_padding.left - cell_padding.right
                        )
                        td.theme.update_space(
                            available_width, table_theme.available_height
                        )
                        cell.text = await self.render_node_content(
                            td,
                            # TODO - get actual colspan cell widths properly
                            left=0,
                        )

        # Render the table
        ft_table = table.render()

        # Render the caption
        # TODO - support "caption-side" css
        captions = element.find_all("caption", recursive=False)
        if captions:
            table_width = max_line_width(ft_table)
            for child in captions:
                ft_caption = await self.render_element(
                    child,
                    available_width=table_width,
                    available_height=table_theme.available_height,
                    left=0,
                    fill=True,
                )
                if ft_caption:
                    ft.extend([*ft_caption, ("", "\n")])

        ft.extend(ft_table)

        return ft

    async def render_grid_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render a element with ``display`` set to ``grid``.

        Args:
            element: The list of parsed elements to render
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            fill: Whether to fill the remainder of the rendered space with whitespace
            align_content: Whether to align the element's content

        Returns:
            Formatted text

        """
        theme = element.theme
        theme_style = theme.style
        table = Table(
            style=theme.style,
            padding=DiInt(0, 0, 0, 0),
            width=theme.content_width,
            expand=False,
            background_style=theme_style,
        )

        available_width = theme.content_width
        available_height = theme.content_height

        # TODO - calculate grid row heights

        col_width_template, _row_height_template = theme.grid_template
        grid_areas = theme.grid_areas or {0: {}}
        n_cols = max(len(col_width_template), len(grid_areas[0]))
        td_map = {}

        # Assign items to their positions in the table

        ## Sort children into those assigned a grid area and those unassigned
        child_areas: dict[str, Node] = {}
        remainder = []
        for child in element.contents:  # Sort by CSS `order
            if ga := child.theme.grid_area:
                child_areas[ga] = child
            else:
                remainder.append(child)

        ## Place children assigned a grid area their positions
        done = set()
        for y, grid_row in grid_areas.items():
            for x, area in grid_row.items():
                if area not in done and area in child_areas:
                    child = child_areas.pop(area)
                    colspan = 1
                    for i in range(x + 1, len(grid_row)):
                        if grid_row[i] == area:
                            colspan += 1
                        else:
                            break
                    rowspan = 1
                    for i in range(y + 1, len(grid_areas)):
                        if grid_areas[i][x + colspan - 1] == area:
                            rowspan += 1
                        else:
                            break

                    # Add a cell child to the table for this child
                    cell = Cell(
                        colspan=colspan,
                        rowspan=rowspan,
                        style=child.theme.style,
                        border_line=NoLine,
                        border_style=theme_style,
                    )
                    table._rows[y].add_cell(cell, index=x)
                    td_map[cell] = child
                    done.add(area)

        table.sync_rows_to_cols()

        ## Place children without a grid area wherever they fit
        x = y = 0
        for child in sorted((*child_areas.values(), *remainder)):
            child_theme = child.theme

            # Skip whitespace
            if not child_theme.in_flow:
                continue

            colspan = child_theme.grid_column_span

            # Find next available cell
            # Or skip cells to get to the child's assigned column
            # or skip cells until cell fits
            col_start = child_theme.grid_column_start
            while (
                x in table._rows[y]._cells
                or (x > 0 and (x + colspan) > n_cols)
                or (col_start is not None and x != col_start)
            ):
                x += 1
                if x >= n_cols:
                    y += 1
                    x = 0

            # Add a cell child to the table for this child
            cell = Cell(
                colspan=colspan,
                style=child_theme.style,
                border_line=NoLine,
                border_style=theme_style,
            )
            table._rows[y].add_cell(cell, index=x)
            td_map[cell] = child

        table.sync_rows_to_cols()

        # Remove outer-most cell borders, and set grid gap
        gap_x, gap_y = map(bool, theme.gap)
        border_visibility = DiBool(gap_y, gap_x, gap_y, gap_x)
        for rowcols, directionss in (
            (table._cols.values(), ("top", "bottom")),
            (table._rows.values(), ("left", "right")),
        ):
            for rowcol in rowcols:
                if cells := rowcol._cells:
                    for func, direction in zip((min, max), directionss):
                        cell = cells[func(cells)]
                        cell.border_visibility = (
                            cell.border_visibility or border_visibility
                        )._replace(**{direction: False})

        # Calculate column widths
        n_cols = len(table._cols)
        available = available_width - gap_x * (n_cols - 1)
        col_widths = {}
        frs = {}
        for x, item in enumerate(col_width_template):
            if item.endswith("fr"):
                frs[x] = css_dimension(item, available=available) or 1
            # TODO
            elif item == "min-content":
                content_widths = []
                for cell in table._cols[x]._cells.values():
                    if cell in td_map:
                        content_widths.append(td_map[cell].theme.min_content_width)
                if content_widths:
                    col_widths[x] = max(content_widths)
            # elif item == "max-content":
            #     content_widths = []
            #     for cell in table._cols[x]._cells.values():
            #         if cell in td_map:
            #           content_widths.append(td_map[cell].theme.max_content_width)
            # if content_widths:
            # col_widths[x] = max(content_widths)
            # elif item.startwith("min-max"): # TODO
            elif (
                value := css_dimension(item, vertical=False, available=available)
            ) is not None:
                col_widths[x] = round(value)
            else:
                # Give remaining columns one fraction
                frs[x] = 1

        # Any undefined columns are min-content
        for x in set(range(n_cols)) - col_widths.keys() - frs.keys():
            frs[x] = 1

        ## Divide reminder between `fr` columns
        if frs:
            fr_available = available - sum(filter(None, col_widths.values()))
            fr_count = sum(frs.values())
            for x, value in frs.items():
                col_widths[x] = round(value / fr_count * fr_available)

        # Add remainder to last column to ensure column widths sum to available space
        if n_cols:
            col_widths[n_cols - 1] += available - sum(col_widths.values())

        # Set cell widths
        for row in table._rows.values():
            for x, cell in row._cells.items():
                colspan = cell.colspan
                cell.width = sum(col_widths[x + i] for i in range(colspan)) + gap_x * (
                    colspan - 1
                )

        # Allow the table to adjust given cell widths to the available space
        cell_widths = table.calculate_cell_widths(available_width)

        # Render cell contents at the final calculated widths
        async def _render_cell(cell: Cell, td: Node, width: int, height: int) -> None:
            cell.text = await self.render_element(
                td,
                available_width=width,
                available_height=height,
                left=0,
                fill=True,
                align_content=align_content,
            )

        coros = []
        for row in table._rows.values():
            for cell in row._cells.values():
                if td := td_map.get(cell):
                    width = cell_widths[cell]
                    td.theme.update_space(width, theme.available_height)
                    coros.append(
                        _render_cell(
                            cell, td, width or available_width, available_height
                        )
                    )
        await asyncio.gather(*coros)

        return table.render()

    async def render_latex_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render LaTeX math content."""
        theme = element.theme

        # Render text representation
        ft: StyleAndTextTuples = await self.render_node_content(
            element, left=0, fill=False, align_content=False
        )

        # Render graphic representation
        latex = element.text + "".join(
            child.text for child in element.renderable_descendents
        )
        latex = f"${latex}$"
        if element.theme.d_blocky:
            latex = f"${latex}$"
        datum = Datum(
            latex,
            "latex",
            fg=theme.color or None,
            bg=theme.background_color or None,
            align=WindowAlign.CENTER,
        )
        self.graphic_data.add(datum)

        # Calculate size and pad text representation
        cols, aspect = await datum.cell_size_async()
        rows = max(len(list(split_lines(ft))), ceil(cols * aspect))
        cols = max(cols, max_line_width(ft))

        key = datum.add_size(Size(rows, cols))
        ft = [(f"[Graphic_{key}]", ""), *ft]
        ft = valign(ft, height=rows, how=FormattedTextVerticalAlign.TOP)
        return ft

    @overload
    async def _render_image(
        self, data: bytes, format_: str, theme: Theme, path: Path | None = None
    ) -> StyleAndTextTuples: ...

    @overload
    async def _render_image(
        self, data: str, format_: str, theme: Theme, path: Path | None = None
    ) -> StyleAndTextTuples: ...

    async def _render_image(self, data, format_, theme, path=None):
        """Render an image and prepare graphic representation."""
        datum = Datum(
            data,
            format_,
            path=path,
        )
        # Keep reference to this graphic
        self.graphic_data.add(datum)
        # Scale down the image to fit to width
        cols, aspect = await datum.cell_size_async()

        if content_width := theme.content_width:
            cols = content_width if cols == 0 else min(content_width, cols)
        rows = ceil(cols * aspect)

        # Convert the image to formatted-text
        ft = (
            await datum.convert_async(
                to="ft",
                cols=cols,
                rows=rows or None,
                fg=theme.color,
                bg=theme.background_color,
            )
            or []
        )
        # Remove trailing new-lines
        ft = strip(ft, chars="\n", left=False)

        # If we couldn't calculate the image size, use the size of the text output
        if rows == 0 and cols:
            rows = min(theme.content_height, len(list(split_lines(ft))))
            aspect = rows / cols

        # Store reference to image element
        key = Datum.add_size(datum, Size(rows, cols))

        return cast(
            "StyleAndTextTuples",
            # Flag graphic position
            [(f"[Graphic_{key}]", "")]
            # Set default background color on generated content
            + [(f"{theme.style} {style}", (text), *rest) for style, text, *rest in ft],
        )

    async def render_img_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render an image's content."""
        theme = element.theme
        content_width = theme.content_width
        # content_height = theme.content_height
        src = str(element.attrs.get("src", ""))
        path = self.base.joinuri(src)

        if not element.attrs.get("_missing") and (data := element.attrs.get("_data")):
            # Display it graphically
            format_ = get_format(path, default="png")
            ft = await self._render_image(data, format_, theme, path)

        else:
            style = f"class:image,placeholder {theme.style}"
            ft = [(style, "🌄")]
            if content_width and content_width >= 7:
                ft.extend(
                    [
                        (style, " "),
                        (
                            style,
                            (
                                element.attrs.get("alt")
                                or (path.name if path else "Image")
                            ),
                        ),
                    ]
                )

        return ft

    async def render_svg_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Display images rendered as ANSI art."""
        theme = element.theme
        # HTMLParser clobbers the case of element attributes
        element.attrs["xmlns"] = "http://www.w3.org/2000/svg"
        element.attrs["xmlns:xlink"] = "http://www.w3.org/1999/xlink"
        # We fix the SVG viewBox here
        data = element._outer_html().replace(" viewbox=", " viewBox=")
        # Replace "currentColor" with theme foreground color
        data = data.replace("currentColor", theme.color)
        ft = await self._render_image(data, "svg", theme)
        return ft

    async def render_input_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Render an input element."""
        attrs = element.attrs
        element.contents.insert(
            0,
            Node(
                dom=self,
                name="::text",
                parent=element,
                text=attrs.get("value", attrs.get("placeholder", " ")) or " ",
            ),
        )
        ft = await self.render_node_content(
            element,
            left=left,
            fill=fill,
            align_content=align_content,
        )
        return ft

    async def render_node_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Generate flows for the contents of the element."""
        ft: StyleAndTextTuples = []

        ft_left: StyleAndTextTuples
        ft_middle: StyleAndTextTuples
        ft_right: StyleAndTextTuples
        empty: StyleAndTextTuples = []

        line_height = 1
        baseline = 0

        parent_theme = element.theme

        d_blocky = d_inline = d_inline_block = False

        float_lines_left: list[StyleAndTextTuples] = []
        float_width_left = 0
        float_lines_right: list[StyleAndTextTuples] = []
        float_width_right = 0

        new_line: StyleAndTextTuples = []

        def flush() -> None:
            """Add the current line to the rendered output."""
            nonlocal new_line, ft, left, line_height, baseline
            if new_line:
                # Pad the new-line to form an alignable block
                new_line = pad(new_line, style=parent_theme.style)
                if ft:
                    # Combine with the output
                    ft = join_lines([ft, new_line]) if ft else new_line
                else:
                    ft = new_line
            # Reset the new line
            left = 0
            line_height = 1
            baseline = 0
            new_line = []

        available_width = parent_theme.content_width
        available_height = parent_theme.content_height

        coros = {}
        for child in element.renderable_descendents:
            theme = child.theme
            if theme.skip:
                continue
            # Render the element
            coros[child] = self.render_element(
                child,
                available_width=available_width,
                available_height=available_height,
                left=0,
                fill=fill,
                align_content=align_content,
            )
        renderings = await asyncio.gather(*coros.values())

        # Render each child node
        for child, rendering in zip(coros, renderings):
            # Start a new line if we just passed a <br> element
            if child.name == "br":
                flush()
                continue

            # If the rendering was empty, move on
            if not rendering:
                continue

            theme = child.theme

            # We will start a new line if the previous item was a block
            if ft and d_blocky and last_char(ft) != "\n":
                line_height = 1
                left = 0
                baseline = 0

            d_blocky = theme.d_blocky
            d_inline = theme.d_inline
            d_inline_block = theme.d_inline_block
            preformatted = theme.preformatted

            # If the rendering was a positioned absolutely or fixed, store it and draw it later
            if theme.theme["position"] == "fixed":
                self.fixed[(theme.z_index, theme.anchors, theme.position)] = rendering

            # if theme.theme["position"] == "absolute":
            #     self.floats[(theme.z_index, theme.anchors, theme.position)] = rendering

            # if theme.theme["position"] == "relative":
            # ... TODO ..

            elif theme.floated == "right":
                lines = []
                for ft_left, ft_right in zip_longest(
                    split_lines(pad(rendering, style=theme.style)),
                    float_lines_right,
                    fillvalue=empty,
                ):
                    lines.append([*ft_left, *ft_right])
                float_lines_right = lines
                float_width_right = fragment_list_width(float_lines_right[0])
                continue

            elif theme.floated == "left":
                lines = []
                for ft_left, ft_right in zip_longest(
                    lines,
                    split_lines(pad(rendering, style=theme.style)),
                    fillvalue=empty,
                ):
                    lines.append([*ft_left, *ft_right])
                float_lines_left = lines
                float_width_left = fragment_list_width(float_lines_left[0])
                continue

            # If the rendering was inline, add it to the end of the last line of the
            # current output. This might involve re-aligning the last line in the
            # output, which could have been an inline-block

            elif d_inline and (parent_theme.d_inline or preformatted):
                new_line.extend(rendering)

            elif d_inline or d_inline_block:
                if d_inline:
                    tokens = list(fragment_list_to_words(rendering))
                else:
                    tokens = [rendering]

                for token in tokens:
                    token_lines = list(split_lines(token))
                    token_width = max(fragment_list_width(line) for line in token_lines)
                    token_height = len(token_lines)

                    # Deal with floats

                    float_width_right = (
                        fragment_list_width(float_lines_right[0])
                        if float_lines_right
                        else 0
                    )
                    float_width_left = (
                        fragment_list_width(float_lines_left[0])
                        if float_lines_left
                        else 0
                    )

                    # If we have floats, transform the current new line and add one row
                    # from each active float
                    if (
                        new_line
                        and (available_width - float_width_left - float_width_right)
                        - left
                        - token_width
                        < 0
                    ):
                        new_rows = list(split_lines(new_line))
                        new_line_width = max(
                            fragment_list_width(line) for line in new_rows
                        )

                        transformed_rows = []
                        for ft_left, ft_middle, ft_right in zip_longest(
                            float_lines_left[:line_height],
                            (
                                pad(
                                    row,
                                    char=" ",
                                    style=parent_theme.style,
                                    width=new_line_width,
                                )
                                for row in new_rows
                            ),
                            float_lines_right[:line_height],
                            fillvalue=empty,
                        ):
                            line_width = (
                                available_width
                                - fragment_list_width(ft_left)
                                - fragment_list_width(ft_right)
                            )
                            transformed_rows.append(
                                [
                                    *ft_left,
                                    *align(
                                        ft_middle,
                                        how=parent_theme.text_align,
                                        width=line_width,
                                        style=parent_theme.style,
                                        placeholder="",
                                    ),
                                    *ft_right,
                                ]
                            )

                        float_lines_left = float_lines_left[line_height:]
                        float_lines_right = float_lines_right[line_height:]

                        # Manually flush the transformed lines
                        if ft:
                            ft = join_lines([ft, *transformed_rows])
                        else:
                            ft = join_lines(transformed_rows)
                        baseline = 0
                        new_rows = [[]]
                        left = 0
                        line_height = 1
                        new_line = []

                    if line_height == token_height == 1 or not new_line:
                        new_line.extend(token)
                        new_rows = [new_line]
                        baseline = int(theme.vertical_align * (token_height - 1))
                        line_height = max(line_height, token_height)
                    else:
                        new_line, baseline = concat(
                            ft_a=new_line,
                            ft_b=token,
                            baseline_a=baseline,
                            baseline_b=int(theme.vertical_align * (token_height - 1)),
                            style=parent_theme.style,
                        )
                        new_rows = list(split_lines(new_line))
                        line_height = len(new_rows)

                    left += token_width

            # Otherwise we are rendering a block-like element, which gets added to the
            # end of the output
            else:
                # Flush the latest line
                flush()
                # Start block elements on a new line
                if ft and d_blocky and last_char(ft) != "\n":
                    ft.append(("", "\n"))

                ft.extend(rendering)

                # line_height = len(list(split_lines(rendering)))
                # ft.extend(
                # concat(
                # concat(join_lines( float_lines_left[:line_height]), rendering)[0],
                # join_lines(float_lines_right[:line_height]),
                # )[0]
                # )
                # float_lines_left = float_lines_left[line_height:]
                # float_lines_right = float_lines_right[line_height:]

                line_height = 1
                left = 0

        # On "clear", draw the rest of the floats
        if float_lines_left or float_lines_right:
            for ft_left, ft_middle, ft_right in zip_longest(
                float_lines_left,
                split_lines(new_line[:]),
                float_lines_right,
                fillvalue=empty,
            ):
                float_width_right = (
                    fragment_list_width(float_lines_right[0])
                    if float_lines_right
                    else 0
                )
                float_width_left = (
                    fragment_list_width(float_lines_left[0]) if float_lines_left else 0
                )
                line_width = (
                    available_width
                    - fragment_list_width(ft_left)
                    - fragment_list_width(ft_right)
                )
                row = [
                    *ft_left,
                    *align(
                        ft_middle,
                        how=parent_theme.text_align,
                        width=line_width,
                        style=parent_theme.style + " nounderline",
                        placeholder="",
                    ),
                    *ft_right,
                ]
                ft = join_lines([ft, row]) if ft else row
            new_line = []

        # Flush any current lines
        flush()

        # Draw flex elements
        # if parent_theme.get("flex") and parent_theme.get("flex-direction") == "column":
        # table = Table(border=Invisible, collapse_empty_borders=True)
        # row = table.new_row()
        # for output in outputs:
        # row.new_cell(output)
        # ft = table.render(available_width)
        #
        # else:
        # ft = sum(outputs, start=ft)

        return ft

    async def format_element(
        self,
        ft: StyleAndTextTuples,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Format an element's content based on its theme."""
        theme = element.theme
        parent_theme = theme.parent_theme

        d_blocky = theme.d_blocky
        d_inline = theme.d_inline
        d_inline_block = theme.d_inline_block

        preformatted = theme.preformatted
        content_width = theme.content_width
        content_height = theme.content_height
        max_width = theme.max_width

        # If an element should not overflow it's width / height, truncate it
        if not d_inline and (not preformatted or max_width is not None):
            if theme.get("overflow_x") == "hidden":
                ft = truncate(
                    ft,
                    content_width,
                    placeholder="",
                    ignore_whitespace=True,
                )
            elif theme.get("overflow_x") == "auto":
                ft = truncate(
                    ft,
                    content_width,
                    placeholder="▹",
                    ignore_whitespace=True,
                    style=theme.style,
                )

        # Truncate or expand the height
        overflow_y = theme.get("overflow_y") in {"hidden", "auto"}
        pad_height = d_blocky and theme.height is not None
        if overflow_y or pad_height:
            target_height = None
            if (min_height := theme.min_height) and min_height > content_height:
                target_height = min_height
            if (max_height := theme.max_height) and max_height < content_height:
                target_height = max_height
            elif height := theme.height:
                target_height = height

            if target_height is not None:
                # Truncate elements with hidden overflows
                if overflow_y:
                    lines = []
                    for i, line in enumerate(split_lines(ft)):
                        if i <= target_height:
                            lines.append(line)
                else:
                    lines = list(split_lines(ft))

                # Pad height of block elements to theme height
                if pad_height and len(lines) < target_height:
                    lines.extend([[]] * (target_height - len(lines)))

                ft = join_lines(lines)

        # Align content
        if align_content and d_blocky:
            alignment = theme.text_align
            if alignment != FormattedTextAlign.LEFT:
                ft = align(
                    ft,
                    alignment,
                    width=None if d_inline_block else content_width,
                    style=theme.style,
                    ignore_whitespace=True,
                    placeholder="",
                )

        # Fill space around block elements so they fill the content width
        if ft and ((fill and d_blocky and not theme.d_table) or d_inline_block):
            pad_width = None
            if d_blocky:
                pad_width = content_width
            elif d_inline_block:
                pad_width = max_line_width(ft) if theme.width is None else content_width
            if pad_width is not None:
                style = theme.style
                ft = pad(
                    ft,
                    width=round(pad_width),
                    char=" ",
                    style=style,
                )

        # Use the rendered content width from now on for inline elements
        if d_inline_block or d_inline:
            content_width = max_line_width(ft)

        # Add padding & border
        if d_blocky or d_inline_block:
            padding = theme.padding
            border_visibility = theme.border_visibility
            if (any(padding) or any(border_visibility)) and not (
                theme.d_table and theme.border_collapse
            ):
                ft = add_border(
                    ft,
                    style=theme.style,
                    border_grid=theme.border_grid,
                    width=content_width if not ft else None,
                    border_visibility=border_visibility,
                    border_style=theme.border_style,
                    padding=padding,
                )

        # Draw borders and padding on text inside inline elements
        elif element.name == "::text":
            padding = theme.padding
            border_visibility = theme.border_visibility
            if (
                padding.left
                or padding.right
                or border_visibility.left
                or border_visibility.right
            ):
                if not element.is_first_child_node:
                    border_visibility = border_visibility._replace(left=False)
                    padding = padding._replace(left=0)
                if not element.is_last_child_node:
                    border_visibility = border_visibility._replace(right=False)
                    padding = padding._replace(right=0)
                if any(padding) or any(border_visibility):
                    ft = add_border(
                        ft,
                        style=theme.style,
                        border_grid=theme.border_grid,
                        width=content_width if not ft else None,
                        border_visibility=border_visibility,
                        border_style=theme.border_style,
                        padding=padding,
                    )

        # The "::marker" element is drawn in the margin, before any padding
        # If the element has no margin, it can end up in the parent's padding
        # We use [ReverseOverwrite] fragments to ensure the marker is ignored
        # now and written over the margin later.
        if element.marker is not None:
            marker_ft = await self.render_element(
                element.marker,
                available_width=99999,
                available_height=theme.available_height,
                left=0,
                fill=False,
                align_content=False,
            )
            ft = [
                *apply_style(marker_ft, "[ReverseOverwrite]"),
                *ft,
            ]

        parent_style = parent_theme.style if parent_theme else ""

        # Render the margin
        if (alignment := theme.block_align) != FormattedTextAlign.LEFT:
            # Center block contents if margin_left and margin_right are "auto"
            ft = align(
                ft,
                how=alignment,
                width=theme.available_width,
                style=parent_style,
                placeholder="",
            )

        elif any(margin := theme.margin):
            ft = add_border(
                ft=ft,
                style=theme.style,
                border_visibility=DiBool.from_value(False),
                padding=margin,
                padding_style=parent_style,
            )

        # Apply mouse handler to elements with href, title, alt
        if callable(handler := self.mouse_handler):
            attrs = element.attrs
            # Inline elements inherit from parents
            if d_inline and (parent := element.parent):
                p_attrs = parent.attrs
                attrs.setdefault("href", p_attrs.get("href"))
                attrs.setdefault("title", p_attrs.get("title"))
                attrs.setdefault("alt", p_attrs.get("alt"))
            # Resolve link paths
            if href := attrs.get("href"):
                attrs["_link_path"] = self.base.joinuri(href)
            if {"title", "alt", "href"} & set(attrs):
                ft = cast(
                    "StyleAndTextTuples",
                    [
                        (style, text, *(rest or [partial(handler, element)]))
                        for style, text, *rest in ft
                    ],
                )

        return ft

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        """Return formatted text."""
        if not self.formatted_text:
            self.render(width=None, height=None)
        return self.formatted_text


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.current import create_app_session, set_app
    from prompt_toolkit.formatted_text.utils import to_formatted_text
    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles.style import Style

    from euporie.core.app.dummy import DummyApp
    from euporie.core.path import parse_path
    from euporie.core.style import HTML_STYLE

    path = parse_path(sys.argv[1])

    with (
        create_app_session(input=DummyApp.load_input(), output=DummyApp.load_output()),
        set_app(DummyApp()),
    ):
        print_formatted_text(
            to_formatted_text(
                asyncio.run(
                    HTML(
                        path.read_text(), base=path, collapse_root_margin=False
                    )._render(None, None)
                )
            ),
            style=Style(HTML_STYLE),
        )
