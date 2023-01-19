"""Contains functions which convert data to png format."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from euporie.core.convert.base import register
from euporie.core.convert.formats.common import base64_to_bytes_py, imagemagick_convert
from euporie.core.convert.utils import commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Optional

    from PIL.Image import Image as PilImage
    from upath import UPath


register(
    from_="base64-png",
    to="png",
)(base64_to_bytes_py)


def latex_to_png_py_ipython(
    backend: "str",
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "bytes":
    """Converts LaTeX data to PNG bytes with :py:mod:`IPython` & :py:mod:`matplotlib`."""
    from IPython.lib.latextools import latex_to_png

    markup = data.decode() if isinstance(data, bytes) else data
    return (
        latex_to_png(
            markup, encode=False, backend=backend, **({"color": fg} if fg else {})
        )
        or b"error"
    )


register(
    from_="latex",
    to="png",
    filter_=commands_exist("dvipng") & have_modules("IPython.lib.latextools"),
)(partial(latex_to_png_py_ipython, "dvipng"))


register(
    from_="latex",
    to="png",
    filter_=have_modules("IPython.lib.latextools", "matplotlib"),
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
    data: "PilImage",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
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
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "str":
    """Convert SVG to PNG using :py:mod:`cairosvg`."""
    import cairosvg

    markup = data.decode() if isinstance(data, bytes) else data
    return cairosvg.surface.PNGSurface.convert(markup, write_to=None)
