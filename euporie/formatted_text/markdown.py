"""Contains a markdown to formatted text parser."""

from random import randint
from typing import TYPE_CHECKING, Callable, Dict, List, Optional
from warnings import warn

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import StyleAndTextTuples, to_formatted_text
from prompt_toolkit.formatted_text.utils import to_plain_text

from euporie.border import Double, Thick, Thin
from euporie.formatted_text.table import DummyRow, Table
from euporie.formatted_text.utils import (
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

if TYPE_CHECKING:
    from markdown_it.token import Token

    from euporie.border import GridStyle
    from euporie.formatted_text.table import Row


# Check for markdown-it-py
markdown_parser: Optional["MarkdownIt"] = None

try:
    from markdown_it import MarkdownIt
except ModuleNotFoundError:
    warn("The markdown parser requires `markdown-it-py` to be installed")
else:

    class MarkdownParser(MarkdownIt):
        """Subclass the markdown parser to allow ``file:`` URIs."""

        def validateLink(self, url: "str") -> "bool":
            """Allows all link URIs."""
            return True

    markdown_parser = (
        MarkdownParser().enable("linkify").enable("table").enable("strikethrough")
    )

# Check for markdown-it-py plugins
try:
    import mdit_py_plugins  # noqa F401
except ModuleNotFoundError:
    pass
else:
    from mdit_py_plugins.amsmath import amsmath_plugin
    from mdit_py_plugins.dollarmath.index import dollarmath_plugin
    from mdit_py_plugins.texmath.index import texmath_plugin

    if markdown_parser is not None:
        markdown_parser.use(texmath_plugin)
        markdown_parser.use(dollarmath_plugin)
        markdown_parser.use(amsmath_plugin)


_SIDES = {
    "left": FormattedTextAlign.LEFT,
    "right": FormattedTextAlign.RIGHT,
    "center": FormattedTextAlign.CENTER,
}


def h1(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format a top-level heading wrapped and centered with a full width double border."""
    ft = wrap(ft, width - 4)
    ft = align(FormattedTextAlign.CENTER, ft, width=width - 4)
    ft = add_border(ft, width, style="class:md.h1.border", border=Double.grid)
    ft.append(("", "\n\n"))
    return ft


def h2(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format a 2nd-level headding wrapped and centered with a double border."""
    ft = wrap(ft, width=width - 4)
    ft = align(FormattedTextAlign.CENTER, ft)
    ft = add_border(ft, style="class:md.h2.border", border=Thin.grid)
    ft = align(FormattedTextAlign.CENTER, ft, width=width)
    ft.append(("", "\n\n"))
    return ft


def h(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format headings wrapped and centeredr."""
    ft = wrap(ft, width)
    ft = align(FormattedTextAlign.CENTER, ft, width=width)
    ft.append(("", "\n\n"))
    return ft


def p(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format paragraphs wrapped."""
    ft = wrap(ft, width)
    ft.append(("", "\n" if token.hidden else "\n\n"))
    return ft


def ul(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format unordered lists."""
    ft.append(("", "\n"))
    return ft


def ol(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Formats ordered lists."""
    ft.append(("", "\n"))
    return ft


def li(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Formats list items."""
    ft = strip(ft)
    # Determine if this is an ordered or unordered list
    if token.attrs.get("data-list-type") == "ol":
        margin_style = "class:md.ol.margin"
    else:
        margin_style = "class:md.ul.margin"
    # Get the margin (potentially contains aligned item numbers)
    margin = str(token.attrs.get("data-margin", "•"))
    # We put a speace each side of the margin
    ft = indent(ft, margin=" " * (len(margin) + 2), style=margin_style)
    ft[0] = (ft[0][0], f" {margin} ")
    ft.append(("", "\n"))
    return ft


def hr(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format horizontal rules."""
    ft = [
        ("class:md.hr", "─" * width),
        ("", "\n\n"),
    ]
    return ft


def br(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format line breaks."""
    return [("", "\n")]


def blockquote(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format blockquotes with a solid left margin."""
    ft = strip(ft)
    ft = indent(ft, margin="▌ ", style="class:md.blockquote.margin")
    ft.append(("", "\n\n"))
    return ft


def code(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format inline code, and lexes and formats code blocks with a border."""
    if token.block:
        ft = strip(ft, left=False, right=True, char="\n")
        ft = lex(ft, lexer_name=token.info)
        ft = align(FormattedTextAlign.LEFT, ft, width - 4)
        ft = add_border(ft, width, style="class:md.code.block.border", border=Thin.grid)
        ft = apply_style(ft, style="class:md.code.block")
        ft.append(("", "\n\n"))
    else:
        ft = apply_style(ft, style="class:md.code.inline")
    return ft


def math(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format inline maths, and quotes math blocks."""
    if token.block:
        return blockquote(ft, width - 2, left, token)
    else:
        return ft

        """     width=width,
                info=token.info,
                block=token.block,
                attrs=token.attrs,
                hidden=token.hidden,
                left=left,"""


def a(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format hyperlinks and adds link escape sequences."""
    href = token.attrs.get("href")
    if href:
        link_id = randint(0, 999999)  # noqa S311
        return [
            ("[ZeroWidthEscape]", f"\x1b]8;id={link_id};{href}\x1b\\"),
            *ft,
            ("[ZeroWidthEscape]", "\x1b]8;;\x1b\\"),
        ]
    else:
        return ft


def img(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Format image titles."""
    bounds = ("", "")
    if not to_plain_text(ft):
        # Add fallback text if there is no image title
        title = str(token.attrs.get("alt"))
        # Try getting the filename
        src = str(token.attrs.get("src", ""))
        if not title and not src.startswith("data:"):
            title = src.rsplit("/", 1)[-1]
        if not title:
            title = "Image"
        ft = [("class:md.img", title)]
    # Add the sunrise emoji to represent an image. I would use :framed_picture:, but it
    # requires multiple code-points and causes breakage in many terminals
    result = [("class:md.img", "🌄 "), *ft]
    result = apply_style(result, style="class:md.img")
    result = [
        ("class:md.img.border", f"{bounds[0]}"),
        *result,
        ("class:md.img.border", f"{bounds[1]}"),
    ]
    return result


# Maps HTML tag names to formatting functions. Functionality can be extended by
# modifying this dictionary
TAG_RULES: Dict[
    str,
    Callable[
        [StyleAndTextTuples, int, int, "Token"],
        StyleAndTextTuples,
    ],
] = {
    "h1": h1,
    "h2": h2,
    "h3": h,
    "h4": h,
    "h5": h,
    "h6": h,
    "p": p,
    "ul": ul,
    "ol": ol,
    "li": li,
    "hr": hr,
    "br": br,
    "blockquote": blockquote,
    "code": code,
    "math": math,
    "a": a,
    "img": img,
}

# Mapping showing how much width the formatting of block elements used. This is used to
# reduce the available width when rendering child elements
TAG_INSETS = {
    "li": 3,
    "blockquote": 2,
}


class Markdown:
    """A markdown formatted text renderer.

    Accepts a markdown string and renders it at a given width.
    """

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

        if markdown_parser is not None:
            self.formatted_text = self.render(
                tokens=markdown_parser.parse(self.markup),
                width=self.width,
            )
        else:
            self.formatted_text = lex(
                to_formatted_text(self.markup),
                lexer_name="markdown",
            )
        if strip_trailing_lines:
            self.formatted_text = strip(
                self.formatted_text,
                left=False,
                char="\n",
            )

    def render(
        self, tokens: List["Token"], width: int = 80, left: int = 0
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown tokens.

        Args:
            tokens: The list of parsed tokens to render
            width: The width at which to render the tokens
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        ft = []

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # If this is an inline block, render it's children
            if token.type == "inline" and token.children:
                ft += self.render(token.children, width)
                i += 1

            # Otherwise gather the tokens in the current block
            else:
                nest = 0
                tokens_in_block = 0
                for j, token in enumerate(tokens[i:]):
                    nest += token.nesting
                    if nest == 0:
                        tokens_in_block = j
                        break

                # If there is a special method for rendering the block, use it

                # Tables require special care
                if token.tag == "table":
                    ft += self.render_table(
                        tokens[i : i + tokens_in_block + 1],
                        width=width,
                        left=last_line_length(ft),
                    )

                # We need to keep track of item numbers in ordered lists
                elif token.tag == "ol":
                    ft += self.render_ordered_list(
                        tokens[i : i + tokens_in_block + 1],
                        width=width,
                        left=last_line_length(ft),
                    )

                # Otherwise all other blocks are rendered in the same way
                else:
                    ft += self.render_block(
                        tokens[i : i + tokens_in_block + 1],
                        width=width,
                        left=last_line_length(ft),
                    )

                i += j + 1

        return ft

    def render_block(
        self,
        tokens: List["Token"],
        width: int,
        left: int = 0,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown tokens representing a block element.

        Args:
            tokens: The list of parsed tokens to render
            width: The width at which to render the tokens
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images

        Returns:
            Formatted text

        """
        ft = []
        token = tokens[0]

        # Restrict width if necessary
        inset = TAG_INSETS.get(token.tag)
        if inset:
            width -= inset

        style = "class:md"
        if token.tag:
            style = f"{style}.{token.tag}"

        # Render innards
        if len(tokens) > 1:
            ft += self.render(tokens[1:-1], width)
            ft = apply_style(ft, style)
        else:
            ft.append((style, token.content))

        # Apply tag rule
        rule = TAG_RULES.get(token.tag)
        if rule:
            ft = rule(
                ft,
                width,
                left,
                token,
            )

        return ft

    def render_ordered_list(
        self,
        tokens: List["Token"],
        width: int,
        left: int = 0,
    ) -> "StyleAndTextTuples":
        """Render an ordered list by adding indices to the child list items."""
        # Find the list item tokens
        list_level_tokens = []
        nest = 0
        for token in tokens:
            if nest == 1 and token.tag == "li":
                list_level_tokens.append(token)
            nest += token.nesting
        # Assign them a marking
        margin_width = len(str(len(list_level_tokens)))
        for i, token in enumerate(list_level_tokens, start=1):
            token.attrs["data-margin"] = str(i).rjust(margin_width) + "."
            token.attrs["data-list-type"] = "ol"
        # Now render the tokens as normal
        return self.render_block(
            tokens,
            width=width,
            left=left,
        )

    def render_table(
        self,
        tokens: List["Token"],
        width: int,
        left: int = 0,
        border: "GridStyle" = Thin.grid,
    ) -> "StyleAndTextTuples":
        """Render a list of parsed markdown tokens representing a table element.

        Args:
            tokens: The list of parsed tokens to render
            width: The width at which to render the tokens
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            border: The border style to use to render the table

        Returns:
            Formatted text

        """
        table = Table(border_style="class:md.table.border")
        # Stack the tokens in the shape of the table
        i = 0
        row: "Row" = DummyRow()
        while i < len(tokens):
            token = tokens[i]
            if token.type == "tr_open":
                row = table.new_row()
            elif token.type in ("th_open", "td_open"):
                side = "left"
                # Check CSS for text alignment
                for style_str in str(token.attrs.get("style", "")).split(";"):
                    if ":" in style_str:
                        key, value = style_str.strip().split(":", 1)
                        if key.strip() == "text-align":
                            side = value
                start_token = token
                for j, token in enumerate(tokens[i:]):
                    if token.type in ("th_close", "td_close"):
                        row.new_cell(
                            text=self.render(tokens[i : i + j + 1], width=width),
                            border=Thick if start_token.type == "th_open" else None,
                            align=_SIDES.get(side, FormattedTextAlign.LEFT),
                        )
                        break
                i += j
            i += 1
        return table.render(width) + [("", "\n\n")]

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Formatted text magic method."""
        return self.formatted_text


if __name__ == "__main__":
    import sys

    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles.style import Style

    from euporie.style import MARKDOWN_STYLE

    with open(sys.argv[1]) as f:
        print_formatted_text(Markdown(f.read()), style=Style(MARKDOWN_STYLE))
