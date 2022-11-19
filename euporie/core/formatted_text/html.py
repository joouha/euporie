"""Contains a HTML to formatted text parser."""

from __future__ import annotations

import logging
import re
from ast import literal_eval
from collections import ChainMap, defaultdict
from functools import cached_property, lru_cache, partial
from html.parser import HTMLParser
from math import ceil
from random import randint
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.formatted_text.utils import fragment_list_width, split_lines

from euporie.core.border import (
    BorderLineStyle,
    Double,
    Invisible,
    Padding,
    Rounded,
    Thick,
    Thin,
)
from euporie.core.convert.base import convert, get_format
from euporie.core.convert.utils import data_pixel_size, pixels_to_cell_size
from euporie.core.formatted_text.table import Table
from euporie.core.formatted_text.utils import (
    FormattedTextAlign,
    add_border,
    align,
    apply_style,
    indent,
    last_line_length,
    lex,
    max_line_width,
    paste,
    strip,
    truncate,
    wrap,
)
from euporie.core.terminal import tmuxify
from euporie.core.url import load_url

if TYPE_CHECKING:
    from typing import Any, Generator, Hashable, Optional, Union

log = logging.getLogger(__name__)


class Position(NamedTuple):
    """A description of a floating element's location."""

    top: "Optional[int]" = None
    right: "Optional[int]" = None
    bottom: "Optional[int]" = None
    left: "Optional[int]" = None


class Direction(NamedTuple):
    """A description of a direction."""

    x: "bool" = False
    y: "bool" = False


# Prefer 6-digit hex-colors over 3-digit ones
_COLOR_RE = re.compile("#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})")

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


_BORDER_WIDTHS = {
    "0": BorderLineStyle(Invisible, Invisible, Invisible, Invisible),
    "1": BorderLineStyle(Thin, Thin, Thin, Thin),
    "2": BorderLineStyle(Thick, Thick, Thick, Thick),
}


def _inline_default() -> "dict[str, Any]":
    return {"inline": True, "block": False, "margin": Padding(0, 0, 0, 0)}


# The default theme to apply to various elements
_ELEMENT_BASE_THEMES: "defaultdict[str, dict[str, Any]]" = defaultdict(
    dict,
    {
        # Default theme for a tag
        "default": {
            "padding": Padding(None, None, None, None),
            "margin": Padding(0, 0, 0, 0),
            "align": FormattedTextAlign.LEFT,
            "border": None,
            "border_collapse": True,
            "language": None,
            "style": "",
            "invisible": False,
            "skip": False,
            "block": True,
            "float": False,
            "zindex": 0,
            "position": Position(None, None, None, None),
            "inline": False,
            # Styles
            "style_classes": [],
        },
        # "Special" tags (not real HTML tags, just used for rendering)
        "text": {  # Use for rendering text
            "inline": True,
            "block": False,
            "margin": Padding(0, 0, 0, 0),
        },
        # Metadata elements which should be hidden
        "head": {"skip": True},
        "base": {"skip": True},
        "command": {"skip": True},
        "link": {"skip": True},
        "meta": {"skip": True},
        "noscript": {"skip": True, "block": False},
        "script": {"skip": True, "block": False},
        "style": {"skip": True},
        "title": {"skip": True},
        # Inline tags
        "a": {"inline": True, "block": False},
        "abbr": {"inline": True, "block": False},
        "acronym": {"inline": True, "block": False},
        "audio": {"inline": True, "block": False},
        "b": {"inline": True, "block": False},
        "bdi": {"inline": True, "block": False},
        "bdo": {"inline": True, "block": False},
        "big": {"inline": True, "block": False},
        "br": {"inline": True, "block": False},
        "button": {"inline": True, "block": False},
        "canvas": {"inline": True, "block": False},
        "cite": {"inline": True, "block": False},
        "code": {"inline": True, "block": False},
        "data": {"inline": True, "block": False},
        "datalist": {"inline": True, "block": False},
        "del": {"inline": True, "block": False},
        "dfn": {"inline": True, "block": False},
        "em": {"inline": True, "block": False},
        "embed": {"inline": True, "block": False},
        "i": {"inline": True, "block": False},
        "iframe": {"inline": True, "block": False},
        "img": {"inline": True, "block": False},
        "input": {"inline": True, "block": False},
        "ins": {"inline": True, "block": False},
        "kbd": {"inline": True, "block": False},
        "label": {"inline": True, "block": False},
        "map": {"inline": True, "block": False},
        "mark": {"inline": True, "block": False},
        "meter": {"inline": True, "block": False},
        "object": {"inline": True, "block": False},
        "output": {"inline": True, "block": False},
        "picture": {"inline": True, "block": False},
        "progress": {"inline": True, "block": False},
        "q": {"inline": True, "block": False},
        "ruby": {"inline": True, "block": False},
        "s": {"inline": True, "block": False},
        "samp": {"inline": True, "block": False},
        "select": {"inline": True, "block": False},
        "slot": {"inline": True, "block": False},
        "small": {"inline": True, "block": False},
        "span": {"inline": True, "block": False},
        "strong": {"inline": True, "block": False},
        "sub": {"inline": True, "block": False},
        "sup": {"inline": True, "block": False},
        "svg": {"inline": True, "block": False},
        "template": {"inline": True, "block": False},
        "textarea": {"inline": True, "block": False},
        "time": {"inline": True, "block": False},
        "u": {"inline": True, "block": False},
        "tt": {"inline": True, "block": False},
        "var": {"inline": True, "block": False},
        "video": {"inline": True, "block": False},
        "wbr": {"inline": True, "block": False},
        # Custom inline tags
        "math": {
            "inline": True,
            "block": False,
            "align": FormattedTextAlign.CENTER,
            "margin": Padding(1, 0, 1, 0),
        },
        # Alignment
        "center": {"align": FormattedTextAlign.CENTER},
        # Table elements
        "table": {"padding": Padding(0, 1, 0, 1)},
        "td": {"block": True, "inline": True, "align": FormattedTextAlign.LEFT},
        "th": {
            "block": True,
            "inline": True,
            "style": "bold",
            "align": FormattedTextAlign.LEFT,
        },
        # Forms & related elements
        "option": {"skip": True},
        # Custom default styles
        "blockquote": {"margin": Padding(1, 0, 1, 0)},
        "hr": {"margin": Padding(1, 0, 1, 0)},
        "p": {"margin": Padding(1, 0, 1, 0)},
        "pre": {"margin": Padding(1, 0, 1, 0)},
        "details": {"margin": Padding(1, 0, 1, 0)},
        "summary": {"margin": Padding(0, 0, 1, 0)},
        "caption": {"align": FormattedTextAlign.CENTER},
        # Lists
        "ol": {"list-style": "decimal", "block": True},
        "ul": {"list-style": "disc", "block": True},
    },
)

_ELEMENT_INSETS = {
    "blockquote": 2,
    "details": 3,
    "summary": 3,
}


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


def get_integer(value: "str") -> "str":
    """Extract the first integer from a string."""
    for word in value.split(" "):
        for c in word.partition(".")[0].split():
            if c.isdigit():
                return c.lstrip("0")
    return ""


def get_color(value: "str") -> "str":
    """Extract a hex color from a string."""
    color = ""
    if match := re.search(_COLOR_RE, value):
        hexes = match.group(1)
        if len(hexes) == 3:
            hexes = "".join(2 * s for s in hexes)
        color = f"#{hexes}"
    elif value.startswith("rgb"):
        # Ignore alpha for now - TODO
        color = "#" + "".join(
            (hex(int(x))[2:] for x in value.strip("rgba()").split(",")[:3])
        )
    else:
        from euporie.core.reference import NAMED_COLORS

        color = NAMED_COLORS.get(value, "")
    return color


class PageElement:
    """Represents an HTML element."""

    def __init__(
        self,
        name: "str",
        parent: "Optional[PageElement]",
        attrs: "list[tuple[str, Optional[str]]]",
        text: "str" = "",
    ) -> "None":
        """Create a new page element."""
        self.name = name
        self.parent = parent
        self.text = text
        self.attrs: "dict[str, Any]" = {k: v for k, v in attrs if v is not None}
        self.contents: "list[PageElement]" = []
        self.closed = False
        # self.attrs["class"] = self.attrs.get("class", "").split()

    def find_all(self, tag: "str", recursive: "bool" = False) -> "list[PageElement]":
        """Find all child elements of a given tag type."""
        return [element for element in self.contents if element.name == tag]

    @property
    def descendents(self) -> "Generator[PageElement, None, None]":
        """Yields all descendent elements."""
        for child in self.contents:
            yield child
            yield from child.descendents

    @cached_property
    def parents(self) -> "list[PageElement]":
        """Yields all descendent elements."""
        parents = []
        parent = self.parent
        while parent is not None:
            parents.append(parent)
            parent = parent.parent
        return parents[::-1]

    def _outer_html(self, d: "int" = 0, attrs: "bool" = True) -> "str":
        dd = " " * d
        s = ""
        if self.name != "text":
            s += f"{dd}<{self.name}"
            if attrs:
                for key, value in self.attrs.items():
                    if key == "class":
                        value = " ".join(value)
                    if value:
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

    def __repr__(self, d: "int" = 0) -> "str":
        return self._outer_html(attrs=False)


class CustomHTMLParser(HTMLParser):
    """An HTML parser."""

    def __init__(self) -> "None":
        """Create a new parser instance."""
        super().__init__()
        self.curr = self.soup = PageElement(name="html", parent=None, attrs=[])

    def parse(self, markup: "str") -> "PageElement":
        """Parse HTML markup."""
        self.curr = self.soup = PageElement(name="html", parent=None, attrs=[])
        self.feed(markup)
        return self.soup

    def handle_starttag(
        self, tag: "str", attrs: "list[tuple[str, Optional[str]]]"
    ) -> "None":
        """Open a new element."""
        self.autoclose()
        element = PageElement(name=tag, parent=self.curr, attrs=attrs)
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
            PageElement(name="text", parent=self.curr, text=data, attrs=[])
        )

    def handle_endtag(self, tag: "str") -> "None":
        """Handle end tags: close the currently opened element."""
        if tag != self.curr.name:
            self.autoclose()
        self.curr.closed = True
        if self.curr.parent:
            self.curr = self.curr.parent


parser = CustomHTMLParser()


def css_dimension(value: "str", vertical: "bool" = False) -> "Optional[int|float]":
    """Convert CSS dimensions to terminal cell sizes."""
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
    if vertical:
        if units == "px":
            cols, aspect = pixels_to_cell_size(px=number, py=number)
            # Add 0.5 to round to nearest whole number
            return int((cols * aspect) + 0.5)
        elif units == "%":
            return number / 100
        else:
            return int(number)

    else:
        if units == "px":
            cols, _ = pixels_to_cell_size(px=number, py=1)
            return cols
        elif units == "%":
            return number / 100
        else:
            # Round down for vertical space
            return int(number) * 2


def parse_css_content(content: "str") -> "dict[str, Any]":
    """Convert CSS declarations into the internals style representation."""
    output: "dict[str, Any]" = {}

    for declaration in content.split(";"):
        name, _, value = declaration.partition(":")
        name = name.strip()
        # Ignore "!important" tags for now - TODO
        value = value.replace("!important", "").strip()

        if name == "color":
            if color := get_color(value):
                output.setdefault("style_fg", "")
                output["style_fg"] = color

        elif name in ("background", "background-color"):
            if color := get_color(value):
                output.setdefault("style_bg", "")
                output["style_bg"] = color

        elif name == "font-weight":
            if value in ("bold", "bolder") or (
                (digits := get_integer(value)) and int(digits) > 700
            ):
                output.setdefault("style_attrs", [])
                output["style_attrs"].append("bold")

        elif name == "text-decoration":
            output.setdefault("style_attrs", [])
            if value == "underline":
                output["style_attrs"].append("underline")
            if value == "none":
                output["style_attrs"].append("nounderline")

        elif name == "text-align":
            value = value.lower()
            if value == "left":
                output["align"] = FormattedTextAlign.LEFT
            elif value == "center":
                output["align"] = FormattedTextAlign.CENTER
            elif value == "right":
                output["align"] = FormattedTextAlign.RIGHT

        elif name == "border-width":
            if digits := get_integer(value):
                output["border"] = _BORDER_WIDTHS.get(
                    digits,
                    BorderLineStyle(Thick, Thick, Thick, Thick),
                )

        elif name == "visibility":
            output["hidden"] = value == "hidden"

        elif name == "display":
            if value == "flex":
                output["flex"] = True
            if value == "block":
                output["block"] = True
            if value == "inline-block":
                output["block"] = True
                output["inline"] = True
            elif value == "none":
                output["skip"] = True

        elif name == "flex-direction":
            output["flex-direction"] = value

        elif name == "position":
            # if value == "absolute":
            # output["float"] = True
            if value == "fixed":
                output["float"] = True

        elif name in ("width", "max-width"):
            # Get width in terminal colmuns
            if width := css_dimension(value, vertical=False):
                output["width"] = width

        elif name == "height":
            # Get height in terminal rows
            if height := css_dimension(value, vertical=True):
                output["height"] = height

        elif name in ("top", "right", "bottom", "left"):
            current = output.get("position", Position(None, None, None, None))._asdict()
            if (
                dim := css_dimension(value, vertical=name in ("top", "bottom"))
            ) is not None:
                output["position"] = Position(**{**current, **{name: dim}})

        elif name == "padding":
            top = right = bottom = left = 0
            values = value.split()
            if len(values) == 1:
                top = bottom = css_dimension(values[0], vertical=True) or 0
                right = left = css_dimension(values[0], vertical=False) or 0
            if len(values) == 2:
                top = bottom = css_dimension(values[0], vertical=True) or 0
                left = right = css_dimension(values[1], vertical=False) or 0
            elif len(values) == 3:
                top = css_dimension(values[0], vertical=True) or 0
                right = left = css_dimension(values[1], vertical=False) or 0
                bottom = css_dimension(values[2], vertical=True) or 0
            elif len(values) == 4:
                top = css_dimension(values[0], vertical=True) or 0
                right = css_dimension(values[1], vertical=False) or 0
                bottom = css_dimension(values[2], vertical=True) or 0
                left = css_dimension(values[3], vertical=False) or 0
            output["padding"] = Padding(top, right, bottom, left)

        elif name.startswith("padding-"):
            prop = name[8:]
            if prop in ("top", "right", "bottom", "left"):
                current = output.get("padding", Padding(0, 0, 0, 0))._asdict()
                if dim := css_dimension(value, vertical=name in ("top", "bottom")):
                    output["padding"] = Padding(**{**current, **{prop: dim}})

        elif name == "margin":
            top = right = bottom = left = 0
            values = value.split()
            if len(values) == 1:
                top = bottom = right = left = values[0]
            elif len(values) == 2:
                top = bottom = values[0]
                left = right = values[1]
            elif len(values) == 3:
                top = values[0]
                right = left = values[1]
                bottom = values[2]
            elif len(values) == 4:
                top, right, bottom, left = values

            # Align to center if margin-x is auto
            if left == "auto" and right == "auto":
                output["align"] = FormattedTextAlign.CENTER
            elif left == "auto":
                output["align"] = FormattedTextAlign.RIGHT
            elif right == "auto":
                output["align"] = FormattedTextAlign.LEFT

            output["margin"] = Padding(
                css_dimension(top, vertical=True) or 0,
                css_dimension(right, vertical=False) or 0,
                css_dimension(bottom, vertical=True) or 0,
                css_dimension(left, vertical=False) or 0,
            )

        elif name.startswith("margin-"):
            prop = name[7:]
            if prop in ("top", "right", "bottom", "left"):
                current = output.get("padding", Padding(0, 0, 0, 0))._asdict()
                if dim := css_dimension(value, vertical=prop in ("top", "bottom")):
                    output["margin"] = Padding(**{**current, **{prop: dim}})

        elif name == "overflow" and value == "hidden":
            output["truncate"] = Direction(x=True, y=True)
        elif name == "overflow-x" and value == "hidden":
            current = output.get("truncate", Direction(x=False, y=False))._asdict()
            output["truncate"] = Direction(**{**current, **{"x": True}})
        elif name == "overflow-y" and value == "hidden":
            current = output.get("truncate", Direction(x=False, y=False))._asdict()
            output["truncate"] = Direction(**{**current, **{"y": True}})

        elif name == "opacity" and value == "0":
            output["invisible"] = True

        elif name == "list-style-type" or name == "list-style":
            if "none" in value.split():
                value = ""
            output["list-style"] = value

    return output


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    def _render_list(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render lists, adding item numbers to child <li> elements."""
        theme = self.element_theme(element, parent_theme)
        items = [li for li in element.contents if li.name == "li"]
        for i, item in enumerate(items, start=1):
            item.attrs["data-list-index"] = i
            item.attrs["data-list-length"] = len(items)
        # Render contents as normal
        return self.render_contents(
            element.contents,
            theme,
            available_width,
            available_height,
            left,
            preformatted,
        )

    render_ul = _render_list
    render_ol = _render_list

    def __init__(
        self,
        markup: "str",
        base: "Optional[Union[UPath, str]]" = None,
        width: "Optional[int]" = None,
        height: "Optional[int]" = None,
        strip_trailing_lines: "bool" = True,
        pad: "bool" = True,
    ) -> None:
        """Initialize the markdown formatter.

        Args:
            markup: The markdown text to render
            base: The base url for the HTML document
            width: The width in characters available for rendering. If :py:const:`None`
                the terminal width will be used
            height: The width in characters available for rendering. If :py:const:`None`
                the terminal height will be used
            strip_trailing_lines: If :py:const:`True`, empty lines at the end of the
                rendered output will be removed
            pad: When :py:const:`True`, the output is padded to fill the width

        """
        self.markup = markup
        self.base = base
        self.strip_trailing_lines = strip_trailing_lines
        self.pad = pad
        self.width: "Optional[int]" = None
        self.height: "Optional[int]" = None

        self.css: "dict[str, dict[str, Any]]" = {
            ".dataframe": {
                "border": BorderLineStyle(Invisible, Invisible, Invisible, Invisible),
                "border_collapse": True,
                "style_classes": ["dataframe"],
            },
            ".block": {"block": True},
        }

        self.element_theme_cache: "SimpleCache[Hashable, dict[str, Any]]" = (
            SimpleCache()
        )

        # Parse the markup
        self.soup = parser.parse(markup.strip())

        # Parse the styles
        self.css.update(self.parse_styles(self.soup))

        # Render the markup
        self.render(width, height)

        if strip_trailing_lines:
            self.formatted_text = strip(
                self.formatted_text,
                left=False,
                char="\n",
            )

    def render(self, width: "int", height: "int") -> "StyleAndTextTuples":
        """Render the current markup at a given size."""
        if not width or not height:
            size = get_app_session().output.get_size()
        self.width = width or size.columns
        self.height = height or size.rows

        self.formatted_text = self.render_element(
            self.soup,
            parent_theme={},
            available_width=self.width,
            available_height=self.height,
        )

    def parse_styles(self, soup: "PageElement") -> "dict[str, dict[str, str]]":
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
                if css_bytes := load_url(href, self.base):
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

    def element_theme(
        self, element: "PageElement", parent_theme: "dict[str, Any]"
    ) -> "dict":
        """Get an element's theme from the cache, or calculate it."""
        return self.element_theme_cache.get(
            # TODO - check this key is unique enough
            (
                element.name,
                element.attrs.get("id"),
                tuple(element.attrs.get("class", [])),
                element.attrs.get("style"),
                tuple(parent_theme.get("style_classes", [])),
            ),
            partial(self.calc_element_theme, element, parent_theme),
        )

    def calc_element_theme(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
    ) -> "dict[str, Any]":
        """Compute the theme of an element."""
        # Add extra attributes
        extras: "dict[str, Any]" = {}
        styles: "dict[str, Any]" = {}

        # -> border
        if border_attr := element.attrs.get("border"):
            extras["border"] = _BORDER_WIDTHS.get(
                border_attr,
                BorderLineStyle(Thick, Thick, Thick, Thick),
            )
        # -> bgcolor
        if bg := element.attrs.get("bgcolor"):
            color = get_color(bg)
            if color:
                extras["style_bg"] = color
        # -> width
        if (value := element.attrs.get("width")) is not None:
            extras["width"] = css_dimension(value)
        # -> cellpadding
        # TODO

        # Check for language highlighting classes
        for class_name in element.attrs.get("class", "").split():
            if class_name.startswith("language-"):
                extras["language"] = class_name[9:]
                break
            elif class_name.startswith("highlight-"):
                extras["language"] = class_name[10:]
                break

        # for class_name in element.attrs.get("class", []):
        # if (rule := self.css.get(f"{element.name}.{class_name}")) is not None:
        # class_rules.append(rule)
        # if (rule := self.css.get(f".{class_name}")) is not None:
        # class_rules.append(rule)
        # self.css.get(element.name, {}),

        @lru_cache
        def _match_selector(selector: "str", element: "PageElement") -> "bool":
            matched = True

            while selector and matched:

                # Universal selector
                if selector == "*":
                    break

                # Type selectors
                if selector[0] not in ".#[":
                    if selector.startswith(name := element.name):
                        selector = selector[len(name) :]
                    else:
                        matched = False

                # ID selectors
                if selector.startswith("#"):
                    if "id" in element.attrs:
                        id_ = element.attrs["id"]
                        if selector[1:].startswith(id_):
                            selector = selector[1 + len(id_) :]
                        else:
                            matched = False
                    else:
                        matched = False

                # Class selectors
                if selector and selector.startswith("."):
                    for class_name in sorted(
                        element.attrs.get("class", "").split(), key=len, reverse=True
                    ):
                        # IF CLASS NAME SUBSTRING
                        if selector[1:].startswith(class_name):
                            selector = selector = selector[1 + len(class_name) :]
                            break
                    else:
                        matched = False

                # Attribute selectors
                if selector.startswith("["):
                    test = selector[1 : selector.index("]")]
                    if (op := "*=") in test:
                        attr, _, value = test.partition(op)
                        value = value.strip("'\"")
                        matched = value in element.attrs.get(attr, "")
                    elif (op := "$=") in test:
                        attr, _, value = test.partition(op)
                        value = value.strip("'\"")
                        matched = element.attrs.get(attr, "").endswith(value)
                    elif (op := "^=") in test:
                        attr, _, value = test.partition(op)
                        value = value.strip("'\"")
                        matched = element.attrs.get(attr, "").startswith(value)
                    elif (op := "|=") in test:
                        attr, _, value = test.partition(op)
                        value = value.strip("'\"")
                        matched = element.attrs.get(attr) in (value, f"{value}-")
                    elif (op := "~=") in test:
                        attr, _, value = test.partition(op)
                        value = value.strip("'\"")
                        matched = value in element.attrs.get(attr, "").split()
                    elif (op := "=") in test:
                        attr, _, value = test.partition(op)
                        value = value.strip("'\"")
                        matched = element.attrs.get(attr) == value
                    else:
                        matched = test in element.attrs
                    selector = selector[2 + len(test) :]

                if not matched:
                    break

            return matched

        css_rules = {}
        for selectors, rule in reversed(self.css.items()):
            split_selectors = selectors.split()
            parent_selectors = split_selectors[:-1]
            element_selector = split_selectors[-1]
            for selector in parent_selectors:
                for parent in element.parents:
                    if _match_selector(selector, parent):
                        break
                else:
                    break
            else:
                if _match_selector(element_selector, element):
                    css_rules[selectors] = rule

        # Chain themes from various levels
        theme = ChainMap(
            # Computed combined styles
            styles,
            # Tag styles
            parse_css_content(element.attrs.get("style", "")),
            # Class rules
            *css_rules.values(),
            # ID rule
            # self.css.get(f"#{element_id}", {}),
            # Tag rules
            # self.css.get(element.name, {}),
            # Tag attributes
            extras,
            # Element base style
            _ELEMENT_BASE_THEMES.get(element.name, _ELEMENT_BASE_THEMES["default"]),
            # Parent theme
            dict(parent_theme),
            # Add an element class
            {"style_classes": [element.name]},
            # Default element style
            _ELEMENT_BASE_THEMES["default"],
        )

        # Concatenate styles
        styles["style_classes"] = sum(
            (mapping.get("style_classes", []) for mapping in theme.maps), start=[]
        )
        styles["style_attrs"] = sum(
            (mapping.get("style_attrs", []) for mapping in theme.maps), start=[]
        )
        style_classes_str = "class:" + ",".join(styles["style_classes"])
        style_attrs_str = " ".join(styles["style_attrs"])
        styles["style"] = f"{style_classes_str} {style_attrs_str}"
        if fg := theme.get("style_fg"):
            styles["style"] += f" fg:{fg}"
        if bg := theme.get("style_bg"):
            styles["style"] += f" bg:{bg}"

        # Flatten chained dict
        return theme
        return dict(theme)

    def render_contents(
        self,
        contents: "list[PageElement]",
        parent_theme: "dict[str, Any]",
        available_width: "int" = 80,
        available_height: "int" = 999999999,
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements.

        Args:
            contents: The list of parsed elements to render
            parent_theme: The theme of the element's parent element
            available_width: The width available for rendering the elements
            available_height: The height available for rendering the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: If True, whitespace will not be stripped from the element's
                text

        Returns:
            Formatted text

        """
        ft: "StyleAndTextTuples" = []

        def _draw_y_margin(
            ft: "StyleAndTextTuples", element: "PageElement", index: "int"
        ) -> "StyleAndTextTuples":
            """Draw the vertical margins for an element."""
            theme = self.element_theme(element, parent_theme)
            margin = theme["margin"][index]
            # Find how much of this margin has already been drawn
            i = -1
            for frag in reversed(ft):
                for c in reversed(frag[1]):
                    if c == "\n":
                        i += 1
                        continue
                    break
                else:
                    continue
                break

            # Draw remaining margin lines
            if n_new_lines := max(0, margin - i):
                return [
                    (
                        parent_theme["style"] if parent_theme else "",
                        "\n" * n_new_lines,
                    )
                ]
            return []

        outputs = []
        floats = {}

        for i, element in enumerate(contents):

            # Convert tags with "math" class to <math> tag
            if "math" in element.attrs.get("class", []):
                element.name = "math"

            theme = self.element_theme(element, parent_theme)

            # Do not render tags with "skip" set in theme
            if theme["skip"]:
                continue

            # Is the current element a block element?
            block = theme["block"]

            # Set preformatted flag for <pre> tags
            _preformatted = preformatted
            if element.name == "pre":
                _preformatted = True

            # Render block element margins. We want to ensure block elements always
            # start on a new line, and that margins collapse.
            # Do not draw a margin if this is the first element of the render list.
            if block and ft:
                ft.extend(_draw_y_margin(ft, element, 0))

            # If there is a special method for rendering the block, use it; otherwise
            # use the generic `render_element` function
            render_func = getattr(self, f"render_{element.name}", self.render_element)

            # Recalculate the left offset if we have rendered output
            if ft:
                left = last_line_length(ft)

            # Render the element
            rendering = render_func(
                element,
                parent_theme=parent_theme,
                available_width=available_width,
                available_height=available_height,
                left=left,
                preformatted=_preformatted,
            )

            if block:
                # Draw block element bottom margin, ensuring block elements end on a new
                # line, and that margins collapse
                if parent_theme["block"] and any(
                    element.name != "text"
                    or (element.name == "text" and element.text.strip())
                    for element in contents[i + 1 :]
                ):
                    rendering.extend(_draw_y_margin(rendering, element, 2))

            if theme["float"]:
                floats[(theme["zindex"], theme["position"])] = rendering
            else:
                ft.extend(rendering)

        # Draw flex elements
        # if parent_theme.get("flex") and parent_theme.get("flex-direction") == "column":
        # table = Table(border=Invisible, border_collapse=True)
        # row = table.new_row()
        # for output in outputs:
        # row.new_cell(output)
        # ft = table.render(available_width)
        #
        # else:
        ft = sum(outputs, start=ft)

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
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a block element.

        Args:
            element: The list of parsed elements to render
            parent_theme: The theme of the element's parent element
            available_width: The width available for rendering the elements
            available_height: The height available for rendering the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: When True, whitespace in the the element's text is not
                collapsed

        Returns:
            Formatted text

        """
        theme = self.element_theme(element, parent_theme)

        inner_width = available_width - _ELEMENT_INSETS.get(element.name, 0)
        inner_height = available_height

        if (theme_height := theme.get("height")) is not None:
            if isinstance(theme_height, float) and 0 < theme_height <= 1:
                inner_height = int(inner_height * theme_height + 0.5)
            else:
                inner_height = min(inner_height, theme_height)

        if (theme_width := theme.get("width")) is not None:
            if isinstance(theme_width, float) and 0 < theme_width <= 1:
                inner_width = int(inner_width * theme_width + 0.5)
            else:
                inner_width = min(inner_width, theme_width)

        if margin := theme.get("margin"):
            for margin_size in (margin.left, margin.right):
                if isinstance(margin_size, float) and 0 < margin_size <= 1:
                    inner_width = int(inner_width * (1 - margin_size))
                else:
                    inner_width -= margin_size or 0

        if padding := theme.get("padding"):
            for padding_size in (padding.left, padding.right):
                if isinstance(padding_size, float) and 0 < padding_size <= 1:
                    inner_width = int(inner_width * (1 - padding_size))
                else:
                    inner_width -= padding_size or 0

        # Render the contents
        ft = self.render_contents(
            element.contents,
            parent_theme=theme,
            available_width=inner_width,
            available_height=inner_height,
            left=left,
            preformatted=preformatted,
        )

        # If an element should not overflow it's width / height, truncate it
        if trunc := theme.get("truncate"):
            if trunc.x:
                ft = truncate(ft, available_width, placeholder="")
            if trunc.y:
                new_ft = []
                for i, line in enumerate(split_lines(ft)):
                    if i <= inner_height:
                        new_ft += line
                        new_ft += [("", "\n")]
                ft = new_ft[:-1]

        # Apply tag formatting
        if format_func := getattr(self, f"format_{element.name}", None):
            ft = format_func(
                ft,
                inner_width,
                inner_height,
                left,
                element,
                theme,
            )

        # Lex the text
        if language := theme["language"]:
            ft = strip(ft, left=False, right=True, char="\n")
            ft = lex(ft, lexer_name=language)

        if theme["block"] and not preformatted:

            # Align the output
            if theme["align"] != FormattedTextAlign.LEFT:
                ft = align(
                    theme["align"], ft, width=available_width, style=theme["style"]
                )

            # Add left margin
            if margin and (margin_left := margin.left):
                if isinstance(margin_left, float) and 0 < margin.left <= 1:
                    margin_left = int(available_width * margin_left)
                ft = indent(ft, margin=" " * margin_left, style=parent_theme["style"])

            # Add left padding
            if padding and (padding_left := padding.left):
                if isinstance(padding_left, float) and 0 < padding.left <= 1:
                    padding_left = int(available_width * padding_left)
                ft = indent(ft, margin=" " * padding_left, style=theme["style"])

            # Fill space around block elements so they fill the width
            if self.pad and not theme["inline"]:

                # Remove one trailing newline if there is one
                for i in range(len(ft) - 1, -1, -1):
                    frag = ft[i]
                    if not frag[1]:
                        continue
                    if frag[1] == "\n":
                        del ft[i]
                    elif frag[1].endswith("\n"):
                        ft[i] = (frag[0], frag[1][:-1])
                    break

                # Format the remainder of each line
                filled_output = []
                for line in split_lines(ft):
                    filled_output.extend(line)
                    if remaining := inner_width - fragment_list_width(line):
                        filled_output.append((theme["style"], (" " * remaining)))
                        # filled_output.append((theme["style"], ("·" * remaining)))
                    if filled_output and not filled_output[-1][1].endswith("\n"):
                        filled_output.append((theme["style"], "\n"))
                ft = filled_output

        if theme.get("invisible"):
            new_ft = []
            for line in split_lines(ft):
                new_ft.append((parent_theme["style"], " " * fragment_list_width(line)))
                new_ft.append(("", "\n"))
            if new_ft:
                new_ft.pop()
            ft = new_ft

        return ft

    def render_text(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a text element.

        Args:
            element: The page element to render
            parent_theme: The theme of the element's parent element
            available_width: The width available for rendering the element
            available_height: The height available for rendering the element
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: When True, whitespace in the the element's text is not
                collapsed

        Returns:
            Formatted text

        """
        ft: "StyleAndTextTuples" = []
        text = element.text
        style = parent_theme["style"]

        # Ensure hidden text is blank and not underlined
        if parent_theme.get("hidden"):
            text = " " * len(text)
            style = f"{style} nounderline"

        # Strip whitespace
        if not preformatted:
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

        if text:
            ft = [(style, text)]

        # Wrap non-pre-formatted text
        if not preformatted:
            ft = wrap(ft, available_width, left=left, style=style)

        return ft

    def render_li(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list item."""
        # Get the element's theme
        theme = self.element_theme(element, parent_theme)
        # Get margin
        list_style = theme.get("list-style", "none")
        margin = {
            "none": "",
            "disc": "•",
            "circle": "○",
            "square": "■",
            "disclosure-open": "▼",
            "disclosure-closed": "▶",
        }.get(list_style, list_style)
        # Pad decimal bullets
        if list_style == "decimal":
            decimal = str(element.attrs["data-list-index"]).rjust(
                len(str(element.attrs["data-list-length"])), " "
            )
            margin = f"{decimal}."
        # Add space around bullet
        margin = f" {margin} "
        margin_len = len(margin)
        # Render the list item
        ft = self.render_contents(
            element.contents,
            parent_theme=theme,
            # Restrict the available width by the margin width
            available_width=available_width - margin_len,
            available_height=available_height,
            left=left,  # + margin_len,
            preformatted=preformatted,
        )
        # Indent using margin
        ft = [(f"{theme['style']} class:bullet", margin), *ft]
        ft = indent(ft, margin=" " * margin_len, skip_first=True, style=theme["style"])
        return ft

    def _render_li(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list element."""
        # Get the element's theme
        theme = self.element_theme(element, parent_theme)
        # Get the bullet details
        bullet = str(element.attrs.get("data-margin", "•"))
        bullet_str = f" {bullet} "
        bullet_width = len(bullet_str)
        # Render the contents of the list item
        ft = self.render_contents(
            element.contents,
            parent_theme=theme,
            # Restrict the available width by the margin width
            available_width=available_width - bullet_width,
            available_height=available_height,
            left=left,
            preformatted=preformatted,
        )
        # Wrap the list item
        ft = wrap(
            ft,
            available_width - bullet_width,
            style=theme["style"],
            strip_trailing_ws=True,
        )
        # Add the bullet
        ft = [(f"{theme['style']} class:bullet", bullet_str), *ft]
        # Indent subsequent lines
        ft = indent(
            ft, margin=" " * bullet_width, skip_first=True, style=theme["style"]
        )
        ft = strip(ft, left=False, right=True)
        ft.append(("", "\n"))
        return ft

    def render_table(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a table element.

        Args:
            element: The list of parsed elements to render
            available_width: The width available for rendering the element
            available_height: The height available for rendering the element
            parent_theme: The theme of the parent element
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: When True, whitespace in the the element's text is not
                collapsed

        Returns:
            Formatted text

        """
        ft = []

        table_theme = self.element_theme(element, parent_theme)

        # Adjust the width
        inner_width = available_width
        if (theme_width := table_theme.get("width")) is not None:
            if isinstance(theme_width, float) and 0 < theme_width <= 1:
                inner_width = int(inner_width * theme_width + 0.5)
            else:
                inner_width = min(inner_width, theme_width)

        if margin := table_theme.get("margin"):
            for margin_size in (margin.left, margin.right):
                if isinstance(margin_size, float) and 0 < margin_size <= 1:
                    available_width = int(inner_width * (1 - margin_size))
                else:
                    available_width -= margin_size or 0

        if padding := table_theme.get("padding"):
            for padding_size in (padding.left, padding.right):
                if isinstance(padding_size, float) and 0 < padding_size <= 1:
                    inner_width = int(inner_width * (1 - padding_size))
                else:
                    inner_width -= padding_size or 0

        table = Table(
            align=table_theme["align"],
            style=table_theme["style"],
            padding=table_theme["padding"],
            border_style=table_theme["style"],
            # Use invisible borders by default
            border=table_theme["border"] or Invisible,
            border_collapse=table_theme["border_collapse"],
        )

        # Stack the elements in the shape of the table
        def render_rows(elements: "list[PageElement]") -> "None":
            for tr in elements:
                if tr.name == "tr":
                    tr_theme = self.element_theme(tr, table_theme)
                    row = table.new_row(
                        align=tr_theme["align"],
                        padding=tr_theme["padding"],
                        border=tr_theme["border"],
                        style=tr_theme["style"],
                    )
                    for td in tr.contents:
                        if td.name in ("th", "td"):
                            td_theme = self.element_theme(td, tr_theme)
                            row.new_cell(
                                text=self.render_contents(
                                    td.contents,
                                    parent_theme=td_theme,
                                    available_width=available_width,
                                    available_height=available_height,
                                    left=0,
                                    preformatted=preformatted,
                                ),
                                padding=td_theme["padding"],
                                border=td_theme["border"],
                                align=td_theme["align"],
                                colspan=try_eval(td.attrs.get("colspan", 1)),
                                rowspan=try_eval(td.attrs.get("rowspan", 1)),
                                style=td_theme["style"] + " nounderline",
                            )

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
        # Render the table
        ft_table = table.render(inner_width)

        # Render the caption
        captions = element.find_all("caption", recursive=False)
        if captions:
            table_width = max_line_width(ft_table)
            for child in captions:
                ft_caption = self.render_element(
                    child, table_theme, table_width, left, preformatted
                )
                if ft_caption:
                    ft.extend(ft_caption)

        ft.extend(ft_table)

        return ft

    def render_details(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render an expand summary / details."""
        ft: "StyleAndTextTuples" = []
        theme = self.element_theme(element, parent_theme)

        summary_element = None
        for child in element.contents:
            if child.name == "summary":
                summary_element = child
                break

        if summary_element is not None:
            ft.extend(
                self.render_element(
                    summary_element,
                    parent_theme=theme,
                    available_width=available_width,
                    available_height=available_height,
                    left=left,
                    preformatted=preformatted,
                )
            )
            ft.append(("", "\n"))

        detail_elements = [e for e in element.contents if e is not summary_element]

        ft.extend(
            self.format_details(
                self.render_contents(
                    detail_elements,
                    parent_theme=theme,
                    available_width=available_width - _ELEMENT_INSETS["details"],
                    available_height=available_height,
                    left=left,
                    preformatted=preformatted,
                ),
                available_width,
                available_height,
                left,
                element,
                theme,
            )
        )
        ft.append(("", "\n"))
        return ft

    def _render_image(
        self,
        data: "Any",
        format_: "str",
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
    ) -> "Optional[StyleAndTextTuples]":
        cols, aspect = pixels_to_cell_size(*data_pixel_size(data, format_=format_))
        # Manially set a value if we don't have one
        cols = cols or 20
        aspect = aspect or 0.5
        # Scale down the image to fit to width
        cols = min(available_width, cols)
        rows = ceil(cols * aspect)
        # Convert the image to formatted-text
        result = convert(
            data,
            format_,
            "formatted_text",
            cols=cols,
            rows=rows,
        )
        # Remove trailing new-lines
        result = strip(result, char="\n", left=False)
        # Optionally add a border
        if try_eval(element.attrs.get("border", "")):
            result = add_border(
                result,
                border=Rounded.grid,
                style="class:md.img.border",
            )
        # Indent for line continuation as images are inline
        # if left:
        result = indent(
            result, " " * left, skip_first=True, style=parent_theme["style"]
        )
        return result

    def render_img(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
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
                element,
                parent_theme,
                available_width,
                available_height,
                left,
            )
            return ft
        # Otherwise, display the image title
        else:
            return self.render_element(
                element,
                parent_theme,
                available_width,
                available_height,
                left,
                preformatted,
            )

    def render_svg(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Display images rendered as ANSI art."""
        # Ensure xml namespace is set
        element.attrs.setdefault("xmlns", "http://www.w3.org/2000/svg")
        element.attrs.setdefault("xmlns:xlink", "http://www.w3.org/1999/xlink")
        data = element._outer_html()
        return self._render_image(
            data, "svg", element, parent_theme, available_width, available_height, left
        )

    def render_math(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        available_width: "int",
        available_height: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
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
            preformatted=True,
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
        element: "PageElement",
        theme: "dict",
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
            ft = apply_style(ft, theme["style"])
        return ft

    @staticmethod
    def format_div(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a horizontal rule."""
        # ft = wrap(ft, available_width, style=theme["style"])
        return ft

    @staticmethod
    def format_hr(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a horizontal rule."""
        ft = [(theme["style"], "─" * available_width)]
        return ft

    @staticmethod
    def format_h1(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a top-level heading wrapped and centered with a full width double border."""
        ft = wrap(ft, available_width - 4, style=theme["style"])
        ft = align(
            FormattedTextAlign.CENTER,
            ft,
            width=available_width - 4,
            style=theme["style"],
        )
        ft = add_border(
            ft,
            width=available_width,
            border=Double.grid,
            style=theme["style"],
        )
        return ft

    @staticmethod
    def format_h2(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a 2nd-level headding wrapped and centered with a double border."""
        ft = wrap(ft, width=available_width - 4, style=theme["style"])
        ft = align(FormattedTextAlign.CENTER, ft)
        ft = add_border(
            ft,
            border=Thin.grid,
            style=theme["style"],
        )
        ft = align(
            FormattedTextAlign.CENTER, ft, width=available_width, style=theme["style"]
        )
        return ft

    @staticmethod
    def format_h(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format headings wrapped and centered."""
        ft = wrap(ft, available_width, style=theme["style"])
        ft = align(FormattedTextAlign.CENTER, ft, width=available_width)
        return ft

    @staticmethod
    def format_p(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format paragraphs wrapped."""
        ft = wrap(ft, available_width, style=theme["style"])
        return ft

    @staticmethod
    def format_br(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format line breaks."""
        return [("", "\n")]

    @staticmethod
    def format_blockquote(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format blockquotes with a solid left margin."""
        ft = wrap(strip(ft, char="\n"), width=available_width, style=theme["style"])
        ft = indent(ft, margin="▌ ", style=f"{theme['style']} class:margin")
        return ft

    @staticmethod
    def format_pre(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a pre-formatted block with a border if it contains code."""
        if element.contents and element.contents[0].name == "code":
            ft = align(FormattedTextAlign.LEFT, ft, available_width - 4)
            ft = add_border(ft, available_width, border=Thin.grid)
        return ft

    @staticmethod
    def format_a(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format hyperlinks and adds link escape sequences."""
        href = element.attrs.get("href")
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
    def format_summary(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format summaries with an arrow."""
        return [
            ("class:html.summary.arrow", " ⮟ "),
            *indent(
                wrap(ft, width=available_width, style=theme["style"]),
                margin="   ",
                skip_first=True,
                style=theme["style"],
            ),
        ]

    @staticmethod
    def format_details(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format details indented."""
        ft = strip(ft, char="\n")
        ft = indent(ft, margin="   ")
        return ft

    @staticmethod
    def format_q(
        ft: "StyleAndTextTuples",
        available_width: "int",
        available_height: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format an inline quote."""
        return [("", '"'), *ft, ("", '"')]


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
                    HTML(path.open().read(), base=path, pad=True),
                    style=Style(HTML_STYLE),
                )
