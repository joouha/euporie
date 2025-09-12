"""Contain functions which convert data to formatted ansi text."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from euporie.core.app.current import get_app
from euporie.core.convert.formats.common import chafa_convert_cmd, chafa_convert_py
from euporie.core.convert.formats.pil import set_background
from euporie.core.convert.registry import register
from euporie.core.convert.utils import call_subproc, scale_to_fit
from euporie.core.filters import command_exists, have_modules

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.convert.datum import Datum

log = logging.getLogger(__name__)


@register(
    from_="html",
    to="ansi",
    filter_=command_exists("w3m"),
)
async def html_to_ansi_w3m(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert HTML text to formatted ANSI using :command:`w3m`."""
    cmd: list[Any] = ["w3m", "-T", "text/html"]
    if cols is not None:
        cmd += ["-cols", str(cols)]
    return (await call_subproc(datum.data.encode(), cmd)).decode()


@register(
    from_="html",
    to="ansi",
    filter_=command_exists("elinks"),
)
async def html_to_ansi_elinks(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
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
    if cols is not None:
        cmd += ["-dump-width", cols]
    return (await call_subproc(datum.data.encode(), cmd)).decode()


@register(
    from_="html",
    to="ansi",
    filter_=command_exists("lynx"),
)
async def html_to_ansi_lynx(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert HTML text to formatted ANSI using :command:`lynx`."""
    cmd: list[Any] = ["lynx", "-dump", "-stdin"]
    if cols is not None:
        cmd += [f"-width={cols}"]
    return (await call_subproc(datum.data.encode(), cmd)).decode()


@register(
    from_="html",
    to="ansi",
    filter_=command_exists("links"),
)
async def html_to_ansi_links(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert HTML text to formatted ANSI using :command:`links`."""
    cmd: list[Any] = ["links", "-dump"]
    if cols is not None:
        cmd += ["-width", cols]
    return (await call_subproc(datum.data.encode(), cmd, use_tempfile=True)).decode()


@register(
    from_="html",
    to="ansi",
    weight=4,
)
async def html_to_ansi_py_htmlparser(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
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
    stripper.feed(datum.data)
    output = stripper.get_data()
    # Strip lines
    output = "\n".join([x.strip() for x in output.strip().split("\n")])
    # Remove empty paragraphs
    return re.sub("\n\n\n+", "\n\n", output)


@register(
    from_="latex",
    to="ansi",
    filter_=command_exists("utftex"),
    weight=0,
)
async def latex_to_ansi_utftex(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Render LaTeX maths as unicode."""
    return (
        (await call_subproc(datum.data.strip().strip("$").strip(), ["utftex"]))
        .decode()
        .rstrip("\n")
    )


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("pylatexenc"),
    weight=0,
)
async def latex_to_ansi_py_pylatexenc(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert LaTeX to ANSI using :py:mod:`pylatexenc`."""
    from pylatexenc.latex2text import LatexNodes2Text

    return LatexNodes2Text().latex_to_text(datum.data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("flatlatex.latexfuntypes"),
    weight=0,
)
async def latex_to_ansi_py_flatlatex(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert LaTeX to ANSI using :py:mod:`flatlatex`."""
    import flatlatex
    from flatlatex.latexfuntypes import latexfun

    converter = flatlatex.converter()
    for style in (
        r"\textstyle",
        r"\displaystyle",
        r"\scriptstyle",
        r"\scriptscriptstyle",
    ):
        converter._converter__cmds[style] = latexfun(lambda x: "", 0)

    return converter.convert(datum.data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("sympy", "antlr4"),
)
async def latex_to_ansi_py_sympy(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert LaTeX to ANSI using :py:mod:`sympy`."""
    from sympy import pretty
    from sympy.parsing.latex import parse_latex
    from sympy.parsing.latex.errors import LaTeXParsingError

    from euporie.core.log import stdout_to_log

    with stdout_to_log(log):
        try:
            parsed = parse_latex(datum.data.strip().strip("$").strip())
        except LaTeXParsingError:
            parsed = datum.data
    return pretty(parsed)


@register(from_="pil", to="ansi", filter_=have_modules("timg"), weight=2)
async def pil_to_ansi_py_timg(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert a PIL image to ANSI text using :py:mod:`timg`."""
    import timg

    # Scale image to fit available space
    cols, rows = await scale_to_fit(datum, cols, rows)
    # `timg` assumes a 2x1 terminal cell aspect ratio, so we correct for this while
    px, py = get_app().cell_size_px
    rows = int(rows * 2 * (px / py) / 0.5)
    # Resize the image
    data = datum.data.resize((cols, rows))
    # Set background if necessary
    if bg:
        data = set_background(data, bg)
    return timg.Ansi24HblockMethod(data).to_string()


@register(
    from_="pil",
    to="ansi",
    filter_=have_modules("img2unicode"),
)
async def pil_to_ansi_py_img2unicode(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert a PIL image to ANSI text using :py:mod:`img2unicode`."""
    import io

    from img2unicode import FastQuadDualOptimizer, Renderer

    output = io.StringIO()
    Renderer(FastQuadDualOptimizer(), max_w=cols, max_h=rows).render_terminal(
        datum.data, output
    )
    output.seek(0)
    return output.read()


register(
    from_=("png", "jpeg", "svg", "pdf", "gif"),
    to="ansi",
    filter_=command_exists("chafa"),
)(partial(chafa_convert_cmd, "symbols"))


register(from_=("pil"), to="ansi", filter_=have_modules("chafa"))(
    partial(chafa_convert_py, "symbols")
)


@register(
    from_=("png", "jpeg", "pdf", "gif"),
    to="ansi",
    filter_=command_exists("timg") & ~have_modules("timg"),
)
async def image_to_ansi_timg(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert image data to ANSI text using :command:`timg`."""
    cmd: list[Any] = ["timg"]
    if cols is not None and rows is not None:
        cmd += [f"-g{cols}x{cols}"]
    cmd += ["--compress", "-pq", "--threads=-1", "-"]
    return (await call_subproc(datum.data, cmd)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=command_exists("catimg"),
)
async def image_to_ansi_catimg(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert image data to ANSI text using :command:`catimg`."""
    cmd: list[Any] = ["catimg"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols * 2]
    cmd += ["-"]
    return (await call_subproc(datum.data, cmd)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=command_exists("icat"),
)
async def image_to_ansi_icat(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert image data to ANSI text using :command:`icat`."""
    cmd: list[Any] = ["icat"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["--mode", "24bit", "-"]
    return (await call_subproc(datum.data, cmd)).decode()


@register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="ansi",
    filter_=command_exists("tiv"),
)
async def image_to_ansi_tiv(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert image data to ANSI text using :command:`tiv`."""
    cmd: list[Any] = ["tiv"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols, "-h", rows]
    return (await call_subproc(datum.data, cmd, use_tempfile=True)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=command_exists("viu"),
)
async def image_to_ansi_viu(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert image data to ANSI text using :command:`viu`."""
    cmd: list[Any] = ["viu", "-b"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["-s", "-"]
    return (await call_subproc(datum.data, cmd)).decode()


@register(
    from_=("png", "jpeg"),
    to="ansi",
    filter_=command_exists("jp2a"),
)
async def image_to_ansi_jp2a(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert image data to ANSI text using :command:`jp2a`."""
    cmd: list[Any] = ["jp2a", "--color"]
    if cols is not None and rows is not None:
        cmd += [f"--height={rows}"]
    cmd += ["-"]
    return (await call_subproc(datum.data, cmd)).decode()


@register(
    from_="png",
    to="ansi",
    filter_=command_exists("img2txt"),
)
async def png_to_ansi_img2txt(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert PNG data to ANSI text using :command:`img2txt`."""
    cmd: list[Any] = ["img2txt"]
    if cols is not None and rows is not None:
        cmd += ["-W", cols, "-H", rows]
    return (await call_subproc(datum.data, cmd, use_tempfile=True)).decode()


@register(from_=("png", "jpeg", "svg"), to="ansi", filter_=True, weight=99)
async def png_to_ansi_py_placeholder(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
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
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert rich objects to formatted ANSI text."""
    import rich

    console = rich.get_console()
    options = console.options
    if cols is not None:
        options = options.update(max_width=cols)
    buffer = console.render(datum.data, options)
    return console._render_buffer(buffer)
