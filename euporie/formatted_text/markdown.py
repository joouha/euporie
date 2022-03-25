"""Contains a markdown to formatted text parser."""
from itertools import zip_longest
from typing import TYPE_CHECKING
from warnings import warn

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.utils import (
    fragment_list_width,
    split_lines,
    to_formatted_text,
    to_plain_text,
)
from prompt_toolkit.layout.containers import WindowAlign
from prompt_toolkit.styles import Style

from euporie.box import DoubleBorder, SquareBorder
from euporie.formatted_text.utils import (
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
    from typing import Any, Callable, Optional, Type

    from markdown_it.token import Token  # type: ignore
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples

markdown_parser: "Optional[MarkdownIt]" = None
try:
    from markdown_it import MarkdownIt  # type: ignore
except ModuleNotFoundError:
    warn("The markdown parser requires `markdown-it-py` to be installed")
else:
    markdown_parser = (
        MarkdownIt().enable("linkify").enable("table").enable("strikethrough")
    )

try:
    import mdit_py_plugins  # type: ignore # noqa F401
except ModuleNotFoundError:
    pass
else:
    from mdit_py_plugins.amsmath import amsmath_plugin  # type: ignore
    from mdit_py_plugins.dollarmath import dollarmath_plugin  # type: ignore
    from mdit_py_plugins.texmath import texmath_plugin  # type: ignore

    if markdown_parser is not None:
        markdown_parser.use(texmath_plugin)
        markdown_parser.use(dollarmath_plugin)
        markdown_parser.use(amsmath_plugin)

DEFAULT_MD_STYLE = Style.from_dict(
    {
        "md": "",
        "md.h1": "bold underline",
        "md.h1.border": "fg:ansiyellow nounderline",
        "md.h2": "bold",
        "md.h2.border": "fg:grey nobold",
        "md.h3": "bold",
        "md.h4": "bold italic",
        "md.h5": "underline",
        "md.h6": "italic",
        "md.code.inline": "bg:#333",
        "md.strong": "bold",
        "md.em": "italic",
        "md.hr": "fg:ansired",
        "md.bullet": "fg:ansiyellow",
        "md.blockquote": "fg:ansipurple",
        "md.blockquote.margin": "fg:grey",
        "md.th": "bold",
        "md.a": "underline fg:ansibrightblue",
        "md.s": "strike",
        "md.img": "bg:cyan fg:black",
        "md.img.border": "fg:cyan bg:default",
    }
)

_SIDES = {
    "left": WindowAlign.LEFT,
    "right": WindowAlign.RIGHT,
    "center": WindowAlign.CENTER,
}


def h1(ft: "StyleAndTextTuples", width: "int", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats a top-level heading wrapped and centered with a full width double border."""
    ft = wrap(ft, width - 4)
    ft = align(WindowAlign.CENTER, ft, width=width - 4)
    ft = add_border(ft, width, style="class:md.h1.border", border=DoubleBorder)
    ft.append(("", "\n\n"))
    return ft


def h2(ft: "StyleAndTextTuples", width: "int", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats a 2nd-level headding wrapped and centered with a double border."""
    ft = wrap(ft, width=width - 4)
    ft = align(WindowAlign.CENTER, ft)
    ft = add_border(ft, style="class:md.h2.border", border=SquareBorder)
    ft = align(WindowAlign.CENTER, ft, width=width)
    ft.append(("", "\n\n"))
    return ft


def h(ft: "StyleAndTextTuples", width: "int", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats headings wrapped and centeredr."""
    ft = wrap(ft, width)
    ft = align(WindowAlign.CENTER, ft, width=width)
    ft.append(("", "\n\n"))
    return ft


def p(
    ft: "StyleAndTextTuples", width: "int", hidden: "bool", **kwargs: "Any"
) -> "StyleAndTextTuples":
    """Formats paragraphs wrapped."""
    ft = wrap(ft, width)
    ft.append(("", "\n" if hidden else "\n\n"))
    return ft


def ul(ft: "StyleAndTextTuples", width: "int", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats unordered lists."""
    ft.append(("", "\n"))
    return ft


def li(ft: "StyleAndTextTuples", width: "int", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats list items."""
    ft = strip(ft)
    ft = indent(ft, margin="   ", style="class:md.bullet")
    ft[0] = (ft[0][0], " • ")
    ft.append(("", "\n"))
    return ft


def hr(ft: "StyleAndTextTuples", width: "int", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats horizontal rules."""
    ft = [
        ("class:md.hr", "─" * width),
        ("", "\n\n"),
    ]
    return ft


def br(ft: "StyleAndTextTuples", **kwargs: "Any") -> "StyleAndTextTuples":
    """Formats line breaks."""
    return [("", "\n")]


def blockquote(
    ft: "StyleAndTextTuples",
    width: "int",
    info: "str" = "",
    block: "bool" = False,
    **kwargs: "Any",
) -> "StyleAndTextTuples":
    """Formats blockquotes with a solid left margin."""
    ft = strip(ft)
    ft = indent(ft, margin="▌ ", style="class:md.blockquote.margin")
    ft.append(("", "\n\n"))
    return ft


def code(
    ft: "StyleAndTextTuples",
    width: "int",
    info: "str" = "",
    block: "bool" = False,
    **kwargs: "Any",
) -> "StyleAndTextTuples":
    """Formats inline code, and lexes and formats code blocks with a border."""
    if block:
        ft = strip(ft, left=False, right=True, char="\n")
        ft = lex(ft, lexer_name=info)
        ft = align(WindowAlign.LEFT, ft, width - 4)
        ft = add_border(ft, width, style="class:md.code.border", border=SquareBorder)
        ft.append(("", "\n\n"))
    else:
        ft = apply_style(ft, style="class:md.code.inline")
    return ft


def math(
    ft: "StyleAndTextTuples", width: "int", block: "bool", **kwargs: "Any"
) -> "StyleAndTextTuples":
    """Formats inline maths, and quotes math blocks."""
    if block:
        return blockquote(ft, width - 2, **kwargs)
    else:
        return ft


def a(
    ft: "StyleAndTextTuples", attrs: "dict[str, str]", **kwargs: "Any"
) -> "StyleAndTextTuples":
    """Formats hyperlinks and adds link escape sequences."""
    result: "StyleAndTextTuples" = []
    href = attrs.get("href")
    if href:
        result.append(("[ZeroWidthEscape]", f"\x1b]8;;{href}\x1b\\"))
    result += ft
    if href:
        result.append(("[ZeroWidthEscape]", "\x1b]8;;\x1b\\"))
    return result


def img(
    ft: "StyleAndTextTuples",
    width: "int",
    attrs: "dict[str, str]",
    block: "bool",
    left: "int",
    border: "bool" = False,
    bounds: "tuple[str, str]" = ("", ""),  # Semi-circle blocks
    **kwargs: "Any",
) -> "StyleAndTextTuples":
    """Formats image titles."""
    if not to_plain_text(ft):
        # Add fallback text if there is no image title
        title = attrs.get("alt")
        # Try getting the filename
        if not title and not (src := attrs.get("src", "")).startswith("data:"):
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
TAG_RULES: "dict[str, Callable]" = {
    "h1": h1,
    "h2": h2,
    "h3": h,
    "h4": h,
    "h5": h,
    "h6": h,
    "p": p,
    "ul": ul,
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
        markup: "str",
        width: "Optional[int]" = None,
        strip_trailing_lines: "bool" = True,
    ) -> "None":
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
        self, tokens: "list[Token]", width: "int" = 80, left: "int" = 0
    ) -> "StyleAndTextTuples":
        """Renders a list of parsed markdown tokens.

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
            if token.type == "inline":
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

                # If there is a special method for rendering the block,
                # used that
                if token.tag == "table":
                    ft += self.render_table(
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
        tokens: "list[Token]",
        width: "int",
        left: "int" = 0,
    ) -> "StyleAndTextTuples":
        """Renders a list of parsed markdown tokens representing a block element.

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
        if inset := TAG_INSETS.get(token.tag):
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
        if rule := TAG_RULES.get(token.tag):
            ft = rule(
                ft,
                width=width,
                info=token.info,
                block=token.block,
                attrs=token.attrs,
                hidden=token.hidden,
                left=left,
            )

        return ft

    def render_table(
        self,
        tokens: "list[Token]",
        width: "int",
        left: "int" = 0,
        border: "Type[SquareBorder]" = SquareBorder,
    ) -> "StyleAndTextTuples":
        """Renders a list of parsed markdown tokens representing a table element.

        Args:
            tokens: The list of parsed tokens to render
            width: The width at which to render the tokens
            left: The position on the current line at which to render the output - used
                to indent subsequent lines when rendering inline blocks like images
            border: The border style to use to render the table

        Returns:
            Formatted text

        """
        ft: "StyleAndTextTuples" = []
        # Stack the tokens in the shape of the table
        cell_tokens: "list[list[Token]]" = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == "tr_open":
                cell_tokens.append([])
            elif token.type in ("th_open", "td_open"):
                for j, token in enumerate(tokens[i:]):
                    if token.type in ("th_close", "td_close"):
                        cell_tokens[-1].append(tokens[i : i + j + 1])
                        break
                i += j
            i += 1

        def _render_token(
            tokens: "list[Token]", width: "Optional[int]" = None
        ) -> "StyleAndTextTuples":
            """Render a token with correct alignment."""
            side = "left"
            # Check CSS for text alignment
            for style_str in tokens[0].attrs.get("style", "").split(";"):
                if ":" in style_str:
                    key, value = style_str.strip().split(":", 1)
                    if key.strip() == "text-align":
                        side = value
            # Render with a very long line length if we do not have a width
            ft = self.render(tokens, width=width or 999999)
            # If we do have a width, wrap and apply the alignment
            if width:
                ft = wrap(ft, width)
                ft = align(_SIDES[side], ft, width)
            return ft

        # Find the naive widths of each cell
        cell_renders: "list[list[StyleAndTextTuples]]" = []
        cell_widths: "list[list[int]]" = []
        for row in cell_tokens:
            cell_widths.append([])
            cell_renders.append([])
            for token in row:
                rendered = _render_token(token)
                cell_renders[-1].append(rendered)
                cell_widths[-1].append(fragment_list_width(rendered))

        # Calculate row and column widths, accounting for broders
        col_widths = [
            max([row[i] for row in cell_widths]) for i in range(len(cell_widths[0]))
        ]

        # Adjust widths and potentially re-render cells
        # Reduce biggest cells until we fit in width
        while sum(col_widths) + 3 * (len(col_widths) - 1) + 4 > width:
            idxmax = max(enumerate(col_widths), key=lambda x: x[1])[0]
            col_widths[idxmax] -= 1
        # Re-render changed cells
        for i, row_widths in enumerate(cell_widths):
            for j, new_width in enumerate(col_widths):
                if row_widths[j] != new_width:
                    cell_renders[i][j] = _render_token(
                        cell_tokens[i][j], width=new_width
                    )

        # Justify cell contents
        for i, row in enumerate(cell_renders):
            for j, cell in enumerate(row):
                cell_renders[i][j] = align(WindowAlign.LEFT, cell, width=col_widths[j])

        # Render table
        style = "class:md.table.border"

        def _draw_add_border(left: "str", split: "str", right: "str") -> "None":
            ft.append((style, left + border.HORIZONTAL))
            for col_width in col_widths:
                ft.append((style, border.HORIZONTAL * col_width))
                ft.append((style, border.HORIZONTAL + split + border.HORIZONTAL))
            ft.pop()
            ft.append((style, border.HORIZONTAL + right + "\n"))

        # Draw top border
        _draw_add_border(border.TOP_LEFT, border.SPLIT_TOP, border.TOP_RIGHT)
        # Draw each row
        for i, row in enumerate(cell_renders):
            for row_lines in zip_longest(*map(split_lines, row)):
                # Draw each line in each row
                ft.append((style, border.VERTICAL + " "))
                for j, line in enumerate(row_lines):
                    if line is None:
                        line = [("", " " * col_widths[j])]
                    ft += line
                    ft.append((style, " " + border.VERTICAL + " "))
                ft.pop()
                ft.append((style, " " + border.VERTICAL + "\n"))
            # Draw border between rows
            if i < len(cell_renders) - 1:
                _draw_add_border(border.SPLIT_LEFT, border.CROSS, border.SPLIT_RIGHT)
        # Draw bottom border
        _draw_add_border(border.BOTTOM_LEFT, border.SPLIT_BOTTOM, border.BOTTOM_RIGHT)

        ft.append(("", "\n"))
        return ft

    def __pt_formatted_text__(self) -> "StyleAndTextTuples":
        """Formatted text magic method."""
        return self.formatted_text


if __name__ == "__main__":
    import sys

    from prompt_toolkit.shortcuts.utils import print_formatted_text

    with open(sys.argv[1]) as f:
        print_formatted_text(Markdown(f.read()), style=DEFAULT_MD_STYLE)
