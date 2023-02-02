"""Contains a HTML to formatted text parser."""

from __future__ import annotations

import logging
import re
from ast import literal_eval
from bisect import bisect_right
from collections.abc import Mapping
from functools import cached_property, lru_cache
from html.parser import HTMLParser
from itertools import zip_longest
from math import ceil
from typing import TYPE_CHECKING, NamedTuple

from flatlatex.data import subscript, superscript
from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.dimension import Dimension
from upath import UPath

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
from euporie.core.convert.base import convert, get_format
from euporie.core.convert.utils import data_pixel_size, pixels_to_cell_size
from euporie.core.current import get_app
from euporie.core.data_structures import DiBool, DiInt, DiStr
from euporie.core.formatted_text.table import Table, compute_padding
from euporie.core.formatted_text.utils import (
    FormattedTextAlign,
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
    strip_one_trailing_newline,
    truncate,
)
from euporie.core.url import load_url


class CssSelector(NamedTuple):
    """A named tuple to hold CSS selector data."""

    comb: str | None = None
    item: str | None = None
    attr: str | None = None
    pseudo: str | None = None

    def __repr__(self) -> "str":
        """Return a string representation of the selector."""
        defaults = self._field_defaults
        attrs = ", ".join(
            f"{k}={v!r}" for k, v in self._asdict().items() if v != defaults[k]
        )
        return f"{self.__class__.__name__}({attrs})"


if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Generator,
        Hashable,
        Iterator,
        Union,
    )

    CssSelectors = dict[tuple[tuple[CssSelector, ...], ...], dict[str, str]]

log = logging.getLogger(__name__)


class Direction(NamedTuple):
    """A description of a direction."""

    x: "bool" = False
    y: "bool" = False


# Prefer 6-digit hex-colors over 3-digit ones
_COLOR_RE = re.compile(r"#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})")

_SELECTOR_RE = re.compile(
    r"""
        (?:^|\s*(?P<comb>[\s>+~]|(?=::))\s*)
        (?P<item>(?:::)?[^\s>+~:[\]]+)?
        (?P<attr>\[[^\s>+~:]+\])?
        (?P<pseudo>\:[^:][^\s>+~]*)?
    """,
    re.VERBOSE,
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
    "visibility",
    "white_space",
    "list_style_type",
    "list_style_position",
    "_pt_class",
}


@lru_cache(maxsize=500_000)
def match_css_selector(
    selector: "str",
    attrs: "str",
    pseudo: "str",
    element_name: "str",
    is_first_child_element: "bool",
    is_last_child_element: "bool",
    sibling_element_index: "int|None",
    **element_attrs: "Any",
) -> "bool":
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
                    (rule == "odd" and sibling_element_index % 2 == 1)
                    or (rule == "even" and sibling_element_index % 2 == 0)
                )
                continue
        return False

    if not matched:
        return False

    while selector and matched:

        # Universal selector
        if selector == "*":
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
        test = attrs[1 : attrs.index("]")]
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
        selector = selector[2 + len(test) :]

    return matched


def try_eval(value: "str", default: "Any" = None) -> "Any":
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


def get_integer(value: "str") -> "int|None":
    """Extract the first integer from a string."""
    for word in value.split(" "):
        for c in word.partition(".")[0].split():
            if c.isdigit():
                return int(c)
    return None


@lru_cache
def get_color(value: "str") -> "str":
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
                hexes.append(hex(int_value)[2:])
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
    value: "str",
    vertical: "bool" = False,
    available: "float|int|None" = None,
) -> "int|float|None":
    """Convert CSS dimensions to terminal cell sizes."""
    # TODO - create a unit class for easy conversion
    # Get digits
    digits = ""
    i = 0
    try:
        while (c := value[i]) in "0123456789.":
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
        return 0

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

    if units == "%":
        assert available is not None
        return number / 100 * available

    # Get cell pixel dimensions
    app = get_app()
    if hasattr(app, "term_info"):
        cell_px, cell_py = get_app().term_info.cell_size_px
    else:
        cell_px, cell_py = 10, 20

    if units in {"em", "rem", "lh", "ex", "ch", "rlh"}:
        # one unit = one cell width
        if vertical:
            return number * cell_px / cell_py
        else:
            return number

    else:  # units == "px"
        cols = number / cell_px

        if vertical:
            aspect = cell_py / cell_px
            return cols / aspect
        else:
            return cols


def parse_css_content(content: "str") -> "dict[str, str]":
    """Convert CSS declarations into the internals style representation."""
    theme: "dict[str, str]" = {}

    if not content:
        return theme

    for declaration in content.split(";"):
        name, _, value = declaration.partition(":")
        name = name.strip()

        # Ignore "!important" tags for now - TODO
        value = value.replace("!important", "").strip()

        # Helpers

        def _split_quad(value: "str") -> "tuple[str, str, str, str]":
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
            return top, right, bottom, left

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

        else:
            name = name.replace("-", "_")
            theme[name] = value

    return theme


@lru_cache(maxsize=1024)
def selector_specificity(
    selector_parts: "tuple[CssSelector, ...]",
) -> "tuple[int, int, int]":
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
    # Position
    "position": "static",
    "top": "0",
    "right": "0",
    "bottom": "0",
    "left": "0",
    "z_index": "0",
    # Lists
    "list_style_type": "none",
    "list_style_position": "inside",
}


class Theme(Mapping):
    """The computed theme of an element."""

    def __init__(
        self,
        element: "Node",
        parent_theme: "Theme|None",
        available_width: "int" = 0,
        available_height: "int" = 0,
    ) -> "None":
        """Initialize a new element theme."""
        self.element = element
        self.parent_theme = parent_theme
        self.available_width = available_width
        self.available_height = available_height

    @cached_property
    def theme(self) -> "dict[str, str]":
        """Return the combined computed theme."""
        return {
            **_DEFAULT_ELEMENT_CSS,
            **self.inherited_browser_css_theme,
            **self.browser_css_theme,
            **self.inherited_theme,
            **self.dom_css_theme,
            **self.attributes_theme,
            **self.style_attribute_theme,
        }

    def update_space(
        self,
        available_width: "int",
        available_height: "int",
    ) -> "None":
        """Set the space available to the element for rendering."""
        self.available_width = available_width
        self.available_height = available_height

    # Theme calculation mathods

    @cached_property
    def inherited_browser_css_theme(self) -> "dict[str, str]":
        """Get the inherited parts from the browser CSS."""
        if (parent_theme := self.parent_theme) is not None:
            return {
                k: v
                for k, v in {
                    **parent_theme.inherited_browser_css_theme,
                    **parent_theme.browser_css_theme,
                }.items()
                if k in _HERITABLE_PROPS
            }

        else:
            return {}

    @cached_property
    def inherited_theme(self) -> "dict[str, str]":
        """Calculate the theme inherited from the element's parent."""
        if (parent_theme := self.parent_theme) is not None:
            browser_css = self.browser_css_theme
            return {
                k: v
                for part in (
                    parent_theme.inherited_theme,
                    parent_theme.dom_css_theme,
                    parent_theme.attributes_theme,
                    parent_theme.style_attribute_theme,
                )
                for k, v in part.items()
                if k in _HERITABLE_PROPS and browser_css.get(k) != "unset"
            }

        else:
            return {}

    @cached_property
    def style_attribute_theme(self) -> "dict[str, str]":
        """Calculate the theme defined by the element's style attribute."""
        return parse_css_content(self.element.attrs.get("style", ""))

    @cached_property
    def attributes_theme(self) -> "dict[str, str]":
        """Calculate the theme defined by (depreciated) HTML attributes."""
        theme = {}
        # border
        attrs = self.element.attrs
        if border_attr := attrs.get("border"):
            theme["border_top_width"] = border_attr
            theme["border_right_width"] = border_attr
            theme["border_bottom_width"] = border_attr
            theme["border_left_width"] = border_attr
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
            theme["width"] = value
        if (value := attrs.get("height")) is not None:
            theme["height"] = value
        # cellpadding # TODO
        return theme

    def _css_theme(self, css: "CssSelectors") -> "dict[str, str]":
        """Calculate the theme defined in CSS."""
        specificity_rules = []
        element = self.element
        for selectors, rule in css.items():
            for selector_parts in selectors:

                # Last selector item should match the current element
                selector = selector_parts[-1]
                if not match_css_selector(
                    selector.item or "",
                    selector.attr or "",
                    selector.pseudo or "",
                    element.name,
                    element.is_first_child_element,
                    element.is_last_child_element,
                    element.sibling_element_index,
                    **element.attrs,
                ):
                    continue

                # All of the parent selectors should match a separate parent in order
                # TODO - combinators
                # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Selectors#combinators
                unmatched_parents: "list[Node]" = [
                    x for x in element.parents[::-1] if x
                ]

                _unmatched_parents: "list[Node]"
                parent = element.parent
                if parent and (
                    (selector.comb == ">" and parent)
                    # Pseudo-element selectors only match direct ancestors
                    or ((item := selector.item) and item.startswith("::"))
                ):
                    _unmatched_parents = [parent]
                else:
                    _unmatched_parents = unmatched_parents

                # TODO investigate caching element / selector chains so we don't have to
                # iterate through every parent every time

                # Iterate through selector items in reverse, skipping the last
                for selector in selector_parts[-2::-1]:

                    for i, parent in enumerate(_unmatched_parents):
                        if parent and match_css_selector(
                            selector.item or "",
                            selector.attr or "",
                            selector.pseudo or "",
                            parent.name,
                            parent.is_first_child_element,
                            parent.is_last_child_element,
                            parent.sibling_element_index,
                            **parent.attrs,
                        ):
                            if selector.comb == ">" and (parent := parent.parent):
                                _unmatched_parents = [parent]
                            else:
                                _unmatched_parents = unmatched_parents[i + 1 :]
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

        return {
            k: v
            for specificity_rule in sorted(specificity_rules, key=lambda x: x[0])
            for k, v in specificity_rule[1].items()
        }

    @cached_property
    def browser_css_theme(self) -> "dict[str, str]":
        """Calculate the theme defined in the browser CSS."""
        return self._css_theme(css=self.element.dom.browser_css)

    @cached_property
    def dom_css_theme(self) -> "dict[str,str]":
        """Calculate the theme defined in CSS in the DOM."""
        return self._css_theme(css=self.element.dom.css)

    # Computed properties

    @cached_property
    def d_block(self) -> "bool":
        """If the element a block element."""
        return self.theme["display"] == "block" and self.theme["float"] == "none"

    @cached_property
    def d_inline(self) -> "bool":
        """If the element an inline element."""
        return self.theme["display"] == "inline" and self.theme["float"] == "none"

    @cached_property
    def d_inline_block(self) -> "bool":
        """If the element an inline element."""
        return self.theme["display"] == "inline-block" or self.theme["float"] != "none"

    @cached_property
    def d_table(self) -> "bool":
        """If the element a block element."""
        return self.theme["display"] == "table"

    @cached_property
    def d_list_item(self) -> "bool":
        """If the element an inline element."""
        return self.theme["display"] == "list-item" and self.theme["float"] == "none"

    @cached_property
    def d_blocky(self) -> "bool":
        """If the element an inline element."""
        return self.d_block or self.d_table or self.d_list_item

    @property
    def min_width(self) -> "int|None":
        """The minimum permitted width."""
        if value := self.get("min_width"):
            theme_width = css_dimension(
                value, vertical=False, available=self.available_width
            )
            if theme_width is not None:
                return int(theme_width)
        return None

    @property
    def width(self) -> "int|None":
        """The pescribed width."""
        if value := self.theme.get("width"):
            theme_width = css_dimension(
                value, vertical=False, available=self.available_width
            )
            if theme_width is not None:
                return int(theme_width)

        else:
            element = self.element
            attrs = element.attrs
            if element.name == "input" and attrs.get("type") in {
                "text",
                "password",
                "email",
                "number",
                "search",
                "tel",
                "url",
            }:
                return try_eval(size) if (size := attrs.get("size")) else 20

        return None

    @property
    def max_width(self) -> "int|None":
        """The maximum permitted width."""
        if value := self.get("max_width"):
            theme_width = css_dimension(
                value, vertical=False, available=self.available_width
            )
            if theme_width is not None:
                return int(theme_width)
        return None

    @property
    def height(self) -> "int":
        """The perscribed height."""
        # TODO - process min-/max-height
        if value := self.get("height"):
            theme_height = css_dimension(
                value, vertical=True, available=self.available_height
            )
            if theme_height is not None:
                return int(theme_height)
        assert self.available_height is not None
        return self.available_height

    @property
    def content_width(self) -> "int":
        """Return the width available for rendering the element's content."""
        value = self.width
        # Set content width to the available width for blocks
        if value is None:
            value = (self.available_width or 0) - self.margin.left - self.margin.right
        # Apply min / max width constraints
        if (max_width := self.max_width) is not None and max_width < value:
            value = max_width
        elif (min_width := self.min_width) is not None and min_width > value:
            value = min_width
        # Remove padding and borders from content width for blocks
        if value and (self.d_blocky or self.d_inline_block):
            value -= self.padding.left + self.padding.right
            value -= self.border_visibility.left + self.border_visibility.right

        return max(0, value)

    @property
    def content_height(self) -> "int":
        """Return the height available for rendering the element's content."""
        value = self.height
        if value and self.d_blocky:
            value -= self.padding.top + self.padding.bottom
            value -= self.border_visibility.top + self.border_visibility.bottom
            value -= self.margin.top + self.margin.bottom
        return max(value, 0)

    @cached_property
    def padding(self) -> "DiInt":
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
            output[direction] = int((value or 0) + 0.49999)

        # Do not render top and bottom padding for inline elements
        if self.d_inline or self.d_inline_block:
            output["top"] = 0
            output["bottom"] = 0

        return DiInt(**output)

    @cached_property
    def base_margin(self) -> "DiInt":
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
            output[direction] = int((value or 0) + 0.6)
        return DiInt(**output)

    @cached_property
    def margin(self) -> "DiInt":
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

        return DiInt(**values)

    @cached_property
    def margin_auto(self) -> "bool":
        """Determine if the left and right margins are set to auto."""
        return self.theme["margin_left"] == self.theme["margin_right"] == "auto"

    @cached_property
    def border_style(self) -> "DiStr":
        """Calculate the visibility of the element's borders."""
        if parent_theme := self.parent_theme:
            parent_style = parent_theme.style
        else:
            parent_style = ""

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

            if getattr(self.border_line, direction) in {
                UpperRightEighthLine,
                LowerLeftEighthLine,
            }:
                style += f" bg:{self.background_color}"

            output[direction] = style

        return DiStr(**output)

    @cached_property
    def border_visibility(self) -> "DiBool":
        """Calculate the visibility of the element's borders."""
        theme = self.theme
        output = {
            direction: css_dimension(theme[f"border_{direction}_width"]) != 0
            and theme[f"border_{direction}_style"] != "none"
            for direction in ("top", "left", "bottom", "right")
        }

        # Do not render top and bottom borders for inline elements
        # if there is no top or bottom padding
        if self.theme["display"] == "inline":
            padding = self.padding
            if not padding.top:
                output["top"] = False
            if not padding.bottom:
                output["bottom"] = False

        return DiBool(**output)

    @cached_property
    def border_line(self) -> "DiLineStyle":
        """Calculate the line style."""
        a_w = self.available_width
        self.d_inline
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

        return DiLineStyle(**output)

    @cached_property
    def border_grid(self) -> "GridStyle":
        """Calculate a GridStyle based on the border lines."""
        border_line = self.border_line
        return (
            border_line.top.top_edge
            + border_line.right.right_edge
            + border_line.bottom.bottom_edge
            + border_line.left.left_edge
        )

    @cached_property
    def border_collapse(self) -> "bool":
        """Determine if the border is collapsed."""
        return self.theme.get("border_collapse") == "collapse"

    @cached_property
    def color(self) -> "str":
        """Get the computed theme foreground color."""
        # TODO - transparency
        color_str = self.theme["color"]
        if color_str == "transparent":
            return self.background_color
        if fg := get_color(color_str):
            return fg
        elif self.parent_theme:
            return self.parent_theme.color
        else:
            return ""

    @cached_property
    def background_color(self) -> "str":
        """Get the computed theme background color."""
        # TODO - transparency
        color_str = self.theme["background_color"]
        if color_str == "transparent":
            if parent_theme := self.parent_theme:
                return parent_theme.background_color
        if bg := get_color(color_str):
            return bg
        elif self.parent_theme:
            return self.parent_theme.background_color
        else:
            return ""

    @cached_property
    def style(self) -> "str":
        """Calculate the output style."""
        theme = self.theme
        style = ""

        if "_pt_class" in self.theme:
            style += f"class:{theme['_pt_class']}"

        if fg := self.color:
            style += f" fg:{fg}"

        if bg := self.background_color:
            style += f" bg:{bg}"

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

        return style

    @cached_property
    def text_transform(self) -> "Callable[[str], str]|None":
        """Return a function which transforms text."""
        if "uppercase" in self.theme["text_transform"]:
            return str.upper
        elif "lowercase" in self.theme["text_transform"]:
            return str.lower
        elif "capitalize" in self.theme["text_transform"]:
            return str.capitalize
        elif "sub" in self.theme["vertical_align"]:
            return lambda x: "".join(subscript.get(c, c) for c in x)
        elif "super" in self.theme["vertical_align"]:
            return lambda x: "".join(superscript.get(c, c) for c in x)
        elif "math" in self.theme["text_transform"]:
            return lambda x: convert(x, "latex", "ansi")
        else:
            return None

    @cached_property
    def preformatted(self) -> "bool":
        """Determine if the content is pre-formatted."""
        return self.theme["white_space"] in {"pre", "pre-wrap", "pre-line"}

    @cached_property
    def text_align(self) -> "FormattedTextAlign":
        """The text alignment direction."""
        return _TEXT_ALIGNS.get(self.theme["text_align"], FormattedTextAlign.LEFT)

    @cached_property
    def vertical_align(self) -> "float":
        """The vertical alignment direction."""
        return _VERTICAL_ALIGNS.get(self.theme["vertical_align"], 1)

    @cached_property
    def list_style_type(self) -> "str":
        """The bullet character to use for the list."""
        return _LIST_STYLE_TYPES.get(
            self.theme["list_style_type"], self.theme["list_style_type"]
        )

    @cached_property
    def list_style_position(self) -> "str":
        """Where the list bullet should be located."""
        if "outside" in self.theme["list_style_position"]:
            return "outside"
        else:
            return "inside"

    @cached_property
    def font_size(self) -> "float|int":
        """Get the computed font size for the current element."""
        available = self.parent_theme.font_size if self.parent_theme else 1
        if (
            result := css_dimension(self.theme["font_size"], available=available)
        ) is not None:
            return result
        else:
            return 1

    @cached_property
    def z_index(self) -> "int":
        """The z-index of the element."""
        return get_integer(self.theme["z_index"]) or 0

    @cached_property
    def position(self) -> "DiInt":
        """The position of an element with a relative, absolute or fixed position."""
        # TODO - calculate position based on top, left, bottom,right, width, height
        return DiInt(
            top=int(
                css_dimension(
                    self.theme["top"],
                    vertical=True,
                    available=self.element.dom.soup.theme.available_height,
                )
                or 0
            ),
            right=int(
                css_dimension(
                    self.theme["right"],
                    vertical=False,
                    available=self.element.dom.soup.theme.available_width,
                )
                or 0
            ),
            bottom=int(
                css_dimension(
                    self.theme["bottom"],
                    vertical=True,
                    available=self.element.dom.soup.theme.available_height,
                )
                or 0
            ),
            left=int(
                css_dimension(
                    self.theme["left"],
                    vertical=False,
                    available=self.element.dom.soup.theme.available_width,
                )
                or 0
            ),
        )

    @cached_property
    def skip(self) -> "bool":
        """Determine if the element should not be displayed."""
        return (
            "none" in self.theme["display"]
            or (
                (element := self.element).name == "text"
                and not self.preformatted
                and not element.text
            )
            or (
                self.theme["position"] == "absolute"
                and try_eval(self.theme["opacity"]) == 0
            )
        )

    @cached_property
    def hidden(self) -> "bool":
        """Determine if the element is hidden."""
        return (
            try_eval(self.theme["opacity"]) == 0 or self.theme["visibility"] == "hidden"
        )

    @cached_property
    def in_flow(self) -> "bool":
        """Determines if the element is "in-flow"."""
        return (
            not self.skip
            and self.theme["float"] == "none"
            and self.theme["position"] not in {"absolute", "fixed"}
            and self.element.name != "html"
        )

    # Mapping methods - these are passed on to the unerlying theme dictionary

    def __getitem__(self, key: "str") -> "Any":
        """Get an item."""
        return self.theme.__getitem__(key)

    def __iter__(self) -> "Iterator":
        """Iterate over items."""
        return self.theme.__iter__()

    def __len__(self) -> "int":
        """Get the length of the mapping."""
        return self.theme.__len__()


_BROWSER_CSS = {
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
        (CssSelector(item="text"),),
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
        "color": "ansibrightblue",
    },
    ((CssSelector(item="b"),), (CssSelector(item="strong"),)): {
        "display": "inline",
        "font_weight": "bold",
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
    ): {"content": "“"},
    (
        (
            CssSelector(item="q"),
            CssSelector(item="::after"),
        ),
    ): {"content": "”"},
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
        "background_color": "#FFFFFF",
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
    },
    ((CssSelector(item="p"),),): {"margin_top": "1em", "margin_bottom": "1em"},
    ((CssSelector(item="pre"),),): {
        "margin_top": "1em",
        "margin_bottom": "1em",
        "white_space": "pre",
    },
    # Lists
    ((CssSelector(item="::marker"),),): {
        "display": "inline",
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
        (CssSelector(item="dir"), CssSelector(item="dir"), CssSelector(item="menu")),
        (CssSelector(item="dir"), CssSelector(item="dir"), CssSelector(item="ul")),
        (CssSelector(item="dir"), CssSelector(item="menu"), CssSelector(item="dir")),
        (CssSelector(item="dir"), CssSelector(item="menu"), CssSelector(item="menu")),
        (CssSelector(item="dir"), CssSelector(item="menu"), CssSelector(item="ul")),
        (CssSelector(item="dir"), CssSelector(item="ol"), CssSelector(item="dir")),
        (CssSelector(item="dir"), CssSelector(item="ol"), CssSelector(item="menu")),
        (CssSelector(item="dir"), CssSelector(item="ol"), CssSelector(item="ul")),
        (CssSelector(item="dir"), CssSelector(item="ul"), CssSelector(item="dir")),
        (CssSelector(item="dir"), CssSelector(item="ul"), CssSelector(item="menu")),
        (CssSelector(item="dir"), CssSelector(item="ul"), CssSelector(item="ul")),
        (CssSelector(item="menu"), CssSelector(item="dir"), CssSelector(item="dir")),
        (CssSelector(item="menu"), CssSelector(item="dir"), CssSelector(item="menu")),
        (CssSelector(item="menu"), CssSelector(item="dir"), CssSelector(item="ul")),
        (CssSelector(item="menu"), CssSelector(item="menu"), CssSelector(item="dir")),
        (CssSelector(item="menu"), CssSelector(item="menu"), CssSelector(item="menu")),
        (CssSelector(item="menu"), CssSelector(item="menu"), CssSelector(item="ul")),
        (CssSelector(item="menu"), CssSelector(item="ol"), CssSelector(item="dir")),
        (CssSelector(item="menu"), CssSelector(item="ol"), CssSelector(item="menu")),
        (CssSelector(item="menu"), CssSelector(item="ol"), CssSelector(item="ul")),
        (CssSelector(item="menu"), CssSelector(item="ul"), CssSelector(item="dir")),
        (CssSelector(item="menu"), CssSelector(item="ul"), CssSelector(item="menu")),
        (CssSelector(item="menu"), CssSelector(item="ul"), CssSelector(item="ul")),
        (CssSelector(item="ol"), CssSelector(item="dir"), CssSelector(item="dir")),
        (CssSelector(item="ol"), CssSelector(item="dir"), CssSelector(item="menu")),
        (CssSelector(item="ol"), CssSelector(item="dir"), CssSelector(item="ul")),
        (CssSelector(item="ol"), CssSelector(item="menu"), CssSelector(item="dir")),
        (CssSelector(item="ol"), CssSelector(item="menu"), CssSelector(item="menu")),
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
        (CssSelector(item="ul"), CssSelector(item="menu"), CssSelector(item="menu")),
        (CssSelector(item="ul"), CssSelector(item="menu"), CssSelector(item="ul")),
        (CssSelector(item="ul"), CssSelector(item="ol"), CssSelector(item="dir")),
        (CssSelector(item="ul"), CssSelector(item="ol"), CssSelector(item="menu")),
        (CssSelector(item="ul"), CssSelector(item="ol"), CssSelector(item="ul")),
        (CssSelector(item="ul"), CssSelector(item="ul"), CssSelector(item="dir")),
        (CssSelector(item="ul"), CssSelector(item="ul"), CssSelector(item="menu")),
        (CssSelector(item="ul"), CssSelector(item="ul"), CssSelector(item="ul")),
    ): {"list_style_type": "square"},
    ((CssSelector(item="li"),),): {"display": "list-item"},
    ((CssSelector(item="details"),),): {
        "list_style_type": "disclosure-closed",
        "list_style_position": "inside",
    },
    ((CssSelector(item="details", attr="[open]"), CssSelector(item="summary")),): {
        "list_style_type": "disclosure-open"
    },
    ((CssSelector(item="summary"),),): {"display": "list-item", "font_weight": "bold"},
    # Dataframes for Jupyter
    ((CssSelector(item=".dataframe"),),): {"_pt_class": "dataframe"},
    (
        (CssSelector(item=".dataframe"), CssSelector(item="td")),
        (CssSelector(item=".dataframe"), CssSelector(item="th")),
    ): {
        "border_top_style": "hidden",
        "border_left_style": "hidden",
        "border_bottom_style": "hidden",
        "border_right_style": "hidden",
        "padding_left": "1em",
    },
    ((CssSelector(item=".dataframe"), CssSelector(item="th"),),): {
        "_pt_class": "dataframe,th",
    },
    (
        (CssSelector(item=".dataframe"), CssSelector(item="th", pseudo=":first-child")),
        (CssSelector(item=".dataframe"), CssSelector(item="th", pseudo=":last-child")),
        (CssSelector(item=".dataframe"), CssSelector(item="td", pseudo=":last-child")),
    ): {"padding_right": "1em"},
    ((CssSelector(item=".dataframe"), CssSelector(item="td")),): {
        "_pt_class": "dataframe,td bg:default"
    },
    (
        (
            CssSelector(item=".dataframe"),
            CssSelector(item="tr", pseudo=":nth-child(odd)"),
            CssSelector(item="td"),
        ),
    ): {"_pt_class": "dataframe,row-odd,td"},
}


class Node:
    """Represents an node in the DOM."""

    theme: "Theme"

    def __init__(
        self,
        dom: "HTML",
        name: "str",
        parent: "Node|None",
        text: "str" = "",
        attrs: "list[tuple[str, str|None]]|None" = None,
        contents: "list[Node]|None" = None,
    ) -> "None":
        """Create a new page element."""
        self.dom = dom
        self.name = name
        self.parent = parent
        self._text = text
        self.attrs: "dict[str, Any]" = {k: v for k, v in (attrs or []) if v is not None}
        self.contents: "list[Node]" = contents or []
        self.closed = False
        self.marker: "Node|None" = None
        self.before: "Node|None" = None
        self.after: "Node|None" = None

        parent_theme = parent.theme if parent else None
        self.theme = Theme(self, parent_theme=parent_theme)

    def _outer_html(self, d: "int" = 0, attrs: "bool" = True) -> "str":
        dd = " " * d
        s = ""
        if self.name != "text":
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
                        s += f"\n{dd} {child._outer_html(d+1, attrs=attrs)}"
                    s += f"\n{dd}{dd}"
                s += f"</{self.name}>"
        else:
            s += f"{dd}{self.text}"
        return s

    @cached_property
    def text(self) -> "str":
        """Get the element's computed text."""
        if text := self._text:

            if callable(transform := self.theme.text_transform):
                text = transform(text)

            if not self.theme.preformatted:
                # Strip whitespace
                strippable = True
                for i in text:
                    if i not in "\x20\x0a\x09\x0c\x0d":
                        strippable = False
                        break
                if strippable:
                    if "\n" in text:
                        text = "\n"
                    else:
                        text = " "

                # Collapse whitespace
                text = re.sub(r"\s+", " ", text.strip("\n").replace("\n", " "))

        return text

    def find_all(self, tag: "str", recursive: "bool" = False) -> "list[Node]":
        """Find all child elements of a given tag type."""
        return [element for element in self.contents if element.name == tag]

    @property
    def descendents(self) -> "Generator[Node, None, None]":
        """Yields all descendent elements."""
        for child in self.contents:
            yield child
            yield from child.descendents

    @cached_property
    def parents(self) -> "list[Node]":
        """Yields all descendent elements."""
        parents = []
        parent = self.parent
        while parent is not None:
            parents.append(parent)
            parent = parent.parent
        return parents[::-1]

    @cached_property
    def is_first_child_node(self) -> "bool":
        """True if the element if the first child node of its parent element."""
        if (parent := self.parent) and (child_nodes := parent.contents):
            return child_nodes[0] == self
        return False

    @cached_property
    def is_last_child_node(self) -> "bool":
        """True if the element if the last child node of its parent element."""
        if (parent := self.parent) and (child_nodes := parent.contents):
            return child_nodes[-1] == self
        return False

    @property
    def child_elements(self) -> "Generator[Node, None, None]":
        """Yields all of the child element nodes."""
        for child in self.contents:
            # Ignore text and comment nodes
            if (
                child.name != "text"
                and child.name != "comment"
                and not child.name.startswith("::")
            ):
                yield child

    @cached_property
    def first_child_element(self) -> "Node|None":
        """Returns the first child element."""
        try:
            return next(self.child_elements)
        except StopIteration:
            return None

    @cached_property
    def last_child_element(self) -> "Node|None":
        """Returns the last child element."""
        if child_elements := list(self.child_elements):
            return child_elements[-1]
        return None

    @cached_property
    def is_first_child_element(self) -> "bool":
        """True if the element if the first child element of its parent element."""
        if parent := self.parent:
            try:
                return next(parent.child_elements) == self
            except StopIteration:
                pass
        return False

    @cached_property
    def is_last_child_element(self) -> "bool":
        """True if the element if the last child element of its parent element."""
        if parent := self.parent:
            for child in reversed(parent.contents):
                # Ignore text and comment nodes
                if (
                    child.name != "text"
                    and child.name != "comment"
                    and not child.name.startswith("::")
                ):
                    return child == self
        return False

    @cached_property
    def sibling_element_index(self) -> "int|None":
        """Return the index of this element among its siblings."""
        if self.parent:
            for i, child in enumerate(self.parent.child_elements):
                if child == self:
                    return i
        return None

    @cached_property
    def prev_node(self) -> "Node|None":
        """Return the previous sibling node."""
        if parent := self.parent:
            prev_node = None
            for child in parent.contents:
                if child == self:
                    return prev_node
                prev_node = child
        return None

    @cached_property
    def next_node(self) -> "Node|None":
        """Return the next sibling node."""
        if parent := self.parent:
            prev_child = None
            for child in parent.contents:
                if prev_child == self:
                    return child
                prev_child = child
        return None

    @cached_property
    def prev_node_in_flow(self) -> "Node|None":
        """Get the previous node in the current element's flow."""
        prev_node = self.prev_node
        while prev_node and not prev_node.theme.in_flow:
            prev_node = prev_node.prev_node
        return prev_node

    @cached_property
    def next_node_in_flow(self) -> "Node|None":
        """Get the next node in the current element's flow."""
        next_node = self.next_node
        while next_node and not next_node.theme.in_flow:
            next_node = next_node.next_node
        return next_node

    @cached_property
    def prev_element(self) -> "Node|None":
        """Return the previous sibling element."""
        if parent := self.parent:
            prev_element = None
            for child in parent.child_elements:
                if child == self:
                    return prev_element
                prev_element = child
        return None

    @cached_property
    def next_element(self) -> "Node|None":
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

    def __repr__(self, d: "int" = 0) -> "str":
        """Return a string representation of the element."""
        parts = [self.name, *[f'{k}="{v}"' for k, v in self.attrs.items()]]
        return f"<{' '.join(parts)}>"


class CustomHTMLParser(HTMLParser):
    """An HTML parser."""

    def __init__(self, dom: "HTML") -> "None":
        """Create a new parser instance."""
        super().__init__()
        self.dom = dom
        self.curr = self.soup = Node(name="::root", dom=dom, parent=None, attrs=[])

    def parse(self, markup: "str") -> "Node":
        """Parse HTML markup."""
        self.curr = self.soup = Node(dom=self.dom, name="::root", parent=None, attrs=[])
        self.feed(markup)
        return self.soup

    def handle_starttag(
        self, tag: "str", attrs: "list[tuple[str, str|None]]"
    ) -> "None":
        """Open a new element."""
        self.autoclose()
        element = Node(dom=self.dom, name=tag, parent=self.curr, attrs=attrs)
        self.curr.contents.append(element)
        self.curr = element

    def autoclose(self) -> "None":
        """Automatically close void elements."""
        if not self.curr.closed and self.curr.name in _VOID_ELEMENTS:
            self.curr.closed = True
            if self.curr.parent:
                self.curr = self.curr.parent

    def handle_data(self, data: "str") -> "None":
        """Create data (text) elements."""
        self.autoclose()
        self.curr.contents.append(
            Node(
                dom=self.dom,
                name="text",
                parent=self.curr,
                text=data,
                attrs=[],
            )
        )

    def handle_endtag(self, tag: "str") -> "None":
        """Handle end tags: close the currently opened element."""
        if tag != self.curr.name:
            self.autoclose()
        self.curr.closed = True
        if self.curr.parent:
            self.curr = self.curr.parent


def parse_styles(soup: "Node", base_url: "UPath") -> "CssSelectors":
    """Collect all CSS styles from style tags."""
    rules: "CssSelectors" = {}
    for child in soup.descendents:
        css_str = ""

        # In case of a <link> style, load the url
        if (
            child.name == "link"
            and child.attrs.get("rel") == "stylesheet"
            and (href := child.attrs.get("href"))
        ):
            if css_bytes := load_url(href, base_url):
                css_str = css_bytes.decode()

        # In case of a <style> tab, load first child's text
        elif child.name == "style":
            if child.contents:
                css_str = child.contents[0].text
        else:
            continue
        # Remove whitespace and newlines
        # css_str = css_str.strip().replace("\n", "")
        css_str = re.sub(r"\s*\n\s*", " ", css_str)
        # Remove comments
        css_str = re.sub(r"\/\*[^\*]+\*\/", "", css_str)
        # Replace ':before' and ':after' with '::before' and '::after'
        css_str = re.sub("(?<!:):(?=before|after)", "::", css_str)
        # Allow plain '@media screen' queries
        css_str = re.sub(
            r"""
            @media\s+screen\s*{\s*
              (.+? {
                (?:[^:}]+\s*:\s*[^;}]+\s*;\s*)*
                (?:[^:}]+\s*:\s*[^;}]+\s*;?\s*)?
              })
              \s*
            }
            """,
            "\\1",
            css_str,
            0,
            flags=re.DOTALL | re.VERBOSE,
        )
        # Remove other media queries for now - TODO
        # TODO - Far too slow sometimes!
        css_str = re.sub(
            r"""
            @media.+?{\s*
              (.+? {
                (?:[^:}]+\s*:\s*[^;}]+\s*;\s*)*
                (?:[^:}]+\s*:\s*[^;}]+\s*;?\s*)?
              })
              \s*
            }
            """,
            "",
            css_str,
            0,
            flags=re.DOTALL | re.VERBOSE,
        )
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
                        if parsed_selectors in rules:
                            rules[parsed_selectors].update(rule_content)
                        else:
                            rules[parsed_selectors] = rule_content

    return rules


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    formatted_text: "StyleAndTextTuples"

    def render_ol_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render lists, adding item numbers to child <li> elements."""
        # Assign a list index to each item. This can be set via the 'value' attributed
        _curr = 0
        for item in element.find_all("li"):
            _curr += 1
            _curr = int(item.attrs.setdefault("value", str(_curr)))
        # Render list as normal
        return self.render_node_content(
            element=element,
            left=left,
            fill=fill,
            align_content=align_content,
        )

    render_ul_content = render_ol_content

    def __init__(
        self,
        markup: "str",
        base: "Union[UPath, str]|None" = None,
        width: "int|None" = None,
        height: "int|None" = None,
        collapse_root_margin: "bool" = False,
        fill: "bool" = True,
        browser_css: "CssSelectors|None" = None,
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
            browser_css: The browser CSS to use

        """
        self.browser_css: "CssSelectors" = {
            **(_BROWSER_CSS if browser_css is None else browser_css)
        }
        self.css: "CssSelectors" = {}

        self.markup = markup
        self.base = base
        self.width: "int|None" = None
        self.height: "int|None" = None
        self.collapse_root_margin = collapse_root_margin
        self.fill = fill

        self.parser = CustomHTMLParser(self)

        self.element_theme_cache: "SimpleCache[Hashable, dict[str, Any]]" = (
            SimpleCache()
        )

        # Parse the markup
        self.soup = self.parser.parse(markup.strip())

        # Parse the styles
        self.css.update(parse_styles(self.soup, self.base))

        # Load images
        for child in self.soup.descendents:
            if child.name == "img" and (src := child.attrs.get("src")):
                if data := load_url(src, self.base):
                    child.attrs["_data"] = data
                else:
                    child.attrs["_missing"] = "true"

        self.floats: dict[tuple[int, DiInt], StyleAndTextTuples] = {}
        self.fixes: dict[tuple[int, DiInt], StyleAndTextTuples] = {}

        # Render the markup
        self.render(width, height)

    def render_list_item_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
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
            bullet_element = Node(
                dom=self,
                name="::marker",
                parent=element,
                contents=[Node(dom=self, name="text", parent=element, text=bullet)],
            )
            if theme.list_style_position == "inside":
                element.contents.insert(0, bullet_element)
            else:
                element.marker = bullet_element
        # Render the list item
        ft = self.render_node_content(
            element,
            left=left,
            fill=fill,
            align_content=align_content,
        )
        return ft

    def render(self, width: "int|None", height: "int|None") -> "None":
        """Render the current markup at a given size."""
        if not width or not height:
            size = get_app_session().output.get_size()
        self.width = width or size.columns
        self.height = height or size.rows

        ft = self.render_element(
            self.soup,
            available_width=self.width,
            available_height=self.height,
            fill=self.fill,
        )

        # Draw floats
        for (_, position), float_ft in sorted(self.floats.items()):
            row = col = 0
            if (top := position.top) is not None:
                row = top
            elif (bottom := position.bottom) is not None:
                row = (
                    sum(1 for _ in split_lines(ft))
                    - sum(1 for _ in split_lines(float_ft))
                    - bottom
                )
            if (left := position.left) is not None:
                col = left
            elif (right := position.right) is not None:
                row = max_line_width(ft) - max_line_width(float_ft) - right

            ft = paste(ft, float_ft, row, col)

        # Apply "ReverseOverwrite"s
        ft = apply_reverse_overwrites(ft)

        self.formatted_text = ft

    def render_element(
        self,
        element: "Node",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render a Node."""
        # Update the element theme with the available space
        element.theme.update_space(available_width, available_height)

        # Render the contents
        if element.theme.d_table:
            render_func = self.render_table_content

        elif element.theme.d_list_item:
            render_func = self.render_list_item_content

        else:
            render_func = getattr(
                self, f"render_{element.name}_content", self.render_node_content
            )

        # Render the element
        ft = render_func(element, left, fill, align_content)

        # Format the contents
        ft = self.format_element(ft, element, left, fill, align_content)

        return ft

    def render_text_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render a text element.

        Args:
            element: The page element to render
            parent_theme: The theme of the element's parent element
            available_width: The width available for rendering the element
            available_height: The height available for rendering the element
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        ft: "StyleAndTextTuples" = []
        if text := element.text:
            if parent_theme := element.theme.parent_theme:
                style = parent_theme.style
            else:
                style = ""
            ft = [(style, text)]
        return ft

    def render_table_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a table element.

        Args:
            element: The list of parsed elements to render
            available_width: The width available for rendering the element
            available_height: The height available for rendering the element
            parent_theme: The theme of the parent element
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        ft = []

        table_theme = element.theme
        table_x_dim = Dimension(
            min=table_theme.min_width,
            preferred=table_theme.content_width if "width" in table_theme else None,
            max=table_theme.max_width or table_theme.available_width,
        )
        table = Table(
            align=table_theme.text_align,
            style=table_theme.style,
            border_line=table_theme.border_line,
            border_style=table_theme.border_style,
            padding=DiInt(0, 0, 0, 0),
            width=table_x_dim,
            expand=True if "width" in table_theme else False,
            collapse_empty_borders=True,
        )

        td_map = {}

        # Stack the elements in the shape of the table
        def render_rows(elements: "list[Node]") -> "None":
            for tr in elements:
                if tr.name == "tr":
                    tr_theme = tr.theme
                    # tr_theme.update_space(available_width, available_height)
                    row = table.new_row(
                        align=tr_theme.text_align,
                        border_line=tr_theme.border_line,
                        border_style=tr_theme.border_style,
                        style=tr_theme.style,
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
                                # text=" ",
                                text=self.render_node_content(
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
                            )
                            # Save for later so we can add the contents once all the
                            # cells are created and we can calculate the cell widths
                            td_map[cell] = td

        # Render the table head
        for child in element.find_all("thead", recursive=False):
            render_rows(child.contents)
        # Render the table body
        for child in element.find_all("tbody", recursive=False):
            render_rows(child.contents)
        # Render rows not in a head / body / foot as part of the body
        render_rows(element.contents)
        for child in element.find_all("tfoot", recursive=False):
            render_rows(child.contents)

        # Add cell contents
        if td_map:
            col_widths = table.calculate_col_widths()

            for row in table.rows:
                for col_width, cell in zip(col_widths, row.cells):
                    if td := td_map.get(cell):
                        cell_padding = compute_padding(cell)
                        available_width = (
                            (table_x_dim.max if cell.colspan > 1 else col_width)
                            - cell_padding.left
                            - cell_padding.right
                        )
                        td.theme.update_space(
                            available_width, table_theme.available_height
                        )
                        cell.text = self.render_node_content(
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
                ft_caption = self.render_element(
                    child,
                    available_width=table_width,
                    available_height=table_theme.available_height,
                    left=0,
                    fill=True,
                )
                if ft_caption:
                    ft.extend(ft_caption)

        ft.extend(ft_table)

        return ft

    def render_img_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> StyleAndTextTuples:
        """Render an image's content."""
        theme = element.theme
        content_width = theme.content_width
        # content_height = theme.content_height
        src = str(element.attrs.get("src", ""))
        path = UPath(src)

        if data := element.attrs.get("_data"):
            # Display it graphically
            format_ = get_format(path, default="png")
            cols, aspect = pixels_to_cell_size(*data_pixel_size(data, format_=format_))
            # Manually set a value if we don't have one
            cols = cols or 20
            aspect = aspect or 0.5
            # Scale down the image to fit to width
            if content_width := theme.content_width:
                cols = min(content_width, cols)
            rows = ceil(cols * aspect)
            # Convert the image to formatted-text
            ft = (
                convert(
                    data,
                    from_=format_,
                    to="formatted_text",
                    cols=cols,
                    rows=rows,
                    bg=theme.background_color,
                    path=path,
                )
                or []
            )
            # Remove trailing new-lines
            ft = strip(ft, chars="\n", left=False)
            # Set default background color on generated content
            ft = [(f"{theme.style} {x[0]}", *x[1:]) for x in ft]

        else:
            ft = []

            if (alt := element.attrs.get("alt")) != "":
                style = f"class:image,placeholder {theme.style}"
                ft.append((style, "🌄"))
                if content_width and content_width >= 7:
                    ft.extend(
                        [
                            (style, " "),
                            (style, (alt or (path.name if path else "Image"))),
                        ]
                    )

        return ft

    def render_svg_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Display images rendered as ANSI art."""
        theme = element.theme
        # HTMLParser clobber the case of element attributes
        # We fix the SVG viewBox here
        data = element._outer_html().replace(" viewbox=", " viewBox=")
        # Render the image
        ft = convert(
            data=data,
            from_="svg",
            to="formatted_text",
            cols=theme.content_width,
            bg=theme.background_color,
        )
        # Remove trailing new-lines
        ft = strip(ft, chars="\n", left=False)
        # Set default background color on generated content
        ft = [(f"{theme.style} {x[0]}", *x[1:]) for x in ft]
        return ft

    def render_input_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render an input element."""
        attrs = element.attrs
        element.contents.insert(
            0,
            Node(
                dom=self,
                name="text",
                parent=element,
                text=attrs.get("value", attrs.get("placeholder", "")),
            ),
        )
        ft = self.render_node_content(
            element,
            left=left,
            fill=fill,
            align_content=align_content,
        )
        return ft

    def render_br_content(
        self,
        element: "Node",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> StyleAndTextTuples:
        """Render line breaks."""
        return [("", "\n")]

    def render_node_content(
        self,
        element: Node,
        left: int = 0,
        fill: bool = True,
        align_content: bool = True,
    ) -> StyleAndTextTuples:
        """Generate flows for the contents of the element."""
        ft: "StyleAndTextTuples" = []

        ft_left: StyleAndTextTuples
        ft_middle: StyleAndTextTuples
        ft_right: StyleAndTextTuples
        empty: StyleAndTextTuples = []

        line_height = 1
        baseline = 0

        # Add "::before"  and "::after" nodes
        # TODO - do we have to do this for every element?
        for name, pos in (("::before", 0), ("::after", 1)):
            if not element.name.startswith("::"):
                content_node = Node(dom=element.dom, name=name, parent=element)
                if text := content_node.theme.get("content", "").strip('"'):
                    content_node.contents.append(
                        Node(
                            dom=element.dom, name="text", parent=content_node, text=text
                        )
                    )
                    element.contents.insert(pos * len(element.contents), content_node)

        parent_theme = element.theme

        d_blocky = d_inline = d_inline_block = False

        float_lines_left: list[StyleAndTextTuples] = []
        float_width_left = 0
        float_lines_right: list[StyleAndTextTuples] = []
        float_width_right = 0

        content_width = parent_theme.content_width

        new_line = []

        # Render each child node
        for child in element.contents:

            theme = child.theme

            if theme.skip:
                continue

            # We will start a new line if the previous item was a block
            if ft and d_blocky and last_char(ft) != "\n":
                line_height = 1
                left = 0
                baseline = 0

            d_blocky = theme.d_blocky
            d_inline = theme.d_inline
            d_inline_block = theme.d_inline_block

            # Render the element
            rendering = self.render_element(
                child,
                available_width=parent_theme.content_width,
                available_height=parent_theme.content_height,
                left=0 if d_blocky or d_inline_block else left,
                fill=fill,
                align_content=align_content,
            )

            # If the rendering was empty, move on
            if not rendering:
                continue

            # If the rendering was a positioned absolutely or fixed, store it and draw it later
            if theme.theme["position"] == "fixed":
                # self.fixes[(theme.z_index, theme.position)] = rendering
                self.floats[(theme.z_index, theme.position)] = rendering

            # if theme.theme["position"] == "absolute":
            # self.floats[(theme.z_index, theme.position)] = rendering

            # if theme.theme["position"] == "relative":
            # ... TODO ..

            elif theme.theme["float"] == "right":
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

            elif theme.theme["float"] == "left":
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

            elif d_inline and (
                parent_theme.d_inline
                or parent_theme.d_inline_block
                or theme.preformatted
            ):
                new_line.extend(rendering)

            elif d_inline or d_inline_block:

                if d_inline:
                    tokens = fragment_list_to_words(rendering)
                else:
                    tokens = [rendering]

                tokens = list(tokens)

                for token in tokens:

                    token_lines = list(split_lines(token))
                    token_width = max(fragment_list_width(line) for line in token_lines)
                    token_height = len(token_lines)

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

                    if (
                        content_width - float_width_left - float_width_right
                    ) - left - token_width < 0:
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
                                content_width
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
                                    ),
                                    *ft_right,
                                ]
                            )

                        ft = join_lines([ft, *transformed_rows]) if ft else new_line

                        float_lines_left = float_lines_left[line_height:]
                        float_lines_right = float_lines_right[line_height:]

                        new_rows = [[]]
                        new_line = []
                        line_height = 1
                        left = 0
                        baseline = 0

                    if line_height == token_height == 1 or not new_line:
                        new_line.extend(token)
                        new_rows = [new_line]
                        baseline = int(theme.vertical_align * (token_height - 1))

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
                if new_line:
                    ft = join_lines([ft, new_line]) if ft else new_line
                    new_line = []
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
                    content_width
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
                    ),
                    *ft_right,
                ]
                ft = join_lines([ft, row]) if ft else row
            new_line = []

        # Flush any current lines
        if new_line:
            ft = join_lines([ft, new_line]) if ft else new_line

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

    def format_element(
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

        # Apply style to inline elements
        if d_inline:
            ft = apply_style(ft, theme.style)

        # Remove trailing newline from the contents of pre-formatted elements
        if preformatted and (
            (parent_theme and not parent_theme.preformatted) or d_blocky
        ):
            ft = strip_one_trailing_newline(ft)

        # If an element should not overflow it's width / height, truncate it
        if not d_inline and not preformatted:
            if theme.get("overflow_x") == "hidden":
                ft = truncate(ft, content_width, placeholder="", ignore_whitespace=True)
            elif theme.get("overflow_x") == "auto":
                ft = truncate(
                    ft,
                    content_width,
                    placeholder="▹",
                    ignore_whitespace=True,
                    style=theme.style,
                )
            else:
                ft = truncate(
                    ft, content_width, ignore_whitespace=True, style=theme.style
                )

        if theme.get("overflow_y") in {"hidden", "auto"}:
            lines = []
            for i, line in enumerate(split_lines(ft)):
                if i <= content_height:
                    lines.append(line)
            ft = join_lines(lines)

        # Align content
        if align_content and (d_blocky or d_inline_block):
            alignment = theme.text_align

            if alignment != FormattedTextAlign.LEFT:
                ft = align(
                    ft,
                    alignment,
                    width=None if d_inline_block else content_width,
                    style=theme.style,
                    ignore_whitespace=True,
                )

        # # Fill space around block elements so they fill the content width
        if ft and (fill and d_blocky) or d_inline_block:
            pad_width = None
            if d_blocky:
                pad_width = content_width
            elif d_inline_block:
                if theme.width is None:
                    pad_width = max_line_width(ft)
                else:
                    pad_width = content_width
            ft = pad(
                ft,
                width=pad_width,
                char=" ",
                style=theme.style,
            )

        # Use the rendered content width from now on for inline elements
        if d_inline_block or d_inline:
            content_width = max_line_width(ft)

        # Add padding & border
        if d_blocky or d_inline_block or d_inline:
            padding = theme.padding
            border_visibility = theme.border_visibility
            if (any(padding) or any(border_visibility)) and not (
                theme.d_table and theme.border_collapse
            ):
                ft = add_border(
                    ft,
                    style=f"{theme.style} nounderline",
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
            marker_ft = self.render_element(
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
        if d_blocky and theme.margin_auto:
            # Center block contents if margin_left and margin_right are "auto"
            ft = align(
                ft,
                how=FormattedTextAlign.CENTER,
                width=theme.available_width,
                style=parent_style,
            )

        elif any(margin := theme.margin):
            ft = add_border(
                ft=ft,
                style=f"{parent_style} nounderline",
                border_visibility=DiBool.from_value(False),
                padding=margin,
                padding_style=parent_style,
            )

        # Ensure hidden content is blank and styled like the parent
        if theme.hidden:
            ft = [
                (
                    parent_style,
                    "\n".join([" " * len(x) for x in text.split("\n")]),
                )
                for style, text, *_ in ft
            ]

        return ft

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Return formatted text."""
        return self.formatted_text


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.current import create_app_session, set_app
    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles.style import Style

    from euporie.core.app import BaseApp
    from euporie.core.style import HTML_STYLE

    path = UPath(sys.argv[1])

    with create_app_session(input=BaseApp.load_input(), output=BaseApp.load_output()):
        with set_app(BaseApp()):
            with path.open() as f:
                html = HTML(
                    path.open().read(),
                    base=path,
                    collapse_root_margin=False,
                    fill=True,
                )

                print_formatted_text(html, style=Style(HTML_STYLE))
