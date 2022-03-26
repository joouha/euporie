"""Contains functions which convert data to formatted ansi text."""

from __future__ import annotations

import logging
from functools import partial
from math import ceil
from typing import TYPE_CHECKING

from euporie.app.current import get_base_app as get_app
from euporie.convert.base import register
from euporie.convert.formats.common import chafa_convert
from euporie.convert.formats.pil import set_background
from euporie.convert.util import call_subproc, commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Any, Optional

    from PIL import Image  # type: ignore
    from rich.console import RenderableType

log = logging.getLogger(__name__)


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("w3m"),
)
def html_to_ansi_w3m(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`w3m`."""
    cmd: "list[Any]" = ["w3m", "-T", "text/html"]
    if width is not None:
        cmd += ["-cols", str(width)]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("elinks"),
)
def html_to_ansi_elinks(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`elinks`."""
    cmd: "list[Any]" = [
        "elinks",
        "-dump",
        "-dump-color-mode",
        "3",
        "-no-numbering",
        "-force-html",
        "-no-references",
    ]
    if width is not None:
        cmd += ["-dump-width", width]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("lynx"),
)
def html_to_ansi_lynx(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`lynx`."""
    cmd: "list[Any]" = ["lynx", "-dump", "-stdin"]
    if width is not None:
        cmd += [f"-width={width}"]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("links"),
)
def html_to_ansi_links(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts HTML text to formatted ANSI using :command:`links`."""
    cmd: "list[Any]" = ["links", "-dump"]
    if width is not None:
        cmd += ["-width", width]
    return call_subproc(data.encode(), cmd, use_tempfile=True).decode()


@register(
    from_="html",
    to="ansi",
    weight=4,
)
def html_to_ansi_py_htmlparser(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert HTML tables to ANSI text using :py:mod:`HTMLParser`."""
    import io
    import re
    from html.parser import HTMLParser

    class HTMLStripper(HTMLParser):
        """Very basic HTML parser which strips style and script tags."""

        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = io.StringIO()
            self.skip = False
            self.skip_tags = ("script", "style")

        def handle_starttag(
            self, tag: "str", attrs: "list[tuple[str, Optional[str]]]"
        ) -> "None":
            if tag in self.skip_tags:
                self.skip = True

        def handle_endtag(self, tag: "str") -> "None":
            if tag in self.skip_tags:
                self.skip = False

        def handle_data(self, d: "str") -> "None":
            if not self.skip:
                self.text.write(d)

        def get_data(self) -> "str":
            return self.text.getvalue()

    stripper = HTMLStripper()
    stripper.feed(data)
    output = stripper.get_data()
    # Strip lines
    output = "\n".join([x.strip() for x in output.strip().split("\n")])
    # Remove empty paragraphs
    output = re.sub("\n\n\n+", "\n\n", output)
    return output


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("flatlatex"),
)
def latex_to_ansi_py_flatlatex(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert LaTeX to ANSI using :py:mod:`flatlatex`."""
    import flatlatex  # type: ignore

    return flatlatex.converter().convert(data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("pylatexenc"),
)
def latex_to_ansi_py_pylatexenc(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert LaTeX to ANSI using :py:mod:`flatlatex`."""
    from pylatexenc.latex2text import LatexNodes2Text  # type: ignore

    return LatexNodes2Text().latex_to_text(data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("sympy", "antlr4"),
)
def latex_to_ansi_py_sympy(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert LaTeX to ANSI using :py:mod:`sympy`."""
    from sympy import pretty  # type: ignore
    from sympy.parsing.latex import parse_latex  # type: ignore
    from sympy.parsing.latex.errors import LaTeXParsingError  # type: ignore

    from euporie.log import stdout_to_log

    with stdout_to_log(log):
        try:
            parsed = parse_latex(data.strip().strip("$").strip())
        except LaTeXParsingError:
            parsed = data
    return pretty(parsed)


@register(
    from_="pil",
    to="ansi",
    filter_=have_modules("timg"),
)
def pil_to_ansi_py_timg(
    data: "Image",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert a PIL image to ANSI text using :py:mod:`timg`."""
    import timg  # type: ignore

    w, h = data.size
    if cols is not None:
        data = data.resize((cols, ceil(cols / w * h)))
    bg = bg or get_app().color_palette["bg"][-1]
    if bg:
        data = set_background(data, bg)
    data = set_background(data, bg)
    return timg.Ansi24HblockMethod(data).to_string()


@register(
    from_="pil",
    to="ansi",
    filter_=have_modules("img2unicode"),
)
def pil_to_ansi_py_img2unicode(
    data: "Image",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert a PIL image to ANSI text using :py:mod:`img2unicode`."""
    import io

    from img2unicode import FastQuadDualOptimizer, Renderer  # type: ignore

    output = io.StringIO()
    Renderer(FastQuadDualOptimizer(), max_w=cols, max_h=rows).render_terminal(
        data, output
    )
    output.seek(0)
    return output.read()


register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="ansi",
    filter_=commands_exist("chafa"),
)(partial(chafa_convert, "symbols"))


@register(
    from_=("png", "jpeg", "pdf"),
    to="ansi",
    filter_=commands_exist("timg") & ~have_modules("timg"),
)
def image_to_ansi_timg(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts image data to ANSI text using :command:`timg`."""
    cmd: "list[Any]" = ["timg"]
    if cols is not None and rows is not None:
        cmd += [f"-g{cols}x{cols}"]
    cmd += ["--compress", "-pq", "--threads=-1", "-"]
    return call_subproc(data, cmd).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("catimg"),
)
def image_to_ansi_catimg(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts image data to ANSI text using :command:`catimg`."""
    cmd: "list[Any]" = ["catimg"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols * 2]
    cmd += ["-"]
    return call_subproc(data, cmd).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("icat"),
)
def image_to_ansi_icat(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts image data to ANSI text using :command:`icat`."""
    cmd: "list[Any]" = ["icat"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["--mode", "24bit", "-"]
    return call_subproc(data, cmd).decode()


@register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="ansi",
    filter_=commands_exist("tiv"),
)
def image_to_ansi_tiv(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts image data to ANSI text using :command:`tiv`."""
    cmd: "list[Any]" = ["tiv"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols, "-h", rows]
    return call_subproc(data, cmd, use_tempfile=True).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("viu"),
)
def image_to_ansi_viu(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts image data to ANSI text using :command:`viu`."""
    cmd: "list[Any]" = ["viu"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["-s", "-"]
    return call_subproc(data, cmd).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("jp2a"),
)
def image_to_ansi_jp2a(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts image data to ANSI text using :command:`jp2a`."""
    cmd: "list[Any]" = ["jp2a", "--color"]
    if cols is not None and rows is not None:
        cmd += [f"--height={rows}"]
    cmd += ["-"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("img2txt"),
)
def png_to_ansi_img2txt(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`img2txt`."""
    cmd: "list[Any]" = ["img2txt"]
    if cols is not None and rows is not None:
        cmd += ["-W", cols, "-H", rows]
    return call_subproc(data, cmd, use_tempfile=True).decode()


@register(from_=("png", "jpeg", "svg"), to="ansi", filter_=True, weight=2)
def png_to_ansi_py_placeholder(
    data: "bytes",
    cols: "int" = 7,
    rows: "int" = 3,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Draw placeholder ANSI text."""
    from euporie.box import RoundBorder as B

    lines = []
    lines.append(B.TOP_LEFT + B.HORIZONTAL * max(5, (cols - 2)) + B.TOP_RIGHT)
    lines += [B.VERTICAL + (" " * (cols - 2)) + B.VERTICAL] * ((rows - 3) // 2)
    lines.append(B.VERTICAL + "Image".center(cols - 2) + B.VERTICAL)
    lines += [B.VERTICAL + " " * (cols - 2) + B.VERTICAL] * (
        (rows - 3) - (rows - 3) // 2
    )
    lines.append(B.BOTTOM_LEFT + B.HORIZONTAL * max(5, (cols - 2)) + B.BOTTOM_RIGHT)
    return "\n".join(lines)


@register(
    from_="rich",
    to="ansi",
    filter_=have_modules("rich"),
)
def markdown_to_rich_py(
    data: "RenderableType",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts rich objects to formatted ANSI text."""
    import rich

    console = rich.get_console()
    options = console.options
    if width is not None:
        options = options.update(max_width=width)
    buffer = console.render(data, options)
    rendered_lines = console._render_buffer(buffer)
    return rendered_lines
