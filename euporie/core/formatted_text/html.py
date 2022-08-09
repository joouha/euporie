"""Contains a markdown to formatted text parser."""

from __future__ import annotations

import re
from ast import literal_eval
from math import ceil
from random import randint
from textwrap import indent as str_indent
from typing import TYPE_CHECKING, Callable, Optional
from warnings import warn

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import StyleAndTextTuples, to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines, to_plain_text

from euporie.core.border import Double, Invisible, Padding, Rounded, Thick, Thin
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

# from html.parser import HTMLParser


_SIDES = {
    "left": FormattedTextAlign.LEFT,
    "right": FormattedTextAlign.RIGHT,
    "center": FormattedTextAlign.CENTER,
}

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
)


def try_eval(value: "str", default: "Any" = None) -> "Any":
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
    finally:
        return parsed_value


# Mapping showing how much width the formatting of block elements used. This is used to
# reduce the available width when rendering child elements
TAG_INSETS = {
    "li": 3,
    "blockquote": 2,
    "summary": 2,
}


class HTML:
    """A HTML formatted text renderer.

    Accepts a HTML string and renders it at a given width.
    """

    _BASE_MARGINS = {
        # We use padding to store margin values...
        "blockquote": Padding(1, 0, 1, 0),
        "hr": (1, 0, 1, 0),
        "p": (1, 0, 1, 0),
        "pre": Padding(1, 0, 1, 0),
        "math": Padding(1, 0, 1, 0),
    }

    def __init__(
        self,
        markup: str,
        width: Optional[int] = None,
        strip_trailing_lines: bool = True,
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

        self.formatted_text = self.render(
            bs4.BeautifulSoup(markup, "html.parser").contents,
            width=self.width,
        )

        if strip_trailing_lines:
            self.formatted_text = strip(
                self.formatted_text,
                left=False,
                char="\n",
            )

    def render(
        self,
        elements: "list[PageElement]",
        width: "int" = 80,
        left: "int" = 0,
        preformatted: "bool" = False,
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
        ft = []

        def _draw_margin(element: "PageElement", index: "int") -> "None":
            """Draw the vertical margins for an element."""
            nonlocal ft

            margin = self._BASE_MARGINS.get(element.name, Padding(0, 0, 0, 0))[index]
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
            ft += [("", "\n" * (max(0, margin - i)))]

        for element in elements:

            # Is the current element a block element?
            block = element.name and element.name not in _INLINE_ELEMENTS

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
                _draw_margin(element, 0)

            # If there is a special method for rendering the block, use it; otherwise
            # use the generic `render_block` function
            render_func = getattr(self, f"render_{element.name}", self.render_block)

            # Render the element
            rendering = render_func(
                element,
                width=width,
                left=last_line_length(ft),
                preformatted=_preformatted,
            )
            ft += rendering

            # Draw block element bottom margin, ensuring block elements end on a new
            # line, and that margins collapse
            if block:
                _draw_margin(element, 2)

        return ft

    def render_block(
        self,
        element: "PageElement",
        width: int,
        left: int = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a block element.

        Args:
            elements: The list of parsed elements to render
            width: The width at which to render the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        ft = []

        tag_ft = []

        # Restrict width if necessary
        inset = TAG_INSETS.get(element.name)
        if inset:
            width -= inset

        style = "class:html"
        if element.name:
            style = f"{style}.{element.name}"

        # Render innards
        if not element.name:
            # or (len(element.contents) == 1 and not element.contents[0].name):
            text = element.text
            if not preformatted:
                text = re.sub(r"\s+", " ", text.strip("\n"))
            if text:
                tag_ft.append((style, text))
        else:
            tag_ft += self.render(element.contents, width, left, preformatted)
            tag_ft = apply_style(tag_ft, style)

        # Apply tag formatting
        if format_func := getattr(self, f"format_{element.name}", None):
            tag_ft = format_func(
                tag_ft,
                width,
                left,
                element,
            )
        ft += tag_ft

        return ft

    def render_ol(
        self,
        element: "PageElement",
        width: int,
        left: int = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render an ordered list by adding indices to the child list items."""
        # Assign them a marking
        items = [li for li in element.children if li.name == "li"]
        margin_width = len(str(len(items)))
        for i, element in enumerate(items, start=1):
            element.attrs["data-margin"] = str(i).rjust(margin_width) + "."
            element.attrs["data-list-type"] = "ol"
        # Now render the elements as normal
        return self.render(items, width=width, left=left, preformatted=preformatted)

    def render_table(
        self,
        element: "PageElement",
        width: int,
        left: int = 0,
        preformatted: "bool" = False,
        border: "GridStyle" = Thin.grid,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown elements representing a table element.

        Args:
            elements: The list of parsed elements to render
            width: The width at which to render the elements
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            border: The border style to use to render the table

        Returns:
            Formatted text

        """
        ft = []

        # Determine whether to draw a border
        border = try_eval(element.attrs.get("border", 1))

        border_style = {
            0: Invisible,
            1: Thin,
            2: Double,
            3: Thick,
        }.get(border, Thick)

        table = Table(
            border_style="class:html.table.border",
            border=border_style,
            border_collapse=True,
        )

        # Stack the elements in the shape of the table
        def render_rows(elements: "list[element]") -> "None":
            for tr in elements:
                if tr.name == "tr":
                    row = table.new_row()
                    for td in tr.children:
                        if td.name in ("th", "td"):
                            side = "left"
                            # Check CSS for text alignment
                            for style_str in str(td.attrs.get("style", "")).split(";"):
                                if ":" in style_str:
                                    key, value = style_str.strip().split(":", 1)
                                    if key.strip() == "text-align":
                                        side = value
                            row.new_cell(
                                text=self.render(
                                    td.children, width=width, preformatted=preformatted
                                ),
                                border=Thick if td.name == "th" and border else None,
                                align=_SIDES.get(side, FormattedTextAlign.LEFT),
                                colspan=try_eval(td.attrs.get("colspan", 1)),
                                rowspan=try_eval(td.attrs.get("rowspan", 1)),
                                style="class:bold" if td.name == "th" else "",
                            )

        for child in element.find_all("caption", recursive=False):
            ft += [*self.render(child, width, left, preformatted), ("", "\n")]
        for child in element.find_all("thead", recursive=False):
            render_rows(child.children)
        for child in element.find_all("tbody", recursive=False):
            render_rows(child.children)
        # Render rows not in a head / body / foot as part of the body
        render_rows(element.children)
        for child in element.find_all("tfoot", recursive=False):
            render_rows(child.children)

        ft += table.render(width)
        return ft

    def render_details(
        self,
        element: "PageElement",
        width: int,
        left: int = 0,
        preformatted: "bool" = False,
    ) -> "StyleAndTextTuples":
        """Render an expand summary / details."""
        summary_elements = element.find_all("summary", recursive=False)
        ft = self.render(summary_elements, width=width, preformatted=preformatted)

        detail_elements = [e for e in element.contents if e.name != "summary"]
        ft += self.format_details(
            self.render(detail_elements, width - 2, left, preformatted),
            width,
            left,
            element,
        )
        return ft

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Formatted text magic method."""
        return self.formatted_text

    # Tag formatting methods

    @staticmethod
    def format_h1(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format a top-level heading wrapped and centered with a full width double border."""
        ft = wrap(ft, width - 4)
        ft = align(FormattedTextAlign.CENTER, ft, width=width - 4)
        ft = add_border(
            ft, width=width, style="class:html.h1.border", border=Double.grid
        )
        return ft

    @staticmethod
    def format_h2(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format a 2nd-level headding wrapped and centered with a double border."""
        ft = wrap(ft, width=width - 4)
        ft = align(FormattedTextAlign.CENTER, ft)
        ft = add_border(ft, style="class:html.h2.border", border=Thin.grid)
        ft = align(FormattedTextAlign.CENTER, ft, width=width)
        return ft

    @staticmethod
    def format_h(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format headings wrapped and centeredr."""
        ft = wrap(ft, width)
        ft = align(FormattedTextAlign.CENTER, ft, width=width)
        return ft

    @staticmethod
    def format_p(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format paragraphs wrapped."""
        ft = wrap(ft, width)
        return ft

    @staticmethod
    def format_ul(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format unordered lists."""
        return ft

    @staticmethod
    def format_ol(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Formats ordered lists."""
        return ft

    @staticmethod
    def format_li(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Formats list items."""
        ft = strip(ft)
        # Determine if this is an ordered or unordered list
        if element.attrs.get("data-list-type") == "ol":
            margin_style = "class:html.ol.margin"
        else:
            margin_style = "class:html.ul.margin"
        # Get the margin (potentially contains aligned item numbers)
        margin = str(element.attrs.get("data-margin", "•"))
        # We put a speace each side of the margin
        ft = wrap(ft, width)
        ft = indent(ft, margin=" " * (len(margin) + 2), style=margin_style)
        ft[0] = (ft[0][0], f" {margin} ")
        return ft

    @staticmethod
    def format_hr(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format horizontal rules."""
        ft = [
            ("class:html.hr", "─" * width),
        ]
        return ft

    @staticmethod
    def format_br(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format line breaks."""
        return [("", "\n")]

    @staticmethod
    def format_blockquote(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format blockquotes with a solid left margin."""
        ft = strip(ft)
        ft = indent(ft, margin="▌ ", style="class:html.blockquote.margin")
        return ft

    @staticmethod
    def format_code(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format lexes code blocks."""
        for class_name in element.attrs.get("class", []):
            if class_name.startswith("language-"):
                language = class_name[9:]
                ft = strip(ft, left=False, right=True, char="\n")
                ft = lex(ft, lexer_name=language)
        return ft

    @staticmethod
    def format_pre(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format a pre-formatted block with a border if it contains code."""
        if element.contents and element.contents[0].name == "code":
            ft = align(FormattedTextAlign.LEFT, ft, width - 4)
            ft = add_border(ft, width, border=Thin.grid)
        return ft

    @staticmethod
    def format_a(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
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
        width: int,
        left: int,
        element: "PageElement",
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
        width: int,
        left: int,
        element: "PageElement",
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
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format summaries with an arrow."""
        return [
            ("class:html.summary.arrow", "⮟ "),
            *indent(ft, margin="  ", skip_first=True),
        ]

    @staticmethod
    def format_details(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        """Format details indented."""
        ft = strip(ft)
        ft = indent(ft, margin="  ")
        return ft

    @staticmethod
    def format_q(
        ft: "StyleAndTextTuples",
        width: int,
        left: int,
        element: "PageElement",
    ) -> "StyleAndTextTuples":
        return [("", '"'), *ft, ("", '"')]


if __name__ == "__main__":
    import sys

    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles.style import Style
    from upath import UPath

    from euporie.core.style import HTML_STYLE

    with UPath(sys.argv[1]).open() as f:
        print_formatted_text(HTML(f.read()), style=Style(HTML_STYLE))
