"""Contains function which convert PNGs to other formats."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.app.current import get_base_app as get_app
from euporie.convert.base import register
from euporie.convert.util import call_subproc, commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Any, Optional

    from PIL import Image  # type: ignore


log = logging.getLogger(__name__)


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("chafa"),
)
def png_to_ansi_chafa(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`chafa`."""
    cmd: "list[Any]" = ["chafa", "--format=symbols"]
    if cols is not None and rows is not None:
        cmd += [f"--size={cols}x{rows}"]
    cmd += ["--stretch", "-"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("timg") & ~have_modules("timg"),
)
def png_to_ansi_timg(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`chafa`."""
    cmd: "list[Any]" = ["timg"]
    if cols is not None and rows is not None:
        cmd += [f"-g{cols}x{cols}"]
    cmd += ["--compress", "-pq", "--threads=-1", "-"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("catimg"),
)
def png_to_ansi_catimg(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`catimg`."""
    cmd: "list[Any]" = ["catimg", "--format=symbols"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols * 2, "-"]
    cmd += ["-"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("icat"),
)
def png_to_ansi_icat(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`icat`."""
    cmd: "list[Any]" = ["icat"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["--mode", "24bit"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("tiv"),
)
def png_to_ansi_tiv(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`tiv`."""
    cmd: "list[Any]" = ["tiv"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols, "-h", rows]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("viu"),
)
def png_to_ansi_viu(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`viu`."""
    cmd: "list[Any]" = ["viu"]
    if cols is not None and rows is not None:
        cmd += ["-w", cols]
    cmd += ["-s", "-"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=commands_exist("jp2a"),
)
def png_to_ansi_jp2a(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG data to ANSI text using :command:`jp2a`."""
    cmd: "list[Any]" = ["jp2a", "--color", "-"]
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
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="ansi",
    filter_=True,
)
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
    from_="png",
    to="pil",
    filter_=have_modules("PIL"),
)
def png_to_pil_py(
    data: "bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "Image":
    """Convert PNG to a pillow image using :py:mod:`PIL`."""
    import io

    from PIL import Image  # type: ignore

    try:
        image = Image.open(io.BytesIO(data))
    except IOError:
        log.error("Could not load image.")
    else:
        return image


@register(
    from_="png",
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
    bg = bg or get_app().term_info.background_color.value
    cmd: "list[Any]" = ["img2sixel"]
    if bg:
        cmd += [f"--bgcolor={bg}"]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += [f"--width={int(cols * px)}"]
    return call_subproc(data, cmd).decode()


@register(
    from_="png",
    to="sixel",
    filter_=commands_exist("convert", "magick"),
)
def png_to_sixel_imagemagick(
    data: "str",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG bytes to sixels using ``imagemagick``."""
    cmd: "list[Any]" = ["convert"]
    if cols is not None:
        px, py = get_app().term_info.cell_size_px
        cmd += ["-geometry", f"{int(cols * px)}"]
    bg = bg or get_app().term_info.background_color.value
    if bg is not None:
        cmd += ["-background", bg]
    cmd += ["-", "sixel:-"]
    return call_subproc(data.encode(), cmd).decode()


@register(
    from_="png",
    to="sixel",
    filter_=commands_exist("chafa"),
)
def png_to_sixel_chafa(
    data: "str",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts PNG bytes to sixels using ``imagemagick``."""
    cmd: "list[Any]" = ["convert"]
    if cols is not None:
        px, py = get_app().term_info.cell_size_px
        cmd += ["-geometry", f"{cols * px}"]
    bg = bg or get_app().term_info.background_color.value
    if bg is not None:
        cmd += ["-background", bg]
    cmd += ["-", "sixel:-"]
    return call_subproc(data.encode(), cmd).decode()
