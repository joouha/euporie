"""Contains function which convert data to sixel format."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from euporie.app.current import get_base_app as get_app
from euporie.convert.base import register
from euporie.convert.formats.common import chafa_convert, imagemagick_convert
from euporie.convert.util import call_subproc, commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Any, Optional

    from PIL import Image  # type: ignore


@register(
    from_=("png", "jpeg"),
    to="sixel",
    filter_=commands_exist("img2sixel"),
)
def png_to_sixel_img2sixel(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to sixels :command:`img2sixel`."""
    bg = bg or get_app().color_palette["bg"][-1]
    cmd: "list[Any]" = ["img2sixel"]
    if bg:
        cmd += [f"--bgcolor={bg}"]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += [f"--width={int(cols * px)}"]
    return call_subproc(data, cmd).decode()


register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="ansi",
    filter_=commands_exist("chafa"),
)(partial(chafa_convert, "sixel"))


register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="sixel",
    filter_=commands_exist("convert", "magick"),
)(partial(imagemagick_convert, "sixel"))


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
