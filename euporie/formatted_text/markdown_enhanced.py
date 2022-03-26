"""Add enhanced display capabilities the the markdown renderer."""

from math import ceil
from typing import TYPE_CHECKING

from euporie.convert.base import convert
from euporie.formatted_text import markdown
from euporie.formatted_text.utils import FormattedTextAlign, align, indent, strip
from euporie.output.container import data_pixel_size, pixels_to_cell_size
from euporie.terminal import tmuxify
from euporie.url import load_url

if TYPE_CHECKING:
    from markdown_it.token import Token
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples


MARKDOWN_STYLE = [
    ("md.h1", "bold underline"),
    ("md.h1.border", "fg:ansiyellow nounderline"),
    ("md.h2", "bold"),
    ("md.h2.border", "fg:grey nobold"),
    ("md.h3", "bold"),
    ("md.h4", "bold italic"),
    ("md.h5", "underline"),
    ("md.h6", "italic"),
    ("md.code.inline", "bg:#333"),
    ("md.strong", "bold"),
    ("md.em", "italic"),
    ("md.hr", "fg:ansired"),
    ("md.ul.margin", "fg:ansiyellow"),
    ("md.ol.margin", "fg:ansicyan"),
    ("md.blockquote", "fg:ansipurple"),
    ("md.blockquote.margin", "fg:grey"),
    ("md.th", "bold"),
    ("md.a", "underline fg:ansibrightblue"),
    ("md.s", "strike"),
    ("md.img", "bg:cyan fg:black"),
    ("md.img.border", "fg:cyan bg:default"),
]


def math_enhanced(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
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
    if token.block:
        result = align(FormattedTextAlign.CENTER, result, width=width)
        result.append(("", "\n\n"))
    return result


def img_enhanced(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Display images rendered as ANSI art."""
    result: "StyleAndTextTuples" = []

    if data := load_url(str(token.attrs.get("src", ""))):
        # Display it graphically
        cols, aspect = pixels_to_cell_size(*data_pixel_size(data, format_="png"))
        # Manially set a value if we don't have one
        cols = cols or 20
        aspect = aspect or 0.5
        # Scale down the image to fit to width
        cols = min(width, cols)
        rows = ceil(cols * aspect)
        # Convert the image to formatted-text
        result = convert(
            data,
            "png",
            "formatted_text",
            cols=cols,
            rows=rows,
        )
        # Remove trailing new-lines
        result = strip(result, char="\n")
        # Optionally add a border
        # result = add_border(
        # result,
        # border=RoundBorder,
        # style="class:md.img.border",
        # )
        # Indent for line continuation as images are inline
        result = indent(result, " " * left, skip_first=True)

    # Fallback to formatting the title if we still don't have image formatted-text data
    if not result:
        result = markdown.img(ft, width, left, token)

    return result


def a_enhanced(
    ft: "StyleAndTextTuples",
    width: int,
    left: int,
    token: "Token",
) -> "StyleAndTextTuples":
    """Adds tmux-passthrough to hyperlinks if in tmux."""
    result: "StyleAndTextTuples" = []
    for fragment in markdown.a(ft, width, left, token):
        if "[ZeroWidthEscape]" in fragment[0]:
            result.append((fragment[0], tmuxify(fragment[1])))
        else:
            result.append(fragment)
    return result


def enable_enchanced_markdown() -> "None":
    """Enables euporie-specific markdown features."""
    if markdown.markdown_parser is not None:
        # Override formatters
        markdown.TAG_RULES["math"] = math_enhanced
        markdown.TAG_RULES["img"] = img_enhanced
        markdown.TAG_RULES["a"] = a_enhanced


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.current import set_app
    from prompt_toolkit.output.color_depth import ColorDepth
    from prompt_toolkit.shortcuts.utils import print_formatted_text
    from prompt_toolkit.styles import Style

    from euporie.app.tui import TuiApp

    enable_enchanced_markdown()
    app = TuiApp()
    with set_app(app):
        app.update_style()
        with open(sys.argv[1]) as f:
            print_formatted_text(
                markdown.Markdown(f.read()),
                style=Style(MARKDOWN_STYLE),
                color_depth=ColorDepth.DEPTH_24_BIT,
            )
