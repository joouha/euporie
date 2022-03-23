"""Contains a markdown to formatted text parser."""

from itertools import zip_longest
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from mdit_py_plugins.amsmath import amsmath_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.texmath import texmath_plugin
from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_width, split_lines
from prompt_toolkit.styles import Style

from euporie.box import DoubleBorder, RoundBorder, SquareBorder
from euporie.formatted_text.ansi import ANSI
from euporie.formatted_text.util import (
    add_border,
    align,
    apply_style,
    indent,
    last_line_length,
    lex,
    strip,
    wrap,
)
from euporie.terminal import tmuxify

if TYPE_CHECKING:
    from markdown_it.token import Token, Optional

_MarkdownItParser = (
    MarkdownIt()
    .enable("linkify")
    .enable("table")
    .use(texmath_plugin)
    .use(dollarmath_plugin)
    .use(amsmath_plugin)
)

DEFAULT_MD_STYLE = Style.from_dict(
    {
        "md": "",
        "md.h1": "bold",
        "md.h1.border": "fg:ansiyellow",
        "md.h2": "bold underline",
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


def h1(ft, width, **kwargs):
    ft = wrap(ft, width - 4)
    ft = align("center", ft, width=width - 4)
    ft = add_border(ft, width, style="class:md.h1.border", border=DoubleBorder)
    ft.append(("", "\n\n"))
    return ft


def h(ft, width, **kwargs):
    ft = wrap(ft, width)
    ft = align("center", ft, width=width)
    ft.append(("", "\n\n"))
    return ft


def p(ft, width, hidden, **kwargs):
    ft = wrap(ft, width)
    ft.append(("", "\n" if hidden else "\n\n"))
    return ft


def ul(ft, width, **kwargs):
    ft.append(("", "\n"))
    return ft


def li(ft, width, **kwargs):
    ft = strip(ft)
    ft = indent(ft, margin="   ", style="class:md.bullet")
    ft[0] = (ft[0][0], " • ")
    ft.append(("", "\n"))
    return ft


def hr(ft, width, **kwargs):
    ft = [
        ("class:md.hr", "─" * width),
        ("", "\n\n"),
    ]
    return ft


def br(ft, **kwargs):
    return (("", "\n"),)


def blockquote(ft, width, info="", block=False, **kwargs):
    ft = strip(ft)
    ft = indent(ft, margin="▌ ", style="class:md.blockquote.margin")
    ft.append(("", "\n\n"))
    return ft


def code(ft, width, info="", block=False, **kwargs):
    if block:
        ft = strip(ft, left=False, right=True, char="\n")
        ft = lex(ft, lexer_name=info)
        ft = align("left", ft, width - 4)
        ft = add_border(ft, width, style="class:md.code.border", border=SquareBorder)
        ft.append(("", "\n\n"))
    else:
        ft = apply_style(ft, style="class:md.code.inline")
    return ft


def math(ft, width, block, **kwargs):
    return blockquote(ft, width - 2, **kwargs)


def a(ft, attrs, **kwargs):
    result = []
    href = attrs.get("href")
    if href:
        result.append(("[ZeroWidthEscape]", tmuxify(f"\x1b]8;;{href}\x1b\\")))
    result += ft
    if href:
        result.append(("[ZeroWidthEscape]", tmuxify("\x1b]8;;\x1b\\")))
    return result


def img(ft, width, attrs, block, left, border: "bool" = False, bounds=("", ""), **kwargs):
    result = []
    result = [("class:md.img", "🖼️  "), *ft]
    result = apply_style(result, style="class:md.img")
    result = [
        ("class:md.img.border", f"{bounds[0]}"),
        *result,
        ("class:md.img.border", f"{bounds[1]}"),
    ]
    return result


class Markdown:

    tag_rules = {
        "h1": h1,
        "h2": h,
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

    tag_insets = {
        "li": 3,
        "blockquote": 2,
    }

    def __init__(self, markup: "str", width: "Optional[int]" = None, strip_trailing_lines: "bool" = True) -> "None":
        self.markup = markup
        self.width = width or get_app_session().output.get_size().columns
        self.strip_trailing_lines = strip_trailing_lines

        self.formatted_text = self.render(
            tokens=_MarkdownItParser.parse(self.markup),
            width=self.width,
        )
        if strip_trailing_lines:
            self.formatted_text = strip(
                self.formatted_text,
                left=False,
                char="\n",
            )

    def render(self, tokens, width: "int" = 80, left: "int" = 0):
        ft = []

        i = 0
        while i < len(tokens):
            token = tokens[i]
            tag = token.tag

            # If this is an inline block, render it's children
            if token.type == "inline":
                ft += self.render(token.children, width)
                i += 1

            # Otherwise gather the tokens in the current block
            else:
                nest = 0
                for j, token in enumerate(tokens[i:]):
                    nest += token.nesting
                    if nest == 0:
                        break

                # If there is a special method for rendering the block,
                # used that
                if token.tag == "table":
                    ft += self.render_table(
                        tokens[i : i + j + 1], width=width, left=last_line_length(ft)
                    )

                # Otherwize all other blocks are rendered in the same way
                else:
                    ft += self.render_block(
                        tokens[i : i + j + 1], width=width, left=last_line_length(ft)
                    )

                i += j + 1

        return ft

    def render_block(self, tokens, width: "int", border=SquareBorder, left: "int" = 0):
        ft = []
        token = tokens[0]

        # Restrict width if necessary
        if inset := self.tag_insets.get(token.tag):
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
        if rule := self.tag_rules.get(token.tag):
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

    def render_table(self, tokens, width: "int", border=SquareBorder, left: "int" = 0):
        ft = []
        # Stack the tokens in the shape of the table
        cell_tokens = []
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

        def _render_token(tokens, width: "Optional[int]" = None):
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
                ft = align(side, ft, width)
            return ft

        # Find the naive widths of each cell
        cell_renders = []
        cell_widths = []
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
                cell_renders[i][j] = align("left", cell, width=col_widths[j])

        # Render table
        style = "class:md.table.border"

        def _draw_add_border(left, split, right):
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
        return self.formatted_text


if __name__ == "__main__":
    import sys

    from prompt_toolkit.shortcuts.utils import print_formatted_text

    with open(sys.argv[1]) as f:
        print_formatted_text(Markdown(f.read()), style=DEFAULT_MD_STYLE)
