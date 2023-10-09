"""Contain functions which convert data to formatted ansi text."""

from __future__ import annotations

import logging
from functools import partial
from math import ceil
from typing import TYPE_CHECKING

from euporie.core.convert.core import register
from euporie.core.convert.formats.common import chafa_convert_cmd, chafa_convert_py
from euporie.core.convert.formats.pil import set_background
from euporie.core.convert.utils import call_subproc, commands_exist, have_modules
from euporie.core.current import get_app

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from PIL.Image import Image as PilImage
    from rich.console import RenderableType

log = logging.getLogger(__name__)


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("w3m"),
)
async def html_to_ansi_w3m(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert HTML text to formatted ANSI using :command:`w3m`."""
    cmd: list[Any] = ["w3m", "-T", "text/html"]
    if width is not None:
        cmd += ["-cols", str(width)]
    return (await call_subproc(data.encode(), cmd)).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("elinks"),
)
async def html_to_ansi_elinks(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert HTML text to formatted ANSI using :command:`elinks`."""
    cmd: list[Any] = [
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
    return (await call_subproc(data.encode(), cmd)).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("lynx"),
)
async def html_to_ansi_lynx(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert HTML text to formatted ANSI using :command:`lynx`."""
    cmd: list[Any] = ["lynx", "-dump", "-stdin"]
    if width is not None:
        cmd += [f"-width={width}"]
    return (await call_subproc(data.encode(), cmd)).decode()


@register(
    from_="html",
    to="ansi",
    filter_=commands_exist("links"),
)
async def html_to_ansi_links(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert HTML text to formatted ANSI using :command:`links`."""
    cmd: list[Any] = ["links", "-dump"]
    if width is not None:
        cmd += ["-width", width]
    return (await call_subproc(data.encode(), cmd, use_tempfile=True)).decode()


@register(
    from_="html",
    to="ansi",
    weight=4,
)
async def html_to_ansi_py_htmlparser(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert HTML tables to ANSI text using :py:mod:`HTMLParser`."""
    import io
    import re
    from html.parser import HTMLParser

    class HTMLStripper(HTMLParser):
        """Very basic HTML parser which strips style and script tags."""

        def __init__(self) -> None:
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = io.StringIO()
            self.skip = False
            self.skip_tags = ("script", "style")

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            if tag in self.skip_tags:
                self.skip = True

        def handle_endtag(self, tag: str) -> None:
            if tag in self.skip_tags:
                self.skip = False

        def handle_data(self, d: str) -> None:
            if not self.skip:
                self.text.write(d)

        def get_data(self) -> str:
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
    filter_=have_modules("flatlatex.latexfuntypes"),
)
async def latex_to_ansi_py_flatlatex(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert LaTeX to ANSI using :py:mod:`flatlatex`."""
    import flatlatex

    return flatlatex.converter().convert(data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("pylatexenc"),
)
async def latex_to_ansi_py_pylatexenc(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert LaTeX to ANSI using :py:mod:`pylatexenc`."""
    from pylatexenc.latex2text import LatexNodes2Text

    return LatexNodes2Text().latex_to_text(data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("sympy", "antlr4"),
)
async def latex_to_ansi_py_sympy(
    data: str,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert LaTeX to ANSI using :py:mod:`sympy`."""
    from sympy import pretty
    from sympy.parsing.latex import parse_latex
    from sympy.parsing.latex.errors import LaTeXParsingError

    from euporie.core.log import stdout_to_log

    with stdout_to_log(log):
        try:
            parsed = parse_latex(data.strip().strip("$").strip())
        except LaTeXParsingError:
            parsed = data
    return pretty(parsed)


@register(from_="pil", to="ansi", filter_=have_modules("timg"), weight=2)
async def pil_to_ansi_py_timg(
    data: PilImage,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert a PIL image to ANSI text using :py:mod:`timg`."""
    import timg

    px, py = get_app().term_info.cell_size_px

    # Calculate rows based on image aspect ratio
    w, h = data.size
    if rows is None and cols is not None:
        w, h = data.size
        rows = ceil(cols / w * h)
    elif cols is None and rows is not None:
        w, h = data.size
        cols = ceil(rows / h * w)
    elif rows is None and cols is None:
        cols = ceil(w / px)
        rows = ceil(h / py)
    assert rows is not None and cols is not None

    # `timg` assumes a 2x1 terminal cell aspect ratio, so we correct for while
    # resizing the image
    data = data.resize((cols, ceil(rows * 2 * (px / py) / 0.5)))

    bg = bg or get_app().color_palette.bg.base_hex
    if bg:
        data = set_background(data, bg)
    data = set_background(data, bg)
    return timg.Ansi24HblockMethod(data).to_string()


@register(
    from_="pil",
    to="ansi",
    filter_=have_modules("img2unicode"),
)
async def pil_to_ansi_py_img2unicode(
    data: PilImage,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert a PIL image to ANSI text using :py:mod:`img2unicode`."""
    import io

    from img2unicode import FastQuadDualOptimizer, Renderer

    output = io.StringIO()
    Renderer(FastQuadDualOptimizer(), max_w=cols, max_h=rows).render_terminal(
        data, output
    )
    output.seek(0)
    return output.read()


register(
    from_=("png", "jpeg", "svg", "pdf", "gif"),
    to="ansi",
    filter_=commands_exist("chafa"),
)(partial(chafa_convert_cmd, "symbols"))


register(from_=("pil"), to="ansi", filter_=have_modules("chafa"))(
    partial(chafa_convert_py, "symbols")
)


@register(
    from_=("png", "jpeg", "pdf", "gif"),
    to="ansi",
    filter_=commands_exist("timg") & ~have_modules("timg"),
)
async def image_to_ansi_timg(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert image data to ANSI text using :command:`timg`."""
    cmd: list[Any] = ["timg"]
    if cols is not None and rows is not None:
        cmd += [f"-g{cols}x{cols}"]
    cmd += ["--compress", "-pq", "--threads=-1", "-"]
    return (await call_subproc(data, cmd)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("catimg"),
)
async def image_to_ansi_catimg(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert image data to ANSI text using :command:`catimg`."""
    cmd: list[Any] = ["catimg"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols * 2]
    cmd += ["-"]
    return (await call_subproc(data, cmd)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("icat"),
)
async def image_to_ansi_icat(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert image data to ANSI text using :command:`icat`."""
    cmd: list[Any] = ["icat"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["--mode", "24bit", "-"]
    return (await call_subproc(data, cmd)).decode()


@register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="ansi",
    filter_=commands_exist("tiv"),
)
async def image_to_ansi_tiv(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert image data to ANSI text using :command:`tiv`."""
    cmd: list[Any] = ["tiv"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols, "-h", rows]
    return (await call_subproc(data, cmd, use_tempfile=True)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("viu"),
)
async def image_to_ansi_viu(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert image data to ANSI text using :command:`viu`."""
    cmd: list[Any] = ["viu", "-b"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["-s", "-"]
    return (await call_subproc(data, cmd)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=commands_exist("jp2a"),
)
async def image_to_ansi_jp2a(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert image data to ANSI text using :command:`jp2a`."""
    cmd: list[Any] = ["jp2a", "--color"]
    if cols is not None and rows is not None:
        cmd += [f"--height={rows}"]
    cmd += ["-"]
    return (await call_subproc(data, cmd)).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("img2txt"),
)
async def png_to_ansi_img2txt(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert PNG data to ANSI text using :command:`img2txt`."""
    cmd: list[Any] = ["img2txt"]
    if cols is not None and rows is not None:
        cmd += ["-W", cols, "-H", rows]
    return (await call_subproc(data, cmd, use_tempfile=True)).decode()


@register(from_=("png", "jpeg", "svg"), to="ansi", filter_=True, weight=99)
async def png_to_ansi_py_placeholder(
    data: bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Draw placeholder ANSI text."""
    from euporie.core.border import RoundedLine

    if cols is None:
        cols = 7
    if rows is None:
        rows = 3

    lines = []
    B = RoundedLine.grid
    lines.append(f"{B.TOP_LEFT}{B.TOP_MID * max(5, (cols - 2))}{B.TOP_RIGHT}")
    lines += [f"{B.MID_LEFT}{B.MID_MID * (cols - 2)}{B.MID_RIGHT}"] * ((rows - 3) // 2)
    lines.append(f"{B.MID_LEFT}{'Image'.center(cols - 2)}{B.MID_RIGHT}")
    lines += [f"{B.MID_LEFT}{B.MID_MID * (cols - 2)}{B.MID_RIGHT}"] * (
        (rows - 3) - (rows - 3) // 2
    )
    lines.append(f"{B.BOTTOM_LEFT}{B.BOTTOM_MID * max(5, (cols - 2))}{B.BOTTOM_RIGHT}")
    return "\n".join(lines)


@register(
    from_="rich",
    to="ansi",
    filter_=have_modules("rich"),
)
async def rich_to_ansi_py(
    data: RenderableType,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert rich objects to formatted ANSI text."""
    import rich

    console = rich.get_console()
    options = console.options
    if width is not None:
        options = options.update(max_width=width)
    buffer = console.render(data, options)
    rendered_lines = console._render_buffer(buffer)
    return rendered_lines
