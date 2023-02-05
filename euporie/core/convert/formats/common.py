"""Contains functions which can be used to convert data to multiple formats."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from euporie.core.convert.utils import call_subproc
from euporie.core.current import get_app

if TYPE_CHECKING:
    from typing import Any, Literal, Optional, Union

    from PIL.Image import Image as PilImage
    from upath import UPath

log = logging.getLogger(__name__)


def base64_to_bytes_py(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "bytes":
    """Converts base64 encoded data to bytes."""
    data_str = data.decode() if isinstance(data, bytes) else data
    return base64.b64decode(data_str)


def imagemagick_convert(
    output_format: "str",
    data: "str|bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "Union[str, bytes]":
    """Converts image data to PNG bytes using ``imagemagick``."""
    cmd: "list[Any]" = ["convert"]  # , "-density", "300"]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += ["-geometry", f"{int(cols * px)}"]
    bg = bg or get_app().color_palette.bg.base_hex
    if bg is not None:
        cmd += ["-background", bg]
    cmd += ["-[0]", f"{output_format}:-"]
    result: "Union[bytes, str]" = call_subproc(data, cmd)
    if output_format in {"sixel", "svg"} and isinstance(result, bytes):
        result = result.decode()
    return result


def chafa_convert_cmd(
    output_format: "str",
    data: "str|bytes",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "Union[str, bytes]":
    """Converts image data to ANSI text using :command:`chafa`."""
    cmd: "list[Any]" = ["chafa", f"--format={output_format}"]
    if cols is not None or rows is not None:
        cmd += [f"--size={cols or '1'}x{rows or '1'}"]
    if bg:
        cmd += ["--bg", bg]
    cmd += ["--stretch", "/dev/stdin"]
    return call_subproc(data, cmd).decode()


def chafa_convert_py(
    output_format: "Literal['symbols','sixels','kitty','iterm2']",
    data: "PilImage",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "Union[str, bytes]":
    """Convert image data to ANSI text using ::`chafa.py`."""
    from chafa.chafa import Canvas, CanvasConfig, PixelMode, PixelType

    pil_mode_to_pixel_type = {
        "RGBa": PixelType.CHAFA_PIXEL_RGBA8_PREMULTIPLIED,
        "RGBA": PixelType.CHAFA_PIXEL_RGBA8_UNASSOCIATED,
        "RGB": PixelType.CHAFA_PIXEL_RGB8,
    }

    str_to_pixel_mode = {
        "symbols": PixelMode.CHAFA_PIXEL_MODE_SYMBOLS,
        "sixels": PixelMode.CHAFA_PIXEL_MODE_SIXELS,
        "kitty": PixelMode.CHAFA_PIXEL_MODE_KITTY,
        "iterm2": PixelMode.CHAFA_PIXEL_MODE_ITERM2,
    }

    # Convert PIL image to format that chafa can use
    if data.mode not in pil_mode_to_pixel_type:
        from PIL import Image

        data = data.convert("RGBA", palette=Image.Palette.ADAPTIVE, colors=16)

    # Init canvas config
    config = CanvasConfig()
    # Set output mode
    config.pixel_mode = str_to_pixel_mode[output_format]
    # Set canvas height and width
    config.height = rows or 20
    config.width = cols or 80
    # Configure the canvas geometry based on our cell size
    config.cell_width, config.cell_height = get_app().term_info.cell_size_px
    # Set the background color
    if bg and (color := bg.lstrip("#")):
        config.bg_color = (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

    # Init the canvas
    canvas = Canvas(config)

    # Draw to canvas
    canvas.draw_all_pixels(
        pil_mode_to_pixel_type.get(data.mode, PixelType.CHAFA_PIXEL_RGBA8_UNASSOCIATED),
        list(data.tobytes()),
        width := data.width,
        data.height,
        width * len(data.getbands()),
    )

    # Return the output
    return canvas.print(fallback=True).decode()
