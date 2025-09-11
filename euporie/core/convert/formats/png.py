"""Contain functions which convert data to png format."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING

from euporie.core.convert.formats.common import base64_to_bytes_py, imagemagick_convert
from euporie.core.convert.registry import register
from euporie.core.filters import command_exists, have_modules

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.convert.datum import Datum

register(
    from_="base64-png",
    to="png",
)(base64_to_bytes_py)


@register(
    from_="latex",
    to="png",
    filter_=command_exists("dvipng", "latex"),
)
async def latex_to_png_dvipng(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    timeout: int = 2,
    **kwargs: Any,
) -> bytes | None:
    """Render LaTeX as a png image using :command:`dvipng`.

    Borrowed from IPython.
    """
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    latex_doc = (
        r"\documentclass{article}\pagestyle{empty}\begin{document}"
        + datum.data
        + r"\end{document}"
    )

    workdir = Path(tempfile.mkdtemp())
    with workdir.joinpath("tmp.tex").open("w", encoding="utf8") as f:
        f.writelines(latex_doc)

    # Convert hex color to latex color
    if fg and len(fg) == 4:
        fg = f"#{fg[1]}{fg[1]}{fg[2]}{fg[2]}{fg[3]}{fg[3]}"
    fg_latex = (
        f"RGB {int(fg[1:3], 16)} {int(fg[3:5], 16)} {int(fg[5:7], 16)}" if fg else ""
    )

    # Convert latex document to dvi image, then Convert dvi image to png
    try:
        proc = await asyncio.create_subprocess_exec(
            *["latex", "-halt-on-error", "-interaction", "batchmode", "tmp.tex"],
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=workdir,
        )
        await asyncio.wait_for(proc.wait(), timeout)

        dvipng_cmd = [
            "dvipng",
            "-T",
            "tight",
            "-D",
            "175",
            "-z",
            "9",
            "-bg",
            "Transparent",
            "-o",
            "/dev/stdout",
            "tmp.dvi",
        ]
        if fg:
            dvipng_cmd += ["-fg", fg_latex]

        proc = await asyncio.create_subprocess_exec(
            *dvipng_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=workdir,
        )
        output, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except (subprocess.CalledProcessError, TimeoutError):
        return None
    finally:
        # Clean up temporary folder
        shutil.rmtree(workdir)

    return output


@register(
    from_="latex",
    to="png",
    filter_=have_modules("matplotlib"),
)
async def latex_to_png_py_mpl(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> bytes:
    """Render LaTeX as a png image using :py:module:`matplotlib`.

    Borrowed from IPython.
    """
    from io import BytesIO

    from matplotlib import figure, font_manager, mathtext
    from matplotlib.backends import backend_agg

    # mpl mathtext doesn't support display math, force inline
    data = datum.data.replace("$", "").strip()
    data = f"${data}$"
    buffer = BytesIO()
    prop = font_manager.FontProperties(size=12)
    parser = mathtext.MathTextParser("path")
    width, height, depth, _, _ = parser.parse(data, dpi=72, prop=prop)
    fig = figure.Figure(figsize=(width / 72, height / 72))
    fig.text(0, depth / height, data, fontproperties=prop, color=fg, usetex=False)
    backend_agg.FigureCanvasAgg(fig)
    fig.savefig(buffer, dpi=120, format="png", transparent=True)
    return buffer.getvalue()


register(
    from_=("svg", "jpeg", "pdf", "gif"),
    to="png",
    filter_=command_exists("magick"),
)(partial(imagemagick_convert, "PNG"))


@register(
    from_="pil",
    to="png",
    filter_=have_modules("PIL"),
)
async def pil_to_png_py_pil(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> bytes:
    """Convert a pillow image to sixels :py:mod:`teimpy`."""
    import io

    with io.BytesIO() as output:
        datum.data.save(output, format="PNG")
        return output.getvalue()


@register(
    from_="svg",
    to="png",
    filter_=have_modules("cairosvg"),
)
async def svg_to_png_py_cairosvg(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert SVG to PNG using :py:mod:`cairosvg`."""
    import cairosvg

    data = datum.data
    markup = data.decode() if isinstance(data, bytes) else data
    return cairosvg.surface.PNGSurface.convert(markup, write_to=None)
