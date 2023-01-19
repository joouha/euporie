"""Contains a HTML to formatted text parser."""

from __future__ import annotations

import logging
import re
from ast import literal_eval
from bisect import bisect_right
from collections.abc import Mapping
from functools import cached_property, lru_cache
from html.parser import HTMLParser
from math import ceil
from random import randint
from typing import TYPE_CHECKING, NamedTuple

from flatlatex.data import subscript, superscript
from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.border import (
    DiLineStyle,
    DoubleLine,
    GridStyle,
    InvisibleLine,
    LowerLeftEighthLine,
    NoLine,
    ThickDoubleDashedLine,
    ThickLine,
    ThickQuadrupleDashedLine,
    ThinDoubleDashedLine,
    ThinLine,
    ThinQuadrupleDashedLine,
    UpperRightEighthLine,
)
from euporie.core.convert.base import convert, get_format
from euporie.core.convert.utils import data_pixel_size, pixels_to_cell_size
from euporie.core.current import get_app
from euporie.core.data_structures import DiBool, DiInt, DiStr
from euporie.core.formatted_text.table import Table
from euporie.core.formatted_text.utils import (
    FormattedTextAlign,
    add_border,
    align,
    apply_reverse_overwrites,
    apply_style,
    concat,
    fragment_list_width,
    indent,
    join_lines,
    last_line_length,
    lex,
    max_line_width,
    pad,
    paste,
    strip,
    strip_one_trailing_newline,
    truncate,
    wrap,
)
from euporie.core.terminal import tmuxify
from euporie.core.url import load_url

if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Generator,
        Hashable,
        Iterator,
        Union,
    )

log = logging.getLogger(__name__)


class Direction(NamedTuple):
    """A description of a direction."""

    x: "bool" = False
    y: "bool" = False


# Prefer 6-digit hex-colors over 3-digit ones
_COLOR_RE = re.compile("#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})")

_SELECTOR_RE = re.compile(
    "(?:^|\s*(?P<comb>[\s\+\>\~]|(?=::))\s*)(?P<item>(?:::)?[^\s\+>~:[\]]+)?(?P<attr>\[[^\s\+>~:]+\])?(?P<pseudo>\:[^:][^\s\+>~]*)?"
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
    0: {
        "none": NoLine,
        "hidden": InvisibleLine,
        "dotted": NoLine,
        "dashed": NoLine,
        "solid": NoLine,
        "double": NoLine,
        "groove": NoLine,
        "inset": NoLine,
        "outset": NoLine,
        "ridge": NoLine,
    },
    0.00001: {
        "none": NoLine,
        "hidden": InvisibleLine,
        "dotted": ThinQuadrupleDashedLine,
        "dashed": ThinDoubleDashedLine,
        "solid": ThinLine,
        "double": DoubleLine,
        "groove": ThinLine,
        "inset": ThickLine,
        "outset": ThickLine,
        "ridge": DoubleLine,
        ":upper-right": UpperRightEighthLine,
        ":lower-left": LowerLeftEighthLine,
    },
    0.3: {
        "none": NoLine,
        "hidden": InvisibleLine,
        "dotted": ThickQuadrupleDashedLine,
        "dashed": ThickDoubleDashedLine,
        "solid": ThickLine,
        "double": DoubleLine,
        "groove": ThickLine,
        "inset": ThickLine,
        "outset": ThickLine,
        "ridge": DoubleLine,
        ":upper-right": UpperRightEighthLine,
        ":lower-left": LowerLeftEighthLine,
    },
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
}


CSS_PROPERTIES = {
    "display": {"inline", "block", "inline-block", "list-item", "table", "none"},
    "visibility": {"visible", "hidden", "collapse"},
    "opacity": set(),
    # Text
    "color": set(),
    "background_color": set(),
    "font_style": {"normal", "italic", "oblique"},
    "font_weight": {
        "normal",
        "bold",
        "lighter",
        "bolder",
        "100",
        "200",
        "300",
        "400",
        "500",
        "600",
        "700",
        "800",
        "900",
    },
    "text_transform": {"none", "uppercase", "lowercase", "capitalize", "full-width"},
    "text_decoration": {"none", "underline", "overline", "line-through"},
    "text_align": {"start", "end", "left", "right", "center", "justify"},
    "white_space": {"normal", "nowrap", "pre", "pre-wrap", "pre-line", "break-spaces"},
    "overflow_x": {"visible", "hidden", "clip", "scroll", "auto", "hidden visible"},
    "overflow_y": {"visible", "hidden", "clip", "scroll", "auto", "hidden visible"},
    "vertical_align": {
        "baseline",
        "sub",
        "super",
        "text-top",
        "text-bottom",
        "middle",
        "top",
        "bottom",
    },
    # Box
    "padding_top": set(),
    "padding_left": set(),
    "padding_bottom": set(),
    "padding_right": set(),
    "margin_top": set(),
    "margin_left": set(),
    "margin_bottom": set(),
    "margin_right": set(),
    "border_top_width": set(),
    "border_left_width": set(),
    "border_bottom_width": set(),
    "border_right_width": set(),
    "border_top_style": set(),
    "border_left_style": set(),
    "border_bottom_style": set(),
    "border_right_style": set(),
    "border_top_color": set(),
    "border_left_color": set(),
    "border_bottom_color": set(),
    "border_right_color": set(),
    # Position
    "float": {"none", "left", "right", "inline-start", "inline-end"},
    "width": str,
    "height": str,
    "position": {"static", "relative", "absolute", "sticky"},
    "top": str,
    "right": str,
    "bottom": str,
    "left": set(),
    "z_index": set(),
    # Lists
    "list_style_type": {
        "none",
        "disc",
        "circle",
        "square",
        "triangle",
        "disclosure",
        "disclosure",
    },
    "list_style_position": {"inside", "outside"},
}


@lru_cache(maxsize=1_000_000)
def match_css_selector(
    selector: "str",
    attrs: "str",
    pseudo: "str",
    element_name: "str",
    is_first_child_element: "bool",
    is_last_child_element: "bool",
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
        else:
            matched = False

    while selector and matched:

        # Universal selector
        if selector == "*":
            break

        # Element selectors
        if selector[0] not in ".#[":
            if selector.startswith(name := element_name):
                selector = selector[len(name) :]
            else:
                matched = False

        # ID selectors
        if selector.startswith("#"):
            if id_ := element_attrs.get("id"):
                if selector[1:].startswith(id_):
                    selector = selector[1 + len(id_) :]
                else:
                    matched = False
            else:
                matched = False

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
                matched = False

        if not matched:
            break

    # Attribute selectors
    # TODO - chained attribute selectors
    if matched and attrs:
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
        pass
    return parsed_value


def get_integer(value: "str") -> "int|None":
    """Extract the first integer from a string."""
    for word in value.split(" "):
        for c in word.partition(".")[0].split():
            if c.isdigit():
                return int(c)
    return None


_NAMED_COLORS: "dict[str, str]|None" = None
_KNOWN_COLORS: "list[str]|None" = None


def get_color(value: "str") -> "str":
    """Extract a hex color from a string."""
    global _NAMED_COLORS
    global _KNOWN_COLORS
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

        if value in KNOWN_COLORS:
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
                    width := css_dimension(each_value)
                ) is not None or each_value in _BORDER_WIDTH_STYLES:
                    width_value = str(width if width is not None else each_value)
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
            **self.element.dom.browser_css["::default"],
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
        """Sets the space available to the element for rendering."""
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
            return {
                k: v
                for part in (
                    parent_theme.inherited_theme,
                    parent_theme.dom_css_theme,
                    parent_theme.attributes_theme,
                    parent_theme.style_attribute_theme,
                )
                for k, v in part.items()
                if k in _HERITABLE_PROPS
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
        # width
        if (value := attrs.get("width")) is not None:
            theme["width"] = value
        # cellpadding # TODO
        return theme

    def _css_theme(self, css: "dict[str, dict[str, str]]") -> "dict[str, str]":
        """Calculate the theme defined in CSS."""
        specificity_rules = []
        element = self.element
        for selectors, rule in css.items():
            split_selectors = [m.groupdict() for m in _SELECTOR_RE.finditer(selectors)][
                ::-1
            ]

            # Last element in the selector should match the current element
            selector = split_selectors[0]
            if not match_css_selector(
                selector["item"] or "",
                selector["attr"] or "",
                selector["pseudo"] or "",
                element.name,
                element.is_first_child_element,
                element.is_last_child_element,
                **element.attrs,
            ):
                continue

            # All of the parent selectors should match a separate parent in order
            # TODO - combinators
            # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Selectors#combinators
            unmatched_parents: "list[Node]" = [
                x for x in reversed(element.parents) if x
            ]

            _unmatched_parents: "list[Node]"
            if selector["comb"] == ">" and (parent := element.parent):
                _unmatched_parents = [parent]
            else:
                _unmatched_parents = unmatched_parents

            # TODO investigate caching element / selector chains so don't have to
            # iterate through every parent every time

            for selector in split_selectors[1:]:

                for i, parent in enumerate(_unmatched_parents):
                    if parent and match_css_selector(
                        selector["item"] or "",
                        selector["attr"] or "",
                        selector["pseudo"] or "",
                        parent.name,
                        parent.is_first_child_element,
                        parent.is_last_child_element,
                        **parent.attrs,
                    ):
                        # unmatched_parents = unmatched_parents[i + 1 :]

                        if selector["comb"] == ">" and (parent := parent.parent):
                            _unmatched_parents = [parent]
                        else:
                            _unmatched_parents = unmatched_parents[i + 1 :]

                        break
                else:
                    break

            else:
                identifiers = classes = elements = 0
                for selector in split_selectors:
                    item = selector["item"] or ""
                    identifiers += (ids := item.count("#"))
                    classes += (clss := item.count("."))
                    if item != "*" and not ids and not clss:
                        elements += 1
                    classes += (selector["attr"] or "").count("[")
                    classes += (selector["pseudo"] or "").count(":")
                key = (identifiers, classes, elements)
                specificity_rules.append((key, rule))

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
        if value := self.get("width"):
            theme_width = css_dimension(
                value, vertical=False, available=self.available_width
            )
            if theme_width is not None:
                return int(theme_width)
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
        if value is None:
            value = (self.available_width or 0) - self.margin.left - self.margin.right
        if (max_width := self.max_width) is not None and max_width < value:
            value = max_width
        elif (min_width := self.min_width) is not None and min_width > value:
            value = min_width
        if value and self.block:
            value -= self.padding.left + self.padding.right
            value -= self.border_visibility.left + self.border_visibility.right

        return max(value, 0)

    @property
    def content_height(self) -> "int":
        """Return the height available for rendering the element's content."""
        value = self.height
        if value and self.block:
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
                self[f"padding_{direction}"], vertical=vertical, available=a_w
            )
            output[direction] = int((value or 0) + 0.49999)
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
                self[f"margin_{direction}"], vertical=vertical, available=a_w
            )
            # output[direction] = int((value or 0) + 0.49999)
            output[direction] = int((value or 0) + 0.5)
        return DiInt(**output)

    @cached_property
    def margin(self) -> "DiInt":
        """Calculate the margin box."""
        margin = self.base_margin
        element = self.element
        if (
            self.block
            and not self.inline
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
                margin = margin._replace(top=0, bottom=0)

            # Collapse if there is no content separating parent and descendants
            if parent_theme := self.parent_theme:

                parent_padding = parent_theme.padding
                parent_border_visibility = parent_theme.border_visibility

                if (
                    parent_theme.block
                    and element.prev_node_in_flow is None
                    and not parent_border_visibility.top
                    and not parent_padding.top
                ):
                    margin = margin._replace(top=0)

                # Remove the margin from the child
                if (
                    parent_theme.block
                    and element.next_node_in_flow is None
                    and not parent_padding.bottom
                    and not parent_border_visibility.bottom
                ):
                    margin = margin._replace(bottom=0)

            # Replace the margin on the parent
            if (
                (first_child := element.first_child_element)
                and not self.border_visibility.top
                and not self.padding.top
            ):
                child_theme = first_child.theme
                if child_theme.block:
                    # TODO - check this
                    if child_theme.available_width is None:
                        child_theme.update_space(
                            self.available_width, self.available_height
                        )
                    margin = margin._replace(
                        top=max(child_theme.base_margin.top, margin.top)
                    )
            if (
                (last_child := element.last_child_element)
                and not self.padding.bottom
                and not self.border_visibility.bottom
            ):
                child_theme = last_child.theme
                if child_theme.block:
                    # TODO - check this
                    if child_theme.available_width is None:
                        child_theme.update_space(
                            self.available_width, self.available_height
                        )
                    margin = margin._replace(
                        bottom=max(child_theme.base_margin.bottom, margin.bottom)
                    )

            # Margins of adjacent children in the flow are collapsed
            if (prev_sib := element.prev_node_in_flow) and prev_sib.theme.block:
                margin = margin._replace(
                    top=max(0, margin.top - prev_sib.theme.margin.bottom)
                )

        # Do not render top and bottom margins for inline elements
        if self.inline and not self.block:
            margin = margin._replace(top=0, bottom=0)

        return margin

    @cached_property
    def margin_auto(self) -> "bool":
        """Determine if the left and right margins are set to auto."""
        return self["margin_left"] == self["margin_right"] == "auto"

    @cached_property
    def border_style(self) -> "DiStr":
        """Calculate the visibility of the element's borders."""
        fg = self.color
        bg = self.parent_theme.background_color if self.parent_theme else "default"

        output = {}
        for direction in ("top", "left", "bottom", "right"):
            fg_, bg_ = fg, bg
            if border_color := get_color(self[f"border_{direction}_color"]):
                fg_ = border_color

            if getattr(self.border_line, direction) in {
                UpperRightEighthLine,
                LowerLeftEighthLine,
            }:
                bg_ = self.background_color

            output[direction] = f"fg:{fg_} bg:{bg_}"

        return DiStr(**output)

    @cached_property
    def border_visibility(self) -> "DiBool":
        """Calculate the visibility of the element's borders."""
        return DiBool(
            **{
                direction: css_dimension(self[f"border_{direction}_width"]) != 0
                and self[f"border_{direction}_style"] != "none"
                for direction in ("top", "left", "bottom", "right")
            }
        )

    @cached_property
    def border_line(self) -> "DiLineStyle":
        """Calculate the line style."""
        a_w = self.available_width
        output = {}
        for direction in ("top", "right", "bottom", "left"):

            border_width = self[f"border_{direction}_width"]
            size = (
                _BORDER_WIDTHS.get(
                    border_width,
                    css_dimension(border_width, vertical=True, available=a_w),
                )
                or 0
            )
            size = max(0, size)

            if size and self.inline and not self.block:
                if direction == "left":
                    output[direction] = LowerLeftEighthLine
                elif direction == "right":
                    output[direction] = UpperRightEighthLine

            else:
                output[direction] = list(_BORDER_WIDTH_STYLES.values())[
                    bisect_right(list(_BORDER_WIDTH_STYLES.keys()), size) - 1
                ].get(self[f"border_{direction}_style"], NoLine)

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
    def color(self) -> "str":
        """Get the computed theme foreground color."""
        # TODO - transparency
        if bg := get_color(self["color"]):
            return bg
        elif self.parent_theme:
            return self.parent_theme.color
        else:
            return "default"

    @cached_property
    def background_color(self) -> "str":
        """Get the computed theme background color."""
        # TODO - transparency
        if bg := get_color(self["background_color"]):
            return bg
        elif self.parent_theme:
            return self.parent_theme.background_color
        else:
            return "default"

    @cached_property
    def style(self) -> "str":
        """Calculate the output style."""
        parts = [f"fg:{self.color}", f"bg:{self.background_color}"]

        if "bold" in self["font_weight"] or (
            isinstance((weight := try_eval(self["font_weight"])), int) and weight >= 700
        ):
            parts.append("bold")

        if "italic" in self["font_style"] or "oblique" in self["font_style"]:
            parts.append("italic")

        if "underline" in self["text_decoration"]:
            parts.append("underline")

        if "line-through" in self["text_decoration"]:
            parts.append("strike")

        return " ".join(parts)

    @cached_property
    def text_transform(self) -> "Callable[[str], str]|None":
        """Return a function which transforms text."""
        if "uppercase" in self["text_transform"]:
            return str.upper
        elif "lowercase" in self["text_transform"]:
            return str.lower
        elif "capitalize" in self["text_transform"]:
            return str.capitalize
        elif "sub" in self["vertical_align"]:
            return lambda x: "".join(subscript.get(c, c) for c in x)
        elif "super" in self["vertical_align"]:
            return lambda x: "".join(superscript.get(c, c) for c in x)
        else:
            return None

    @cached_property
    def preformatted(self) -> "bool":
        """Determine if the content is pre-formatted."""
        return self["white_space"] in {"pre", "pre-wrap", "pre-line"}

    @cached_property
    def text_align(self) -> "FormattedTextAlign":
        """The text alignment direction."""
        return _TEXT_ALIGNS.get(self["text_align"], FormattedTextAlign.LEFT)

    @cached_property
    def vertical_align(self) -> "float":
        """The vertical alignment direction."""
        return _VERTICAL_ALIGNS.get(self["vertical_align"], 1)

    @cached_property
    def list_style_type(self) -> "str":
        """The bullet character to use for the list."""
        return _LIST_STYLE_TYPES.get(self["list_style_type"], self["list_style_type"])

    @cached_property
    def list_style_position(self) -> "str":
        """Where the list bullet should be located."""
        if "outside" in self["list_style_position"]:
            return "outside"
        else:
            return "inside"

    @cached_property
    def font_size(self) -> "float|int":
        """Get the computed font size for the current element."""
        available = self.parent_theme.font_size if self.parent_theme else 1
        if (
            result := css_dimension(self["font_size"], available=available)
        ) is not None:
            return result
        else:
            return 1

    @cached_property
    def block(self) -> "bool":
        """If the element a block element."""
        return "block" in self["display"] or "table" in self["display"]

    @cached_property
    def inline(self) -> "bool":
        """If the element an inline element."""
        return "inline" in self["display"]

    @cached_property
    def z_index(self) -> "int":
        """The z-index of the element."""
        return get_integer(self["z_index"]) or 0

    @cached_property
    def position(self) -> "DiInt":
        """The position of an element with a relative, absolute or fixed position."""
        # TODO - calculate position based on top, left, bottom,right, width, height
        return DiInt(
            top=int(css_dimension(self["top"], vertical=True) or 0),
            right=int(css_dimension(self["right"], vertical=False) or 0),
            bottom=int(css_dimension(self["bottom"], vertical=True) or 0),
            left=int(css_dimension(self["left"], vertical=False) or 0),
        )

    @cached_property
    def skip(self) -> "bool":
        """Determine if the element should not be displayed."""
        return "none" in self["display"] or (
            (element := self.element).name == "text" and not element.text
        )

    @cached_property
    def hidden(self) -> "bool":
        """Determine if the element is hidden."""
        return try_eval(self["opacity"]) == 0 or "hidden" in self["visibility"]

    @cached_property
    def in_flow(self) -> "bool":
        """Determines if the element is "in-flow"."""
        return (
            not self.skip
            and self["float"] == "none"
            and self["position"] not in {"absolute", "fixed"}
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
    "::default": {
        # Display
        "display": "block",
        "visibility": "visible",
        "opacity": "1.0",
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
        "overflow_x": "visible",
        "overflow_y": "visible",
        "vertical_align": "baseline",
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
        "float": "none",
        "position": "static",
        "top": "0",
        "right": "0",
        "bottom": "0",
        "left": "0",
        "z_index": "0",
        # Lists
        "list_style_type": "none",
        "list_style_position": "inside",
    },
    # "Special" tags (not real HTML tags, just used for rendering)
    "text": {"display": "inline"},  # Use for rendering text
    # Metadata elements which should be hidden
    "head": {"display": "none"},
    "base": {"display": "none"},
    "command": {"display": "none"},
    "link": {"display": "none"},
    "meta": {"display": "none"},
    "noscript": {
        "display": "none",
    },
    "script": {
        "display": "none",
    },
    "style": {"display": "none"},
    "title": {"display": "none"},
    # Inline tags
    "a": {
        "display": "inline",
        "text_decoration": "underline",
        "color": "ansibrightblue",
    },
    "abbr": {"display": "inline"},
    "acronym": {"display": "inline"},
    "audio": {"display": "inline"},
    "b": {"display": "inline", "font_weight": "bold"},
    "bdi": {"display": "inline"},
    "bdo": {"display": "inline"},
    "big": {"display": "inline"},
    "br": {"display": "inline"},
    "canvas": {"display": "inline"},
    "cite": {"display": "inline", "font_style": "italic"},
    "code": {"display": "inline", "background_color": "#333333", "color": "#FFFFFF"},
    "data": {"display": "inline"},
    "datalist": {"display": "inline"},
    "del": {"display": "inline", "text_decoration": "line-through"},
    "dfn": {"display": "inline", "font_style": "italic"},
    "em": {"display": "inline", "font_style": "italic"},
    "embed": {"display": "inline"},
    "i": {"display": "inline", "font_style": "italic"},
    "iframe": {"display": "inline"},
    "img": {"display": "inline-block", "overflow_x": "hidden", "overflow_y": "hidden"},
    "ins": {"display": "inline", "text_decoration": "underline"},
    "kbd": {"display": "inline", "background_color": "#333344", "color": "#FFFFFF"},
    "label": {"display": "inline"},
    "map": {"display": "inline"},
    "mark": {"display": "inline", "color": "black", "background_color": "#FFFF00"},
    "meter": {"display": "inline"},
    "object": {"display": "inline"},
    "output": {"display": "inline"},
    "picture": {"display": "inline"},
    "progress": {"display": "inline"},
    "q": {"display": "inline"},
    "ruby": {"display": "inline"},
    "s": {"display": "inline", "text_decoration": "line-through"},
    "samp": {"display": "inline", "background_color": "#334433", "color": "#FFFFFF"},
    "select": {"display": "inline"},
    "slot": {"display": "inline"},
    "small": {"display": "inline"},
    "span": {"display": "inline"},
    "strong": {"display": "inline", "font_weight": "bold"},
    "sub": {
        "display": "inline",
        "vertical_align": "sub",
    },
    "sup": {
        "display": "inline",
        "vertical_align": "super",
    },
    "svg": {"display": "inline"},
    "template": {"display": "inline"},
    "textarea": {"display": "inline"},
    "time": {"display": "inline"},
    "u": {"display": "inline", "text_decoration": "underline"},
    "tt": {"display": "inline"},
    "var": {"display": "inline", "font_style": "italic"},
    "video": {"display": "inline"},
    "wbr": {"display": "inline"},
    # Custom inline tags
    "math": {
        "display": "inline",
        "text_align": "center",
        "margin_top": "1rem",
        "margin_bottom": "1rem",
    },
    # Alignment
    "center": {"text_align": "center"},
    # Table elements
    "table": {
        "display": "table",
    },  #
    "td": {
        "display": "table-cell",
    },
    "th": {
        "display": "table-cell",
        "font_weight": "bold",
        "text_align": "center",
    },
    # Forms & related elements
    "option": {"display": "none"},
    "input": {
        "display": "inline-block",
        "color": "#000000",
        "border_top_style": ":lower-left",
        "border_right_style": ":lower-left",
        "border_bottom_style": ":upper-right",
        "border_left_style": ":upper-right",
        "border_top_width": "2px",
        "border_right_width": "2px",
        "border_bottom_width": "2px",
        "border_left_width": "2px",
        "vertical_align": "middle",
    },
    "input[type=hidden]": {"display": "none"},
    "input[type=text]": {
        "background_color": "#FFFFFF",
        "border_top_color": "#606060",
        "border_right_color": "#E9E7E3",
        "border_bottom_color": "#E9E7E3",
        "border_left_color": "#606060",
    },
    "input[type=button]": {
        "background_color": "#d4d0c8",
        "border_right": "#606060",
        "border_bottom": "#606060",
        "border_left": "#ffffff",
        "border_top": "#ffffff",
    },
    "input[type=submit]": {
        "background_color": "#d4d0c8",
        "border_right": "#606060",
        "border_bottom": "#606060",
        "border_left": "#ffffff",
        "border_top": "#ffffff",
    },
    "input[type=reset]": {
        "background_color": "#d4d0c8",
        "border_right": "#606060",
        "border_bottom": "#606060",
        "border_left": "#ffffff",
        "border_top": "#ffffff",
    },
    "button": {
        "display": "inline-block",
        "color": "#000000",
        "border_top_style": ":lower-left",
        "border_right_style": ":lower-left",
        "border_bottom_style": ":upper-right",
        "border_left_style": ":upper-right",
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
    # Custom default styles
    "body": {
        "display": "block",
    },
    "h1": {
        "display": "block",
        "font_weight": "bold",
        "border_bottom_style": "solid",
        "text_decoration": "underline",
        "border_bottom_width": "thick",
        "padding_bottom": "2rem",
        "margin_top": "2rem",
        "margin_bottom": "2em",
    },
    "h2": {
        "display": "block",
        "font_weight": "bold",
        "border_bottom_style": "double",
        "border_bottom_width": "thick",
        "padding_bottom": "1.5rem",
        "margin_top": "1.5rem",
        "margin_bottom": "1.5rem",
    },
    "h3": {
        "display": "block",
        "font_weight": "bold",
        "font_style": "italic",
        "border_bottom_style": ":lower-left",
        "border_bottom_width": "thin",
        "padding_top": "1rem",
        "padding_bottom": "1rem",
        "margin_bottom": "1.5rem",
    },
    "h4": {
        "display": "block",
        "text_decoration": "underline",
        "border_bottom_style": "solid",
        "border_bottom_width": "thin",
        "padding_top": "1rem",
        "padding_bottom": "1rem",
        "margin_bottom": "1.5rem",
    },
    "h5": {
        "display": "block",
        "border_bottom_style": "dashed",
        "border_bottom_width": "thin",
        "margin_bottom": "1.5rem",
    },
    "h6": {
        "display": "block",
        "font_style": "italic",
        "border_bottom_style": "dotted",
        "border_bottom_width": "thin",
        "margin_bottom": "1.5rem",
    },
    "blockquote": {
        "display": "block",
        "margin_top": "1em",
        "margin_bottom": "1em",
        "padding_left": "1em",
        "border_left_width": "thick",
        "border_left_style": "solid",
        "border_left_color": "darkmagenta",
    },
    "hr": {
        "margin_top": "1rem",
        "margin_bottom": "1rem",
        "border_top_width": "thin",
        "border_top_style": "solid",
        "border_top_color": "ansired",
    },
    "p": {"margin_top": "1em", "margin_bottom": "1em"},
    "pre": {"margin_top": "1em", "margin_bottom": "1em", "white_space": "pre"},
    "caption": {"text_align": "center"},
    # Lists
    "::marker": {
        "display": "inline",
        "padding_right": "1em",
        "text_align": "right",
    },
    "ol": {
        "display": "block",
        "list_style_type": "decimal",
        "list_style_position": "outside",
        "padding_left": "4em",
        "margin_top": "1em",
        "margin_bottom": "1em",
    },
    "ul": {
        "display": "block",
        "list_style_type": "disc",
        "list_style_position": "outside",
        "padding_left": "3em",
        "margin_top": "1em",
        "margin_bottom": "1em",
    },
    "menu": {
        "display": "block",
        "list_style_type": "disc",
        "list_style_position": "outside",
        "padding_left": "3em",
        "margin_top": "1em",
        "margin_bottom": "1em",
    },
    "dir": {
        "display": "block",
        "list_style_type": "disc",
        "list_style_position": "outside",
        "padding_left": "3em",
        "margin_top": "1em",
        "margin_bottom": "1em",
    },
    "li": {"display": "block"},
    "ol li::marker": {"color": "ansicyan"},
    "ul li::marker": {"color": "ansiyellow"},
    # No top or bottom margins for nested lists
    # Also use a circle marker for 2-deep unordered lists
    "dir dir": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "dir dl": {"margin_top": "0em", "margin_bottom": "0em"},
    "dir ol": {"margin_top": "0em", "margin_bottom": "0em"},
    "dir menu": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "dir ul": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "dl dir": {"margin_top": "0em", "margin_bottom": "0em"},
    "dl dl": {"margin_top": "0em", "margin_bottom": "0em"},
    "dl ol": {"margin_top": "0em", "margin_bottom": "0em"},
    "dl menu": {"margin_top": "0em", "margin_bottom": "0em"},
    "dl ul": {"margin_top": "0em", "margin_bottom": "0em"},
    "ol dir": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "ol dl": {"margin_top": "0em", "margin_bottom": "0em"},
    "ol ol": {"margin_top": "0em", "margin_bottom": "0em"},
    "ol menu": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "ol ul": {"margin_top": "0em", "margin_bottom": "0em", "list_style_type": "circle"},
    "menu dir": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "menu dl": {"margin_top": "0em", "margin_bottom": "0em"},
    "menu ol": {"margin_top": "0em", "margin_bottom": "0em"},
    "menu menu": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "menu ul": {
        "list_style_type": "circle",
        "margin_top": "0em",
        "margin_bottom": "0em",
    },
    "ul dir": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "ul dl": {"margin_top": "0em", "margin_bottom": "0em"},
    "ul ol": {"margin_top": "0em", "margin_bottom": "0em"},
    "ul menu": {
        "margin_top": "0em",
        "margin_bottom": "0em",
        "list_style_type": "circle",
    },
    "ul ul": {"margin_top": "0em", "margin_bottom": "0em", "list_style_type": "circle"},
    # Use a square marker for 3-deep unordered lists
    "dir dir dir": {"list_style_type": "square"},
    "dir dir menu": {"list_style_type": "square"},
    "dir dir ul": {"list_style_type": "square"},
    "dir menu dir": {"list_style_type": "square"},
    "dir menu menu": {"list_style_type": "square"},
    "dir menu ul": {"list_style_type": "square"},
    "dir ol dir": {"list_style_type": "square"},
    "dir ol menu": {"list_style_type": "square"},
    "dir ol ul": {"list_style_type": "square"},
    "dir ul dir": {"list_style_type": "square"},
    "dir ul menu": {"list_style_type": "square"},
    "dir ul ul": {"list_style_type": "square"},
    "menu dir dir": {"list_style_type": "square"},
    "menu dir menu": {"list_style_type": "square"},
    "menu dir ul": {"list_style_type": "square"},
    "menu menu dir": {"list_style_type": "square"},
    "menu menu menu": {"list_style_type": "square"},
    "menu menu ul": {"list_style_type": "square"},
    "menu ol dir": {"list_style_type": "square"},
    "menu ol menu": {"list_style_type": "square"},
    "menu ol ul": {"list_style_type": "square"},
    "menu ul dir": {"list_style_type": "square"},
    "menu ul menu": {"list_style_type": "square"},
    "menu ul ul": {"list_style_type": "square"},
    "ol dir dir": {"list_style_type": "square"},
    "ol dir menu": {"list_style_type": "square"},
    "ol dir ul": {"list_style_type": "square"},
    "ol menu dir": {"list_style_type": "square"},
    "ol menu menu": {"list_style_type": "square"},
    "ol menu ul": {"list_style_type": "square"},
    "ol ol dir": {"list_style_type": "square"},
    "ol ol menu": {"list_style_type": "square"},
    "ol ol ul": {"list_style_type": "square"},
    "ol ul dir": {"list_style_type": "square"},
    "ol ul menu": {"list_style_type": "square"},
    "ol ul ul": {"list_style_type": "square"},
    "ul dir dir": {"list_style_type": "square"},
    "ul dir menu": {"list_style_type": "square"},
    "ul dir ul": {"list_style_type": "square"},
    "ul menu dir": {"list_style_type": "square"},
    "ul menu menu": {"list_style_type": "square"},
    "ul menu ul": {"list_style_type": "square"},
    "ul ol dir": {"list_style_type": "square"},
    "ul ol menu": {"list_style_type": "square"},
    "ul ol ul": {"list_style_type": "square"},
    "ul ul dir": {"list_style_type": "square"},
    "ul ul menu": {"list_style_type": "square"},
    "ul ul ul": {"list_style_type": "square"},
    # Summary/details
    "details": {
        "display": "block",
        "list_style_type": "disclosure-closed",
        "list_style_position": "inside",
    },
    "details[open] summary": {"list_style_type": "disclosure-open"},
    "summary": {"font_weight": "bold"},
    #
    # Custom for Jupyter
    ".dataframe": {
        "border_top_width": "0",
        "border_right_width": "0",
        "border_bottom_width": "0",
        "border_left_width": "0",
        "border_top_style": "none",
        "border_right_style": "none",
        "border_bottom_style": "none",
        "border_left_style": "none",
    },
    #
    # Custom for markdownit-py
    ".block": {"display": "block"},
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
                text = re.sub(r"\s+", " ", text.strip("\n").replace("\n", " "))

                # This next is does not appear to be needed
                """
                if text and (
                    self.is_first_child_node
                    or (
                        (prev_element := self.prev_element)
                        and (prev_theme := prev_element.theme).block
                        and not prev_theme.inline
                    )
                ):
                    text = text.lstrip()

                if text and (
                    self.is_last_child_node
                    or (
                        (next_element := self.next_element)
                        and (next_theme := next_element.theme).block
                        and not next_theme.inline
                    )
                ):
                    text = text.rstrip()
                """

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
        if (parent := self.parent) and (child_elements := list(parent.child_elements)):
            return child_elements[-1] == self
        return False

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
        """String representation of the element."""
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


def parse_styles(soup: "Node", base_url: "UPath") -> "dict[str, dict[str, str]]":
    """Collect all CSS styles from style tags."""
    rules: "dict[str, dict[str, str]]" = {}
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
        css_str = css_str.strip().replace("\n", "")
        # Remove comments
        css_str = re.sub(r"\/\*[^\*]+\*\/", "", css_str)
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
                    # TODO - more CSS matching complex rules
                    for selector in map(str.strip, selectors.split(",")):
                        content = content.strip().rstrip(";")
                        rule_content = parse_css_content(content)
                        if rule_content:
                            if selector in rules:
                                rules[selector].update(rule_content)
                            else:
                                rules[selector] = rule_content

    return rules


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    formatted_text: "StyleAndTextTuples"

    def _render_list(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
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
        return self.render_element(
            element=element,
            parent_theme=parent_theme,
            available_width=available_width,
            available_height=available_height,
            left=left,
            fill=fill,
            align_content=align_content,
        )

    render_ul = _render_list
    render_ol = _render_list

    def render_li(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render a list item."""
        # Get element theme
        theme = element.theme
        theme.update_space(available_width, available_height)
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
        ft = self.render_element(
            element,
            parent_theme=parent_theme,
            available_width=available_width,
            available_height=available_height,
            left=left,
            fill=fill,
            align_content=align_content,
        )
        return ft

    render_summary = render_li

    def __init__(
        self,
        markup: "str",
        base: "Union[UPath, str]|None" = None,
        width: "int|None" = None,
        height: "int|None" = None,
        collapse_root_margin: "bool" = False,
        fill: "bool" = True,
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

        """
        self.browser_css: "dict[str, dict[str, str]]" = {**_BROWSER_CSS}
        self.css: "dict[str, dict[str, str]]" = {}

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

        # Render the markup
        self.render(width, height)

    def render(self, width: "int|None", height: "int|None") -> "None":
        """Render the current markup at a given size."""
        if not width or not height:
            size = get_app_session().output.get_size()
        self.width = width or size.columns
        self.height = height or size.rows

        ft = self.render_element(
            self.soup,
            parent_theme=self.soup.theme,
            available_width=self.width,
            available_height=self.height,
            fill=self.fill,
        )

        # Apply "ReverseOverwrite"s
        ft = apply_reverse_overwrites(ft)
        # ft = [x for x in ft if "[ReverseOverwrite]" not in x[0]]

        self.formatted_text = ft

    def render_contents(
        self,
        contents: "list[Node]",
        parent_theme: "Theme",
        available_width: "int" = 80,
        available_height: "int" = 999999999,
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements.

        Args:
            contents: The list of parsed elements to render
            parent_theme: The theme of the element's parent element
            available_width: The width available for rendering the elements
            available_height: The height available for rendering the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        ft: "StyleAndTextTuples" = []
        floats = {}
        line_height = 1
        baseline = 0

        for element in contents:

            # Convert tags with "math" class to <math> tag
            if "math" in element.attrs.get("class", []):
                element.name = "math"

            # theme = element.theme(parent_theme, available_width, available_height)
            theme = element.theme
            theme.update_space(available_width, available_height)

            # Do not render tags set to display:none
            if theme["display"] == "none":
                continue

            # Is the current element a block element?
            block = theme.block
            inline = theme.inline

            # Start block elements on a new line
            if ft and block and not inline and ft[-1][-1] != "\n":
                ft.append(("", "\n"))

            # If there is a special method for rendering the block, use it; otherwise
            # use the generic `render_element` function
            render_func = getattr(self, f"render_{element.name}", self.render_element)

            # Non-inline blocks always start on a new line
            # if inline:
            # left = last_line_length(ft, rows=line_height)

            # Render the element
            # p rint(
            # "<",
            # *(x.name for x in element.parents),
            # element.name,
            # left,
            # # element.text.__repr__(),
            # [x[1] for x in ft],
            # )

            rendering = render_func(
                element,
                parent_theme=parent_theme,
                available_width=available_width,
                available_height=available_height,
                left=0 if block else left,
                fill=fill,
                align_content=align_content,
            )

            # If the rendering was empty, move on
            if not rendering:
                continue

            # If the rendering was a float, store it and draw it later
            if theme["position"] == "fixed":
                floats[(theme.z_index, theme.position)] = rendering

            # If the rendering was inline (an inline-block or text), add it to the end
            # of the current output. This might involve re-aligning the last line in
            # the output, which could have been an inline-block
            elif inline:

                # If this is an inline-block element, align and add the whole rendering
                if block:
                    next_part = rendering
                    next_part_lines = list(split_lines(next_part))
                    remaining_lines = []

                # Otherwise this is inline text, so we only want to align and add the
                # first line of the rendering. (The text will already be wrapped and
                # the first line the correct length for the remaining space)
                else:
                    lines = list(split_lines(rendering))
                    next_part = lines[0]
                    next_part_lines = list(split_lines(next_part))
                    remaining_lines = lines[1:]

                # Start a new line if there is not enough space to fit the next part on
                # the current line
                next_part_width = max(
                    fragment_list_width(line) for line in next_part_lines
                )

                if next_part_width > available_width - left:
                    ft.append(("", "\n"))
                    left = last_line_length(ft)
                    line_height = 1

                if next_part:

                    # If the new part and the existing line are both only one row
                    # high, we can just slam the new part on the end of the output
                    if (new_line_height := max(line_height, len(next_part_lines))) <= 1:
                        ft.extend(next_part)

                    # Otherwise, we need extract the previous line, align it vertically
                    # with the new part, concatenate the two, and update the last line
                    else:

                        # Get previous line part
                        ft_lines = list(split_lines(ft))
                        last_line = join_lines(ft_lines[-line_height:])
                        # Concat aligned previous n lines and aligned new content
                        new_line, baseline = concat(
                            ft_a=last_line,
                            ft_b=next_part,
                            baseline_a=baseline,
                            baseline_b=int(
                                theme.vertical_align
                                * (len(list(split_lines(next_part))) - 1)
                            ),
                            style=parent_theme.style,
                        )
                        # Replace last y-lines with concatenated result
                        ft = join_lines([*ft_lines[:-line_height], new_line])
                        # Set last line height to new height
                        line_height = new_line_height
                left += next_part_width

                # If there is anything left from the rendering, add this to the output
                if remaining_lines:
                    ft.append(("", "\n"))
                    ft.extend(join_lines(remaining_lines))
                    left = last_line_length(ft)
                    line_height = 1

            # Otherwise we are rendering a block-like element, which gets added to the
            # end of the output
            elif rendering:
                ft.extend(rendering)
                if not element.is_last_child_node:
                    ft.append(("", "\n"))
                line_height = 1
                left = 0

            # p rint(
            # ">",
            # *(x.name for x in element.parents),
            # element.name,
            # left,
            # # element.text.__repr__(),
            # [x[1] for x in ft],
            # )

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

        # Draw floats
        for (_, position), float_ft in sorted(floats.items()):
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

        return ft

    def render_element(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a block element.

        Args:
            element: The list of parsed elements to render
            parent_theme: The theme of the element's parent element
            available_width: The width available for rendering the elements
            available_height: The height available for rendering the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        theme = element.theme  # (parent_theme, available_width, available_height)
        theme.update_space(available_width, available_height)

        if theme.skip:
            return []

        block = theme.block
        inline = theme.inline
        border_visibility = theme.border_visibility

        content_width = theme.content_width
        content_height = theme.content_height

        if element.name != "::before":
            # TODO - do not parse all
            before_node = Node(dom=element.dom, name="::before", parent=element)
            if text := before_node.theme.get("content", "").strip('"'):
                before_node.contents.append(
                    Node(dom=element.dom, name="text", parent=before_node, text=text)
                )
                element.contents.insert(0, before_node)

        # Render the contents
        ft = self.render_contents(
            element.contents,
            parent_theme=theme,
            available_width=content_width,
            available_height=content_height,
            # left=0,
            left=left,
            fill=False if inline and block else fill,
            align_content=False if inline and block else align_content,
        )

        # Remove trailing newline from the contents of blocks or pre-formatted elements
        if block or theme.preformatted:
            ft = strip_one_trailing_newline(ft)

        # If an element should not overflow it's width / height, truncate it
        if theme.get("overflow_x") == "hidden":
            ft = truncate(ft, content_width, placeholder="", ignore_whitespace=True)
        if theme.get("overflow_y") == "hidden":
            lines = []
            for i, line in enumerate(split_lines(ft)):
                if i <= content_height:
                    lines.append(line)
            ft = join_lines(lines)

        # Apply tag formatting
        if format_func := getattr(self, f"format_{element.name}", None):
            ft = format_func(
                ft,
                content_width,
                content_height,
                left,
                element,
                theme,
            )

        # Lex the text
        # TODO - do this upstream in markdown -> HTML conv.
        for class_name in element.attrs.get("class", "").split():
            if class_name.startswith("language-"):
                ft = strip(ft, left=False, right=True, chars="\n")
                ft = lex(ft, lexer_name=class_name[9:])

        # Center the contents if margin_left and margin_right are "auto"

        if block:

            # Align the output
            if ft and not theme.preformatted and not theme.margin_auto:
                if (
                    align_content
                    and (alignment := theme.text_align) != FormattedTextAlign.LEFT
                ):
                    ft = align(
                        ft,
                        alignment,
                        width=content_width if not inline else None,
                        style=theme.style,
                        ignore_whitespace=True,
                    )

            # Fill space around block elements so they fill the width
            if ft and fill and not inline and not theme.margin_auto:
                ft = pad(ft, width=content_width, char=" ", style=theme.style)

        padding = theme.padding

        if inline and not block:

            # Do not render top and bottom borders for inline elements
            # if there is no top or bottom padding
            if not padding.top:
                border_visibility = border_visibility._replace(top=False)
            if not padding.bottom:
                border_visibility = border_visibility._replace(bottom=False)

            # Do not render top and bottom padding for inline elements
            padding = padding._replace(top=0, bottom=0)

        # Add padding & border
        if any(padding) or any(theme.border_visibility):

            ft = add_border(
                ft,
                style=f"{theme.style} nounderline",
                border_grid=theme.border_grid,
                width=content_width if not ft else None,
                border_visibility=border_visibility,
                border_style=theme.border_style,
                padding=padding,
                # padding_style="bg:green",
            )

        # The "::marker" element is drawn in the margin, before any padding
        # If the element has no margin, it can end up in the parent's padding
        # We use [ReverseOverwrite] fragments to ensure the marker is ignored
        # now and written over the margin later.
        if element.marker is not None:
            marker_ft = self.render_element(
                element.marker,
                parent_theme=theme,
                available_width=99999,
                available_height=available_height,
                left=0,
                fill=False,
                align_content=False,
            )
            ft = [
                *apply_style(marker_ft, "[ReverseOverwrite]"),
                *ft,
            ]

        # Render the margin
        if theme.margin_auto:
            ft = align(
                ft,
                how=FormattedTextAlign.CENTER,
                style=parent_theme.style,
                width=available_width,
            )

        elif any(margin := theme.margin):
            ft = add_border(
                ft=ft,
                style=f"{parent_theme.style} nounderline",
                border_visibility=DiBool.from_value(False),
                padding=margin,
                padding_style=parent_theme.style,
                # padding_style="bg:purple",
            )

        return ft

    def render_text(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
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

            style = parent_theme.style

            # Ensure hidden text is blank and not underlined
            if parent_theme.hidden:
                text = " " * len(text)
                style = f"{style} nounderline"

            ft = [(style, text)]

            # Wrap non-pre-formatted text
            if not parent_theme.preformatted:
                ft = wrap(ft, available_width, left=left, style=style)

        return ft

    def render_input(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render an input element."""
        element.contents.insert(
            0,
            Node(
                dom=self,
                name="text",
                parent=element,
                text=element.attrs.get("value", ""),
            ),
        )
        ft = self.render_element(
            element,
            parent_theme=parent_theme,
            available_width=available_width,
            available_height=available_height,
            left=left,
            fill=fill,
            align_content=align_content,
        )
        return ft

    def render_table(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
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
        table_theme.update_space(available_width, available_height)

        table = Table(
            align=table_theme.text_align,
            style=table_theme.style,
            border_line=table_theme.border_line,
            border_style=table_theme.border_style,
            padding=DiInt(0, 0, 0, 0),
            width=Dimension(
                min=table_theme.min_width,
                preferred=table_theme.content_width if "width" in table_theme else None,
                max=table_theme.max_width or available_width,
            ),
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
                                table_theme.content_width,
                                table_theme.content_height,
                            )
                            cell = row.new_cell(
                                # text=" ",
                                text=self.render_contents(
                                    td.contents,
                                    parent_theme=td.theme,
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
                        cell.text = self.render_contents(
                            td.contents,
                            parent_theme=td.theme,
                            # TODO - get actual colspan cell widths properly
                            available_width=(
                                table_theme.content_width
                                if cell.colspan > 1
                                else col_width
                            )
                            - cell.computed_padding.left
                            - cell.computed_padding.right,
                            # - cell.computed_border_width.left
                            # - cell.computed_border_width.right,
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
                    parent_theme=table_theme,
                    available_width=table_width,
                    available_height=available_height,
                    left=0,
                    fill=True,
                )
                if ft_caption:
                    ft.extend(
                        [
                            ("", "\n"),
                            *ft_caption,
                            ("", "\n"),
                        ]
                    )

        ft.extend(ft_table)

        return ft

    def render_details(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Render an expand summary / details."""
        ft: "StyleAndTextTuples" = []
        theme = element.theme
        theme.update_space(available_width, available_height)

        summary_element = None
        for child in element.contents:
            if child.name == "summary":
                summary_element = child
                break

        if summary_element is not None:
            ft.extend(
                self.render_summary(
                    summary_element,
                    parent_theme=theme,
                    available_width=available_width,
                    available_height=available_height,
                    left=left,
                    fill=fill,
                )
            )
            ft.append(("", "\n"))

        if "open" in element.attrs:
            ft.extend(
                self.render_contents(
                    [e for e in element.contents if e is not summary_element],
                    parent_theme=theme,
                    available_width=available_width,
                    available_height=available_height,
                    left=left,
                    fill=fill,
                ),
            )
            ft.append(("", "\n"))
        return ft

    def _render_image(
        self,
        data: "Any",
        format_: "str",
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        cols, aspect = pixels_to_cell_size(*data_pixel_size(data, format_=format_))
        # Manually set a value if we don't have one
        cols = cols or 20
        aspect = aspect or 0.5
        # Scale down the image to fit to width
        cols = min(available_width, cols)
        rows = ceil(cols * aspect)
        # Convert the image to formatted-text
        result = (
            convert(
                data,
                from_=format_,
                to="formatted_text",
                cols=cols,
                rows=rows,
                # TODO - set background color
                path=element.attrs.get("src"),
            )
            or []
        )
        # Remove trailing new-lines
        result = strip(result, chars="\n", left=False)
        return result

    def render_img(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Display images rendered as ANSI art."""
        src = str(element.attrs.get("src", ""))
        # Attempt to load the image url
        if data := load_url(src, self.base):
            # Display it graphically
            format_ = get_format(src, default="png")
            ft = self._render_image(
                data,
                format_,
                element=element,
                parent_theme=parent_theme,
                available_width=available_width,
                available_height=available_height,
                left=left,
                fill=fill,
                align_content=align_content,
            )
            return ft
        # Otherwise, display the image title
        else:
            return self.render_element(
                element=element,
                parent_theme=parent_theme,
                available_width=available_width,
                available_height=available_height,
                left=left,
                fill=fill,
                align_content=align_content,
            )

    def render_svg(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Display images rendered as ANSI art."""
        element.theme.update_space(available_width, available_height)
        # Ensure xml namespace is set. These muse be first attributes
        if "xmlns:xlink" not in element.attrs:
            element.attrs = {
                "xmlns:xlink": "http://www.w3.org/1999/xlink",
                **element.attrs,
            }
        if "xmlns" not in element.attrs:
            element.attrs = {"xmlns": "http://www.w3.org/2000/svg", **element.attrs}
        # Ensure svg width and height are set
        element.attrs.setdefault("width", f"{element.theme.content_width}")
        element.attrs.setdefault("height", f"{element.theme.content_height}")
        ft = self._render_image(
            element._outer_html(),
            "svg",
            element,
            parent_theme,
            available_width,
            available_height,
            left,
            fill,
            align_content=align_content,
        )
        return ft

    def render_math(
        self,
        element: "Node",
        parent_theme: "Theme",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        fill: "bool" = True,
        align_content: "bool" = True,
    ) -> "StyleAndTextTuples":
        """Display LaTeX maths rendered as unicode text."""
        text = "".join(desc.text for desc in element.descendents)
        for desc in element.descendents:
            if desc.name == "text":
                desc.text = convert(text, "latex", "ansi")
        return self.render_element(
            element,
            parent_theme,
            available_width,
            available_height,
            left,
            fill,
            align_content=align_content,
        )

    ###

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Formatted text magic method."""
        return self.formatted_text

    # Tag formatting methods

    @staticmethod
    def format_img(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "Node",
        theme: "Theme",
    ) -> "StyleAndTextTuples":
        """Fallback to formatting an image as title text if nothing loaded."""
        if not ft:
            bounds = ("", "")
            # Add fallback text if there is no image title
            title = str(element.attrs.get("alt"))
            # Try getting the filename
            if not title:
                src = str(element.attrs.get("src", ""))
                if not src.startswith("data:"):
                    title = src.rsplit("/", 1)[-1]
            if not title:
                title = "Image"
            # Add the sunrise emoji to represent an image. I would use :framed_picture:, but it
            # requires multiple code-points and causes breakage in many terminals
            ft = [
                ("reverse", f"{bounds[0]}"),
                ("", f"🌄 {title}"),
                ("reverse", f"{bounds[1]}"),
            ]
            ft = apply_style(ft, theme.style)
        return ft

    @staticmethod
    def format_br(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "Node",
        theme: "Theme",
    ) -> "StyleAndTextTuples":
        """Format line breaks."""
        return [("", "\n")]

    @staticmethod
    def format_a(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "Node",
        theme: "Theme",
    ) -> "StyleAndTextTuples":
        """Format hyperlinks and adds link escape sequences."""
        href = element.attrs.get("href")
        # TODO - re-endable links
        return ft
        if href:
            link_id = randint(0, 999999)  # noqa S311
            result = []
            for line in split_lines(ft):
                result += [
                    ("[ZeroWidthEscape]", tmuxify(f"\x1b]8;id={link_id};{href}\x1b\\")),
                    *line,
                    ("[ZeroWidthEscape]", tmuxify("\x1b]8;;\x1b\\")),
                    ("", "\n"),
                ]
            result.pop()
            return result
        else:
            return ft

    @staticmethod
    def format_details(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "Node",
        theme: "Theme",
    ) -> "StyleAndTextTuples":
        """Format details indented."""
        ft = strip(ft, chars="\n")
        ft = indent(ft, margin="   ")
        return ft

    @staticmethod
    def format_q(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "Node",
        theme: "Theme",
    ) -> "StyleAndTextTuples":
        """Format an inline quote."""
        return [("", '"'), *ft, ("", '"')]

    @staticmethod
    def format_input(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "Node",
        theme: "Theme",
    ) -> "StyleAndTextTuples":
        """Format an input element."""
        if element.attrs.get("type") in {
            "text",
            "password",
            "email",
            "number",
            "search",
            "tel",
            "text",
            "url",
        }:
            content_width = min(
                try_eval(size) if (size := element.attrs.get("size")) else 20,
                theme.content_width,
            )
            ft = align(ft, how=theme.text_align, width=content_width, style=theme.style)
        return ft


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.current import create_app_session, set_app
    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles.style import Style
    from upath import UPath

    from euporie.core.app import BaseApp
    from euporie.core.style import HTML_STYLE

    path = UPath(sys.argv[1])

    with create_app_session(input=BaseApp.load_input(), output=BaseApp.load_output()):
        with set_app(BaseApp()):
            with path.open() as f:

                print_formatted_text(
                    HTML(
                        path.open().read(),
                        base=path,
                        collapse_root_margin=False,
                        fill=True,
                    ),
                    style=Style(HTML_STYLE),
                )
