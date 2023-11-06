"""Contain function which convert data to sixel format."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from euporie.core.convert.formats.common import (
    chafa_convert_cmd,
    chafa_convert_py,
    imagemagick_convert,
)
from euporie.core.convert.registry import register
from euporie.core.convert.utils import call_subproc, commands_exist, have_modules
from euporie.core.current import get_app

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.convert.datum import Datum


register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="sixel",
    filter_=commands_exist("chafa"),
)(partial(chafa_convert_cmd, "sixels"))


register(
    from_=("pil"),
    to="sixel",
    filter_=have_modules("chafa"),
)(partial(chafa_convert_py, "sixels"))


@register(
    from_=("png", "jpeg"),
    to="sixel",
    filter_=commands_exist("img2sixel"),
)
async def png_to_sixel_img2sixel(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
) -> str:
    """Convert PNG data to sixels :command:`img2sixel`."""
    bg = datum.bg or get_app().color_palette.bg.base_hex
    cmd: list[Any] = ["img2sixel", "-I"]
    if bg:
        cmd += [f"--bgcolor={bg}"]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += [f"--width={int(cols * px)}"]
    return (await call_subproc(datum.data, cmd)).decode()


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
async def pil_to_sixel_py_timg(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
) -> str:
    """Convert a pillow image to sixels :py:mod:`timg`."""
    import timg

    return timg.SixelMethod(datum.data).to_string()


@register(
    from_="pil",
    to="sixel",
    filter_=have_modules("teimpy", "numpy"),
)
async def pil_to_sixel_py_teimpy(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
) -> str:
    """Convert a pillow image to sixels :py:mod:`teimpy`."""
    import numpy as np
    import teimpy

    return teimpy.get_drawer(teimpy.Mode.SIXEL).draw(np.asarray(datum.data))
