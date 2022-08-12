"""Contains a markdown to formatted text parser."""

from __future__ import annotations

import re
from ast import literal_eval
from collections import ChainMap, defaultdict
from functools import lru_cache
from math import ceil
from random import randint
from textwrap import indent as str_indent
from typing import TYPE_CHECKING, Any, Dict, Callable, Optional
from warnings import warn

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import StyleAndTextTuples, to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines, to_plain_text

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
from euporie.core.formatted_text.table import DummyRow, Table
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
    from typing import Any, Union

    from bs4.element import PageElement

    from euporie.core.border import GridStyle
    from euporie.core.formatted_text.table import Row

import bs4
from html.parser import HTMLParser


# Prefer 6-digit hex-colors over 3-digit ones
_COLOR_RE = re.compile("#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})")


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


def get_digits(value: "str") -> "str":
    for c in value.partition(".")[0].split():
        if c.isdigit():
            return c.lstrip("0")
    else:
        return ""


def get_color(value: "str") -> "str":
    color = ""
    if match := re.search(_COLOR_RE, value):
        hexes = match.group(1)
        if len(hexes) == 3:
            hexes = "".join(2 * s for s in hexes)
        color = f"#{hexes}"
    return color


class PageElement:
    def __init__(
        self,
        name: "Optional[str]",
        parent: "Optional[PageElement]",
        attrs: "dict[str, str]",
        text: "str" = "",
    ):
        self.name = name
        self.parent = parent
        self.text = text
        self.attrs = attrs
        self.contents = []
        self.closed = False

        self.attrs["class"] = self.attrs.get("class", "").split()

    def find_all(self, tag: "str", recursive: "bool" = False):
        """Find all child elements of a given tag type."""
        return [element for element in self.contents if element.name == tag]

    @property
    def descendents(self) -> "Generator[PageElement]":
        """Yields all descendent elements."""
        for child in self.contents:
            yield child
            yield from child.descendents

    def __repr__(self, d: "int" = 0):
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

    def __init__(self):
        super().__init__()
        self.curr = self.soup = PageElement(name="soup", parent=None, attrs={})

    def parse(self, markup):
        self.curr = self.soup = PageElement(name="soup", parent=None, attrs={})
        self.feed(markup)
        return self.soup

    def handle_starttag(self, tag: "str", attrs: "list[tuple[str, str]]"):
        self.autoclose()
        element = PageElement(name=tag, parent=self.curr, attrs=dict(attrs))
        self.curr.contents.append(element)
        self.curr = element

    def autoclose(self):
        # Automatically close void elements
        if not self.curr.closed and self.curr.name in self._VOID_ELEMENTS:
            self.curr.closed = True
            self.curr = self.curr.parent

    def handle_data(self, data):
        self.autoclose()

        self.curr.contents.append(
            PageElement(name=None, parent=self.curr, text=data, attrs={})
        )

    def handle_endtag(self, tag):
        if tag != self.curr.name:
            self.autoclose()
        self.curr.closed = True
        if self.curr.parent:
            self.curr = self.curr.parent


parser = CustomHTMLParser()


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    # Maps css side values to alignment enums
    _SIDES = {
        "left": FormattedTextAlign.LEFT,
        "right": FormattedTextAlign.RIGHT,
        "center": FormattedTextAlign.CENTER,
    }

    _METADATA_ELEMENTS = (
        "head",
        "base",
        "command",
        "link",
        "meta",
        "noscript",
        "script",
        "style",
        "title",
    )

    # A list of HTML elements which are rendered as "in0line" elements
    _INLINE_ELEMENTS = (
        "a",
        "abbr",
        "acronym",
        "audio",
        "b",
        "bdi",
        "bdo",
        "big",
        "br",
        "button",
        "canvas",
        "cite",
        "code",
        "data",
        "datalist",
        "del",
        "dfn",
        "em",
        "embed",
        "i",
        "iframe",
        "img",
        "input",
        "ins",
        "kbd",
        "label",
        "map",
        "mark",
        "math",
        "meter",
        "noscript",
        "object",
        "output",
        "picture",
        "progress",
        "q",
        "ruby",
        "s",
        "samp",
        "script",
        "select",
        "slot",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "svg",
        "template",
        "textarea",
        "time",
        "u",
        "tt",
        "var",
        "video",
        "wbr",
        #
        "td",
        "th",
    )

    # Mapping showing how much width the formatting of block elements used. This is used to
    # reduce the available width when rendering child elements
    _TAG_INSETS = {
        # "li": 3,
        "blockquote": 2,
        "summary": 3,
        "details": 3,
    }

    _BORDER_WIDTHS = {
        "0": BorderLineStyle(Invisible, Invisible, Invisible, Invisible),
        "1": BorderLineStyle(Thin, Thin, Thin, Thin),
        "2": BorderLineStyle(Double, Double, Double, Double),
        "3": BorderLineStyle(Thick, Thick, Thick, Thick),
    }

    # The default theme to apply to various elements
    _ELEMENT_BASE_THEMES = defaultdict(
        dict,
        {
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
            },
            "blockquote": {"margin": Padding(1, 0, 1, 0)},
            "hr": {"margin": Padding(1, 0, 1, 0)},
            "p": {"margin": Padding(1, 0, 1, 0)},
            "pre": {"margin": Padding(1, 0, 1, 0)},
            "math": {"margin": Padding(1, 0, 1, 0)},
            "details": {"margin": Padding(1, 0, 1, 0)},
            "summary": {"margin": Padding(0, 0, 1, 0)},
            "caption": {"align": FormattedTextAlign.CENTER},
            "th": {"style": "bold"},
            "table": {"padding": Padding(0, 1, 0, 1)},
        },
    )

    def __init__(
        self,
        markup: "str",
        width: "Optional[int]" = None,
        strip_trailing_lines: "bool" = True,
    ) -> None:
        """Initialize the markdown formatter.

        Args:
            markup: The markdown text to render
            width: The width in characters available for rendering. If :py:const:`None`
                the terminal width will be used
            strip_trailing_lines: If :py:const:`True`, empty lines at the end of the
                rendered output will be removed

        """
        self.markup = markup
        self.width = width or get_app_session().output.get_size().columns
        self.strip_trailing_lines = strip_trailing_lines

        self.css = {
            ".dataframe": {
                "border": BorderLineStyle(Invisible, Invisible, Invisible, Invisible),
                "border_collapse": True,
                "style_classes": "class:dataframe",
            }
        }

        # Parse the markup
        # soup = bs4.BeautifulSoup(markup, "html.parser")
        soup = parser.parse(markup)

        # Parse the styles
        self.css.update(self.parse_styles(soup))

        # Render the markup
        self.formatted_text = self.render(
            soup.contents,
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
        rules = {}
        for child in soup.descendents:
            css_str = ""

            # In case of a <link> style, load the url
            if (
                child.name == "link"
                and child.attrs.get("rel") == "stylesheet"
                and (href := child.attrs.get("href"))
            ):
                css_str = load_url(href) or ""

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
                        selector, _, content = rule.partition("{")
                        selector = selector.strip()
                        # For now, only parse single element and ID selectors
                        # TODO - more complex rules
                        if len(selector.split()) == 1:
                            content = content.strip().rstrip(";")
                            rule_content = self.parse_css_content(content)
                            if selector in rules:
                                rules[selector].update(rule_content)
                            else:
                                rules[selector] = rule_content

        return rules

    def parse_css_content(self, content: "str") -> "dict[str, Any]":
        """Convert CSS declarations into the internals style representation."""
        output = {}

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
                    (digits := get_digits(value)) and int(digits) > 700
                ):
                    output.setdefault("style_attrs", "")
                    output["style_attrs"] += " bold"

            elif name == "text-decoration":
                if value == "underline":
                    output.setdefault("style_attrs", "")
                    output["style_attrs"] += " underline"

            elif name == "text-align":
                output["align"] = FormattedTextAlign(value.upper())

            elif name == "border-width":
                if digits := get_digits(value):
                    output["border"] = self._BORDER_WIDTHS.get(digits)

            elif name == "visibility":
                output["hidden"] = value == "hidden"

            elif name == "display":
                output["skip"] = value == "none"

        return output

    def get_element_theme(
        self, element: "PageElement", parent_theme: "Optional[dict]" = None
    ) -> "ChainMap":
        """Compute the theme of an element."""
        element_id = element.attrs.get("id")

        # Add extra attributes
        extras = {}

        # -> border
        if border_attr := element.attrs.get("border"):
            extras["border"] = self._BORDER_WIDTHS.get(
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

        # Check for lanaguage highlighting classes
        for class_name in element.attrs.get("class", []):
            if class_name.startswith("language-"):
                extras["language"] = class_name[9:]
                break
            elif class_name.startswith("highlight-"):
                extras["language"] = class_name[10:]
                break

        # Chain themes from various levels
        theme = ChainMap(
            # Tag styles
            self.parse_css_content(element.attrs.get("style", "")),
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
            self._ELEMENT_BASE_THEMES[element.name],
            # Parent theme
            dict(parent_theme) if parent_theme else {},
            # Add an element class
            {"style_classes": f"class:html,{element.name}" if element.name else ""},
            # Default element style
            self._ELEMENT_BASE_THEMES["default"],
        )

        # Concatenate styles
        style_classes = ""
        style_attrs = ""
        for mapping in theme.maps:
            if style_class := mapping.get("style_classes"):
                style_classes = f"{style_classes} {style_class}"
            if style_attr := mapping.get("style_attrs"):
                style_attrs = f"{style_attrs} {style_attr}"
        style_str = f"{style_classes} {style_attrs}"
        if fg := theme.get("style_fg"):
            style_str = f"{style_str} fg:{fg}"
        if bg := theme.get("style_bg"):
            style_str = f"{style_str} bg:{bg}"
        extras["style"] = style_str

        return theme

    def render(
        self,
        elements: "list[PageElement]",
        width: "int" = 80,
        left: "int" = 0,
        preformatted: "bool" = False,
        parent_theme: "Optional[dict]" = None,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements.

        Args:
            elements: The list of parsed elements to render
            width: The width at which to render the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: If True, whitespace will not be stripped from the element's
                text

        Returns:
            Formatted text

        """
        if parent_theme is None:
            parent_theme = self._ELEMENT_BASE_THEMES["default"]

        ft = []

        def _draw_margin(
            ft: "StyleAndTextTuples", element: "PageElement", index: "int"
        ) -> "None":
            """Draw the vertical margins for an element."""
            theme = self.get_element_theme(element, parent_theme)
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
            return [
                (
                    # self.get_element_theme(element)["style"],
                    parent_theme["style"] if parent_theme else "",
                    "\n" * (max(0, margin - i)),
                )
            ]

        for element in elements:

            # Do not render metadata tags
            if element.name in self._METADATA_ELEMENTS:
                continue

            # Is the current element a block element?
            block = element.name and element.name not in self._INLINE_ELEMENTS

            # Set preformatted flag for <pre> tags
            _preformatted = preformatted
            if element.name == "pre":
                _preformatted = True

            # Convert tags with "math" class to <math> tag
            if element.name and "math" in element.attrs.get("class", []):
                element.name = "math"

            # Render block element margins. We want to ensure block elements always
            # start on a new line, and that margins collapse.
            # Do not draw a margin if this is the first element of the render list.
            if block and ft:
                ft.extend(_draw_margin(ft, element, 0))

            # If there is a special method for rendering the block, use it; otherwise
            # use the generic `render_block` function
            render_func = getattr(self, f"render_{element.name}", self.render_block)

            # Render the element
            rendering = render_func(
                element,
                width=width,
                left=last_line_length(ft),
                preformatted=_preformatted,
                parent_theme=parent_theme,
            )

            # Draw block element bottom margin, ensuring block elements end on a new
            # line, and that margins collapse
            if block:
                rendering.extend(_draw_margin(rendering, element, 2))

            ft.extend(rendering)

        return ft

    def render_block(
        self,
        element: "PageElement",
        width: "int",
        left: "int" == 0,
        preformatted: "bool" = False,
        parent_theme: "Optional[dict]" = None,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a block element.

        Args:
            element: The list of parsed elements to render
            width: The width at which to render the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: When True, whitespace in the the element's text is not
                collapsed

        Returns:
            Formatted text

        """
        ft = []

        theme = self.get_element_theme(element, parent_theme)

        # Render a tag
        if element.name:
            # Restrict width if necessary
            inner_width = width - self._TAG_INSETS.get(element.name, 0)

            ft.extend(
                self.render(
                    element.contents,
                    inner_width,
                    left,
                    preformatted,
                    parent_theme=theme,
                )
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

            # Fill space around an element
            if element.name not in self._INLINE_ELEMENTS:
                from prompt_toolkit.formatted_text.utils import fragment_list_width

                ft = wrap(ft, width)
                filled_output = []

                # Remove one trailing newline
                ft = strip(ft, left=False, right=True, char="\n")
                for i, frag in enumerate(reversed(ft)):
                    if not frag[1]:
                        continue
                    if frag[1].endswith("\n"):
                        ft[-i] = (frag[0], frag[1][:-1])
                        break

                # Format the remainder of each line
                for line in split_lines(ft):
                    filled_output.extend(line)
                    remaining = width - fragment_list_width(line)
                    filled_output.append((theme["style"], (" " * remaining)))
                    # filled_output.append((theme["style"], ("·" * remaining)))
                    filled_output.append(("", "\n"))

                ft = filled_output

        # Render a text element
        else:
            # Strip the text
            text = element.text
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
                text = re.sub(r"\s+", " ", text.replace("\n", ""))

            style = parent_theme["style"]

            if parent_theme.get("hidden"):
                text = " " * len(text)
                style = f"{style} nounderline"

            # Render the text
            if text:
                ft.append((style, text))

        return ft

    def render_ol(
        self,
        element: "PageElement",
        width: "int",
        left: "int" == 0,
        preformatted: "bool" = False,
        parent_theme: "Optional[dict]" = None,
    ) -> "StyleAndTextTuples":
        """Render order lists, adding item numbers to child <li> elements."""
        items = [li for li in element.contents if li.name == "li"]
        margin_width = len(str(len(items)))
        for i, item in enumerate(items, start=1):
            item.attrs["data-margin"] = str(i).rjust(margin_width) + "."
            item.attrs["data-list-type"] = "ol"
        # Render as normal
        ft = self.render_block(
            element,
            width=width,
            left=left,
            preformatted=preformatted,
            parent_theme=self.get_element_theme(element, parent_theme),
        )
        return ft

    def render_li(
        self,
        element: "PageElement",
        width: "int",
        left: "int" == 0,
        preformatted: "bool" = False,
        parent_theme: "Optional[dict]" = None,
    ) -> "StyleAndTextTuples":
        """Render a list element."""
        # Get the element's theme
        theme = self.get_element_theme(element, parent_theme)
        # Is this a <ol> or a <ul> list?
        list_type = element.attrs.get("data-list-type", "ul")
        # Get the bullet details
        bullet = str(element.attrs.get("data-margin", "•"))
        bullet_str = f" {bullet} "
        bullet_width = len(bullet_str)
        # Render the contents of the list item
        ft = self.render(
            element.contents,
            # Restrict the available width by the margin width
            width=width - bullet_width,
            left=left,
            preformatted=preformatted,
            parent_theme=theme,
        )
        # Wrap the list item
        ft = wrap(ft, width - bullet_width)
        # Add the bullet
        ft = [(f"{theme['style']} class:{list_type}.bullet", bullet_str), *ft]
        # Indent subsequent lines
        ft = indent(
            ft, margin=" " * bullet_width, skip_first=True, style=theme["style"]
        )
        ft = strip(ft, left=False, right=True)
        return ft

    def render_table(
        self,
        element: "PageElement",
        width: "int",
        left: "int" == 0,
        preformatted: "bool" = False,
        parent_theme: "Optional[dict]" = None,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a table element.

        Args:
            element: The list of parsed elements to render
            width: The width at which to render the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            preformatted: When True, whitespace in the the element's text is not
                collapsed

        Returns:
            Formatted text

        """
        ft = []

        table_theme = self.get_element_theme(element, parent_theme)
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
        def render_rows(elements: "list[element]") -> "None":
            for tr in elements:
                if tr.name == "tr":
                    tr_theme = self.get_element_theme(tr, table_theme)

                    row = table.new_row(
                        align=tr_theme["align"],
                        # padding=tr_theme["padding"],
                        border=tr_theme["border"],
                        style=tr_theme["style"],
                    )
                    for td in tr.contents:
                        if td.name in ("th", "td"):
                            td_theme = self.get_element_theme(td, tr_theme)
                            row.new_cell(
                                text=self.render_block(
                                    td,
                                    width=width,
                                    left=0,
                                    preformatted=preformatted,
                                    parent_theme=tr_theme,
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
                ft_caption = self.render(
                    child.contents, table_width, left, preformatted, table_theme
                )
                caption_theme = self.get_element_theme(child, table_theme)
                if ft_caption:
                    # TODO - rely on CSS default styling here
                    ft.extend(
                        align(
                            FormattedTextAlign.CENTER,
                            ft_caption,
                            width=table_width,
                            style=caption_theme["style"],
                        )
                    )
                    ft.append(("", "\n"))

        ft.extend(ft_table)

        return ft

    def render_details(
        self,
        element: "PageElement",
        width: "int",
        left: "int" == 0,
        preformatted: "bool" = False,
        parent_theme: "Optional[dict]" = None,
    ) -> "StyleAndTextTuples":
        """Render an expand summary / details."""
        theme = self.get_element_theme(element, parent_theme)
        # Restrict width if necessary
        width -= self._TAG_INSETS.get(element.name, 0)

        summary_elements = element.find_all("summary", recursive=False)
        ft = self.render(
            summary_elements, width=width, preformatted=preformatted, parent_theme=theme
        )

        detail_elements = [e for e in element.contents if e.name != "summary"]
        ft.extend(
            self.format_details(
                self.render(
                    detail_elements, width, left, preformatted, parent_theme=theme
                ),
                width,
                left,
                element,
                theme,
            )
        )
        return ft

    ###

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Formatted text magic method."""
        return self.formatted_text

    # Tag formatting methods

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
        ft = wrap(ft, width - 4)
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
        ft = wrap(ft, width=width - 4)
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
        ft = wrap(ft, width)
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
        ft = wrap(ft, width, style=theme["style"])
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
    def format_code(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Format lexes code blocks."""
        # for class_name in element.attrs.get("class", []):
        # if class_name.startswith("language-"):
        # language = class_name[9:]
        # ft = strip(ft, left=False, right=True, char="\n")
        # ft = lex(ft, lexer_name=language)
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
    def format_math(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Display LaTeX maths rendered as unicode text."""
        result: "StyleAndTextTuples" = []
        for (style, value, *_) in ft:
            result.append(
                (
                    style,
                    convert(value, "latex", "ansi"),
                )
            )
        if "block" in element.attrs.get("class", []):
            result = align(FormattedTextAlign.CENTER, result, width=width)
        return result

    @staticmethod
    def format_img(
        ft: "StyleAndTextTuples",
        width: "int",
        left: "int",
        element: "PageElement",
        theme: "dict",
    ) -> "StyleAndTextTuples":
        """Display images rendered as ANSI art."""
        result: "StyleAndTextTuples" = []
        src = str(element.attrs.get("src", ""))
        if data := load_url(src):
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
            result = strip(result, char="\n")
            # Optionally add a border
            if try_eval(element.attrs.get("border")):
                result = add_border(
                    result,
                    border=Rounded,
                    style="class:md.img.border",
                )
            # Indent for line continuation as images are inline
            result = indent(result, " " * left, skip_first=True)

        # Fallback to formatting the title if we still don't have image formatted-text data
        if not result:
            bounds = ("", "")
            if not to_plain_text(ft):
                # Add fallback text if there is no image title
                title = str(element.attrs.get("alt"))
                # Try getting the filename
                src = str(element.attrs.get("src", ""))
                if not title and not src.startswith("data:"):
                    title = src.rsplit("/", 1)[-1]
                if not title:
                    title = "Image"
                ft = [("class:md.img", title)]
            # Add the sunrise emoji to represent an image. I would use :framed_picture:, but it
            # requires multiple code-points and causes breakage in many terminals
            result = [("class:html.img", "🌄 "), *ft]
            result = apply_style(result, style="class:html.img")
            result = [
                ("class:html.img.border", f"{bounds[0]}"),
                *result,
                ("class:html.img.border", f"{bounds[1]}"),
            ]

        return result

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
                wrap(ft, width=width),
                margin="   ",
                skip_first=True,
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

    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles.style import Style
    from upath import UPath

    from euporie.core.style import HTML_STYLE

    with UPath(sys.argv[1]).open() as f:
        html = f.read()
        # parser.parse(html)
        print_formatted_text(HTML(html), style=Style(HTML_STYLE))
        # print(bs4.BeautifulSoup(html, "html.parser").contents)
