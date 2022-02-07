"""Contains function which convert PIL images to other formats."""

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

from PIL import Image  # type: ignore

from euporie.app.current import get_base_app as get_app
from euporie.convert.base import register
from euporie.convert.util import have_modules

if TYPE_CHECKING:
    from typing import Optional

log = logging.getLogger(__name__)


def set_background(image: "Image", bg_color: "Optional[str]" = None) -> "bytes":
    """Removes the alpha channel from an image and set the background colour."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        alpha = image.convert("RGBA").getchannel("A")
        bg = Image.new("RGBA", image.size, bg_color)
        bg.paste(image, mask=alpha)
        image = bg
    image = image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
        "RGB", palette=Image.ADAPTIVE, colors=16
    )
    return image


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
    bg = bg or get_app().term_info.background_color.value
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
    """Convert a PIL image to ANSI text using :py:mod:`timg`."""
    import io

    from img2unicode import FastQuadDualOptimizer, Renderer  # type: ignore

    output = io.StringIO()
    Renderer(FastQuadDualOptimizer(), max_w=cols, max_h=rows).render_terminal(
        data, output
    )
    output.seek(0)
    return output.read()


@register(
    from_="pil",
    to="sixel",
    filter_=have_modules("timg"),
)
def pil_to_sixel_py_timg(
    data: "Image",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert a pillow image to sixels :py:mod:`timg`."""
    import timg  # type: ignore

    return timg.SixelMethod(data).to_string()


@register(
    from_="pil",
    to="sixel",
    filter_=have_modules("teimpy", "numpy"),
)
def pil_to_sixel_py_teimpy(
    data: "Image",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert a pillow image to sixels :py:mod:`teimpy`."""
    import numpy as np  # type: ignore
    import teimpy  # type: ignore

    return teimpy.get_drawer(teimpy.Mode.SIXEL).draw(np.asarray(data))
