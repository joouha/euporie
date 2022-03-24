"""Add enhanced display capabilities the the markdown renderer."""

from math import ceil
from typing import TYPE_CHECKING

from mdit_py_plugins.amsmath import amsmath_plugin  # type: ignore
from mdit_py_plugins.dollarmath import dollarmath_plugin  # type: ignore
from mdit_py_plugins.texmath import texmath_plugin  # type: ignore
from prompt_toolkit.layout.containers import WindowAlign

from euporie.box import RoundBorder
from euporie.convert.base import convert
from euporie.formatted_text import markdown
from euporie.formatted_text.util import add_border, align, indent, strip
from euporie.output.container import get_dims
from euporie.terminal import tmuxify
from euporie.url import load_url

if TYPE_CHECKING:
    from typing import Any

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples


def math_enhanced(
    ft: "StyleAndTextTuples", width: "int", block: "bool", **kwargs: "Any"
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
    if block:
        result = align(WindowAlign.CENTER, result, width=width)
        result.append(("", "\n\n"))
    return result


def img_enhanced(
    ft: "StyleAndTextTuples",
    width: "int",
    attrs: "dict[str, str]",
    block: "bool",
    left: "int",
    border: "bool" = False,
    **kwargs: "Any",
) -> "StyleAndTextTuples":
    """Display images rendered as ANSI art."""
    result: "StyleAndTextTuples" = []

    if data := load_url(attrs.get("src", "")):
        # Display it graphically
        cols, aspect = get_dims(data, format_="png")
        cols = cols or 50
        aspect = aspect or 0.5
        cols = min(width, cols)
        rows = ceil(cols * aspect)
        result = convert(
            data,
            "png",
            "formatted_text",
            cols=cols,
            rows=rows,
        )
        result = strip(result, char="\n")
        if border:
            result = add_border(
                result,
                border=RoundBorder,
                style="class:md.img.border",
            )
        result = indent(result, " " * left, skip_first=True)

    if not result:
        result = markdown.img(ft, width, attrs, block, left, border, **kwargs)

    return result


def a_enhanced(
    ft: "StyleAndTextTuples", attrs: "dict[str, str]", **kwargs: "Any"
) -> "StyleAndTextTuples":
    """Adds tmux-passthrough to hyperlinks if in tmux."""
    result: "StyleAndTextTuples" = []
    for fragment in markdown.a(ft, attrs, **kwargs):
        if "[ZeroWidthEscape]" in fragment[0]:
            result.append((fragment[0], tmuxify(fragment[1])))
        else:
            result.append(fragment)
    return result


def enable_enchanced_markdown() -> "None":
    """Enables euporie-specific markdown features."""
    if markdown.markdown_parser is not None:
        # Enable plugins
        markdown.markdown_parser.use(texmath_plugin)
        markdown.markdown_parser.use(dollarmath_plugin)
        markdown.markdown_parser.use(amsmath_plugin)
        # Override formatters
        markdown.TAG_RULES["math"] = math_enhanced
        markdown.TAG_RULES["img"] = img_enhanced
        markdown.TAG_RULES["a"] = a_enhanced


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.current import set_app
    from prompt_toolkit.output.color_depth import ColorDepth
    from prompt_toolkit.shortcuts.utils import print_formatted_text

    from euporie.app.tui import TuiApp

    enable_enchanced_markdown()
    app = TuiApp()
    with set_app(app):
        app.update_style()
        with open(sys.argv[1]) as f:
            print_formatted_text(
                markdown.Markdown(f.read()),
                style=markdown.DEFAULT_MD_STYLE,
                color_depth=ColorDepth.DEPTH_24_BIT,
            )