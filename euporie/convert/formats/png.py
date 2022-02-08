"""Contains functions which convert data to png format."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from euporie.convert.base import register
from euporie.convert.formats.common import base64_to_bytes_py, imagemagick_convert
from euporie.convert.util import commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Optional

    from PIL import Image  # type: ignore


register(
    from_="base64-png",
    to="png",
)(base64_to_bytes_py)


def latex_to_png_py_ipython(
    backend: "str",
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Converts LaTeX data to PNG bytes with :py:mod:`IPython` & :py:mod:`matplotlib`."""
    from IPython.lib.latextools import latex_to_png  # type: ignore

    return latex_to_png(
        data, encode=False, backend=backend, **({"color": fg} if fg else {})
    )


register(
    from_="latex",
    to="png",
    filter_=commands_exist("dvipng") & have_modules("IPython"),
)(partial(latex_to_png_py_ipython, "dvipng"))


register(
    from_="latex",
    to="png",
    filter_=have_modules("IPython", "matplotlib"),
)(partial(latex_to_png_py_ipython, "matplotlib"))


register(
    from_=("svg", "jpeg", "pdf"),
    to="png",
    filter_=commands_exist("convert", "magick"),
)(partial(imagemagick_convert, "PNG"))


@register(
    from_="pil",
    to="png",
    filter_=have_modules("PIL"),
)
def pil_to_png_py_pil(
    data: "Image",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Convert a pillow image to sixels :py:mod:`teimpy`."""
    import io

    with io.BytesIO() as output:
        data.save(output, format="PNG")
        contents = output.getvalue()
    return contents


@register(
    from_="svg",
    to="png",
    filter_=have_modules("cairosvg"),
)
def svg_to_png_py_cairosvg(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert SVG to PNG using :py:mod:`cairosvg`."""
    import cairosvg  # type: ignore

    return cairosvg.surface.PNGSurface.convert(data, write_to=None)
