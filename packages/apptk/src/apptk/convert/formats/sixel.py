"""Contain function which convert data to sixel format."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.convert.formats.common import (
    chafa_convert_cmd,
    chafa_convert_py,
    imagemagick_convert,
)
from apptk.convert.registry import register
from apptk.convert.utils import call_subproc
from apptk.filters.environment import command_exists, have_modules

if TYPE_CHECKING:
    from typing import Any

    from apptk.convert.datum import Datum


register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="sixel",
    filter_=command_exists("chafa"),
)(partial(chafa_convert_cmd, "sixels"))


register(
    from_=("pil"),
    to="sixel",
    filter_=have_modules("chafa"),
)(partial(chafa_convert_py, "sixels"))


@register(
    from_=("png", "jpeg"),
    to="sixel",
    filter_=command_exists("img2sixel"),
)
async def png_to_sixel_img2sixel(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert PNG data to sixels :command:`img2sixel`."""
    cmd: list[Any] = ["img2sixel", "-I"]
    if bg:
        cmd += [f"--bgcolor={bg}"]
    if cols is not None:
        px, _ = get_app().output.cell_pixel_size
        cmd += [f"--width={int(cols * px)}"]
    output = (await call_subproc(datum.data, cmd)).decode()
    if not output.startswith("\x1bP"):
        # Some libsixel builds exit successfully having written nothing at all,
        # which would reserve the image's cells and draw nothing in them
        msg = "`img2sixel` produced no sixel data"
        raise ValueError(msg)
    return output


register(
    from_=("png", "jpeg", "svg", "pdf"),
    to="sixel",
    filter_=command_exists("magick"),
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
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
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
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert a pillow image to sixels :py:mod:`teimpy`."""
    import numpy as np
    import teimpy

    return teimpy.get_drawer(teimpy.Mode.SIXEL).draw(np.asarray(datum.data))
