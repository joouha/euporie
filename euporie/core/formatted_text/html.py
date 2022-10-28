"""Contains a HTML to formatted text parser."""

from __future__ import annotations

import logging
import re
from ast import literal_eval
from collections import ChainMap, defaultdict
from functools import partial
from html.parser import HTMLParser
from math import ceil
from random import randint
from typing import TYPE_CHECKING

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
from euporie.core.convert.base import FORMAT_EXTENSIONS, convert
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
    strip,
    wrap,
)
from euporie.core.terminal import tmuxify
from euporie.core.url import load_url

if TYPE_CHECKING:
    from typing import Any, Generator, Hashable, Optional, Union

log = logging.getLogger(__name__)

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

# The default theme to apply to various elements
_ELEMENT_BASE_THEMES: "defaultdict[str, dict[str, Any]]" = defaultdict(
    dict,
    {
        # Default theme for a tag
        "default": {
            "padding": None,
            "margin": Padding(0, 0, 0, 0),
            "align": FormattedTextAlign.LEFT,
            "border": None,
            "border_collapse": True,
            "language": None,
            "style": "",
            "invisilble": False,
            "skip": False,
            "block": True,
            "inline": False,
            # Styles
            "style_classes": [],
        },
        # "Special" tags (not real HTML tags, just used for rendering)
        "text": {"inline": True, "block": False},  # Use for rendering text
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
        "math": {
            "inline": True,
            "block": False,
            "align": FormattedTextAlign.CENTER,
            "margin": Padding(1, 0, 1, 0),
        },
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
        # Table elements
        "table": {"padding": Padding(0, 1, 0, 1)},
        "td": {"block": False},
        "th": {"block": False, "style": "bold"},
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

        self.attrs["class"] = self.attrs.get("class", "").split()

    def find_all(self, tag: "str", recursive: "bool" = False) -> "list[PageElement]":
        """Find all child elements of a given tag type."""
        return [element for element in self.contents if element.name == tag]

    @property
    def descendents(self) -> "Generator[PageElement, None, None]":
        """Yields all descendent elements."""
        for child in self.contents:
            yield child
            yield from child.descendents

    def __repr__(self, d: "int" = 0) -> "str":
        dd = " " * d
        s = ""
        if self.name:
            s += f"{dd}<{self.name}>"
            if self.contents:
                for child in self.contents:
                    s += f"\n{dd} {child.__repr__(d+1)}"
                s += f"\n{dd}{dd}"
            s += f"</{self.name}>"
        else:
            text = self.text.__repr__()
            s += f"{dd}{text}"
        return s


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


def parse_css_content(content: "str") -> "dict[str, Any]":
    """Convert CSS declarations into the internals style representation."""
    output: "dict[str, Any]" = {}

    for declaration in content.split(";"):
        name, _, value = declaration.partition(":")
        name, value = name.strip(), value.strip()

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
            if value == "underline":
                output.setdefault("style_attrs", [])
                output["style_attrs"].append("underline")

        elif name == "text-align":
            value = value.upper()
            if "LEFT" in value:
                output["align"] = FormattedTextAlign.LEFT
            if "CENTER" in value:
                output["align"] = FormattedTextAlign.CENTER
            if "RIGHT" in value:
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
            output["skip"] = value == "none"
            if value == "block":
                output["block"] = True

    return output


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    def __init__(
        self,
        markup: "str",
        base: "Optional[Union[UPath, str]]" = None,
        width: "Optional[int]" = None,
        strip_trailing_lines: "bool" = True,
        pad: "bool" = True,
    ) -> None:
        """Initialize the markdown formatter.

        Args:
            markup: The markdown text to render
            base: The base url for the HTML document
            width: The width in characters available for rendering. If :py:const:`None`
                the terminal width will be used
            strip_trailing_lines: If :py:const:`True`, empty lines at the end of the
                rendered output will be removed
            pad: When :py:const:`True`, the output is padded to fill the width

        """
        self.markup = markup
        self.base = base
        self.width = width or get_app_session().output.get_size().columns
        self.strip_trailing_lines = strip_trailing_lines
        self.pad = pad

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
        self.formatted_text = self.render_element(
            self.soup,
            parent_theme={},
            width=self.width,
        )

        if strip_trailing_lines:
            self.formatted_text = strip(
                self.formatted_text,
                left=False,
                char="\n",
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
            if css_str:
                css_str = css_str.replace("\n", "").strip()
                if css_str:
                    for rule in css_str.rstrip("}").split("}"):
                        selectors, _, content = rule.partition("{")
                        # TODO - more CSS matching complex rules
                        for selector in map(str.strip, selectors.split(",")):
                            if len(selector.split()) <= 2:
                                content = content.strip().rstrip(";")
                                rule_content = parse_css_content(content)
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
            (
                element.name,
                element.attrs.get("id"),
                tuple(element.attrs.get("class", [])),
                element.attrs.get("style"),
            ),
            partial(self.calc_element_theme, element, parent_theme),
        )

    def calc_element_theme(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
    ) -> "dict[str, Any]":
        """Compute the theme of an element."""
        element_id = element.attrs.get("id")

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
        # -> cellpadding
        # TODO

        # Check for language highlighting classes
        for class_name in element.attrs.get("class", []):
            if class_name.startswith("language-"):
                extras["language"] = class_name[9:]
                break
            elif class_name.startswith("highlight-"):
                extras["language"] = class_name[10:]
                break

        # Chain themes from various levels
        theme = ChainMap(
            # Computed combined styles
            styles,
            # Tag styles
            parse_css_content(element.attrs.get("style", "")),
            # Tag rules
            self.css.get(element.name, {}),
            # Class rules
            *[
                self.css.get(f".{class_name}", {})
                or self.css.get(f"{element.name}.{class_name}", {})
                for class_name in element.attrs.get("class", [])
            ],
            # ID rule
            self.css.get(f"#{element_id}", {}),
            # Tag attributes
            extras,
            # Element base style
            _ELEMENT_BASE_THEMES[element.name],
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

        return dict(theme)

    def render_contents(
        self,
        contents: "list[PageElement]",
        parent_theme: "dict[str, Any]",
        width: "int" = 80,
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements.

        Args:
            contents: The list of parsed elements to render
            parent_theme: The theme of the element's parent element
            width: The width at which to render the elements
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
            if block and parent_theme["block"] and ft:
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
                width=width,
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

            ft.extend(rendering)

        return ft

    def render_element(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a block element.

        Args:
            element: The list of parsed elements to render
            parent_theme: The theme of the element's parent element
            width: The width at which to render the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: When True, whitespace in the the element's text is not
                collapsed

        Returns:
            Formatted text

        """
        theme = self.element_theme(element, parent_theme)
        inner_width = width - _ELEMENT_INSETS.get(element.name, 0)

        # Render the contents
        ft = self.render_contents(
            element.contents,
            parent_theme=theme,
            width=inner_width,
            left=left,
            preformatted=preformatted,
        )

        # Apply tag formatting
        if format_func := getattr(self, f"format_{element.name}", None):
            ft = format_func(
                ft,
                inner_width,
                left,
                element,
                theme,
            )

        # Lex the text
        if language := theme["language"]:
            ft = strip(ft, left=False, right=True, char="\n")
            ft = lex(ft, lexer_name=language)

        if theme["block"]:

            # Align the output
            if theme["align"] != FormattedTextAlign.LEFT:
                ft = align(theme["align"], ft, width=width, style=theme["style"])

            # Fill space around block elements so they fill the width
            if self.pad:

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
                    if remaining := width - fragment_list_width(line):
                        filled_output.append((theme["style"], (" " * remaining)))
                        # filled_output.append((theme["style"], ("·" * remaining)))
                    if filled_output and not filled_output[-1][1].endswith("\n"):
                        filled_output.append((theme["style"], "\n"))
                ft = filled_output

        return ft

    def render_text(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a text element.

        Args:
            element: The page element to render
            parent_theme: The theme of the element's parent element
            width: The width at which to render the elements
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
            ft = wrap(ft, width, left=left, style=style)

        return ft

    def render_ol(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render order lists, adding item numbers to child <li> elements."""
        items = [li for li in element.contents if li.name == "li"]
        margin_width = len(str(len(items)))
        for i, item in enumerate(items, start=1):
            item.attrs["data-margin"] = str(i).rjust(margin_width) + "."
            item.attrs["data-list-type"] = "ol"
        # Render as normal
        return self.render_element(element, parent_theme, width, left, preformatted)

    def render_li(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list element."""
        # Get the element's theme
        theme = self.element_theme(element, parent_theme)
        # Is this a <ol> or a <ul> list?
        list_type = element.attrs.get("data-list-type", "ul")
        # Get the bullet details
        bullet = str(element.attrs.get("data-margin", "•"))
        bullet_str = f" {bullet} "
        bullet_width = len(bullet_str)
        # Render the contents of the list item
        ft = self.render_contents(
            element.contents,
            parent_theme=theme,
            # Restrict the available width by the margin width
            width=width - bullet_width,
            left=left,
            preformatted=preformatted,
        )
        # Wrap the list item
        ft = wrap(ft, width - bullet_width, style=theme["style"])
        # Add the bullet
        ft = [(f"{theme['style']} class:{list_type}.bullet", bullet_str), *ft]
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
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a table element.

        Args:
            element: The list of parsed elements to render
            width: The width at which to render the elements
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
                            td_theme = self.element_theme(td, parent_theme)
                            row.new_cell(
                                text=self.render_contents(
                                    td.contents,
                                    parent_theme=td_theme,
                                    width=width,
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
        ft_table = table.render(width)

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
        width: "int",
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
                    width=width,
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
                    width=width - _ELEMENT_INSETS["details"],
                    left=left,
                    preformatted=preformatted,
                ),
                width,
                left,
                element,
                theme,
            )
        )
        ft.append(("", "\n"))
        return ft

    def render_img(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Display images rendered as ANSI art."""
        result: "StyleAndTextTuples" = []
        src = str(element.attrs.get("src", ""))
        # Attempt to load the image url
        if data := load_url(src, self.base):
            # Display it graphically
            _, _, suffix = src.rpartition(".")
            format_ = FORMAT_EXTENSIONS.get(suffix.lower(), "png")
            cols, aspect = pixels_to_cell_size(*data_pixel_size(data, format_=format_))
            # Manially set a value if we don't have one
            cols = cols or 20
            aspect = aspect or 0.5
            # Scale down the image to fit to width
            cols = min(width, cols)
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
            result = indent(
                result, " " * left, skip_first=True, style=parent_theme["style"]
            )
            return result
        # Otherwise, display the image title
        else:
            return self.render_element(element, parent_theme, width, left, preformatted)

    def render_math(
        self,
        element: "PageElement",
        parent_theme: "dict[str, Any]",
        width: "int",
        left: "int" = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Display LaTeX maths rendered as unicode text."""
        text = "".join(desc.text for desc in element.descendents)
        for desc in element.descendents:
            if desc.name == "text":
                desc.text = convert(text, "latex", "ansi")
        return self.render_element(
            element, parent_theme, width, left, preformatted=True
        )

    ###

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Formatted text magic method."""
        return self.formatted_text

    # Tag formatting methods

    @staticmethod
    def format_img(
        ft: "StyleAndTextTuples",
        width: "int",
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
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a horizontal rule."""
        # ft = wrap(ft, width, style=theme["style"])
        return ft

    @staticmethod
    def format_hr(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a horizontal rule."""
        ft = [(theme["style"], "─" * width)]
        return ft

    @staticmethod
    def format_h1(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a top-level heading wrapped and centered with a full width double border."""
        ft = wrap(ft, width - 4, style=theme["style"])
        ft = align(FormattedTextAlign.CENTER, ft, width=width - 4, style=theme["style"])
        ft = add_border(
            ft,
            width=width,
            border=Double.grid,
            style=theme["style"],
        )
        return ft

    @staticmethod
    def format_h2(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a 2nd-level headding wrapped and centered with a double border."""
        ft = wrap(ft, width=width - 4, style=theme["style"])
        ft = align(FormattedTextAlign.CENTER, ft)
        ft = add_border(
            ft,
            border=Thin.grid,
            style=theme["style"],
        )
        ft = align(FormattedTextAlign.CENTER, ft, width=width, style=theme["style"])
        return ft

    @staticmethod
    def format_h(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format headings wrapped and centeredr."""
        ft = wrap(ft, width, style=theme["style"])
        ft = align(FormattedTextAlign.CENTER, ft, width=width)
        return ft

    @staticmethod
    def format_p(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format paragraphs wrapped."""
        # ft = wrap(ft, width, style=theme["style"])
        return ft

    @staticmethod
    def format_br(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format line breaks."""
        return [("", "\n")]

    @staticmethod
    def format_blockquote(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format blockquotes with a solid left margin."""
        ft = wrap(strip(ft), width=width, style=theme["style"])
        ft = indent(ft, margin="▌ ", style=f"{theme['style']} class:margin")
        return ft

    @staticmethod
    def format_pre(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format a pre-formatted block with a border if it contains code."""
        if element.contents and element.contents[0].name == "code":
            ft = align(FormattedTextAlign.LEFT, ft, width - 4)
            ft = add_border(ft, width, border=Thin.grid)
        return ft

    @staticmethod
    def format_a(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format hyperlinks and adds link escape sequences."""
        href = element.attrs.get("href")
        if href:
            link_id = randint(0, 999999)  # noqa S311
            return [
                ("[ZeroWidthEscape]", tmuxify(f"\x1b]8;id={link_id};{href}\x1b\\")),
                *ft,
                ("[ZeroWidthEscape]", tmuxify("\x1b]8;;\x1b\\")),
            ]
        else:
            return ft

    @staticmethod
    def format_summary(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format summaries with an arrow."""
        return [
            ("class:html.summary.arrow", " ⮟ "),
            *indent(
                wrap(ft, width=width, style=theme["style"]),
                margin="   ",
                skip_first=True,
                style=theme["style"],
            ),
        ]

    @staticmethod
    def format_details(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format details indented."""
        ft = strip(ft)
        ft = indent(ft, margin="   ")
        return ft

    @staticmethod
    def format_q(
        ft: "StyleAndTextTuples",
        width: "int",
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
