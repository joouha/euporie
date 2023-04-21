"""Contain functions which can be used to convert data to multiple formats."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from euporie.core.convert.utils import call_subproc
from euporie.core.current import get_app

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Literal

    from PIL.Image import Image as PilImage

log = logging.getLogger(__name__)


def base64_to_bytes_py(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
) -> bytes:
    """Convert base64 encoded data to bytes."""
    data_str = data.decode() if isinstance(data, bytes) else data
    return base64.b64decode(data_str)


def imagemagick_convert(
    output_format: str,
    data: str | bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
) -> str | bytes:
    """Convert image data to PNG bytes using ``imagemagick``."""
    cmd: list[Any] = ["convert"]  # , "-density", "300"]
    app = get_app()
    if cols is not None and hasattr(app, "term_info"):
        px, _ = app.term_info.cell_size_px
        cmd += ["-geometry", f"{int(cols * px)}"]
    if bg is None and hasattr(app, "color_palette"):
        bg = app.color_palette.bg.base_hex
    if bg is not None:
        cmd += ["-background", bg]
    cmd += ["-[0]", f"{output_format}:-"]
    result: bytes | str = call_subproc(data, cmd)

    if output_format in {"sixel", "svg"} and isinstance(result, bytes):
        result = result.decode()
    return result


def chafa_convert_cmd(
    output_format: str,
    data: str | bytes,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
) -> str | bytes:
    """Convert image data to ANSI text using :command:`chafa`."""
    cmd: list[Any] = ["chafa", f"--format={output_format}"]
    if cols is not None or rows is not None:
        cmd += [f"--size={cols or '1'}x{rows or '1'}"]
    if bg:
        cmd += ["--bg", bg]
    cmd += ["--stretch", "/dev/stdin"]
    return call_subproc(data, cmd).decode()


def chafa_convert_py(
    output_format: Literal["symbols", "sixels", "kitty", "iterm2"],
    data: PilImage,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
) -> str | bytes:
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
    # Configure the canvas geometry based on our cell size
    if hasattr(app := get_app(), "term_info"):
        px, py = app.term_info.cell_size_px
    else:
        px, py = 10, 20
    config.cell_width, config.cell_height = px, py
    # Set canvas height and width
    if cols:
        config.width = cols
        if rows:
            config.height = rows
        # If we don't have specified, use the image's aspect
        else:
            config.height = int(cols / data.size[0] * data.size[1] * px / py)

    # Set the foreground color
    if fg is None and hasattr(app, "color_palette"):
        fg = app.color_palette.fg.base_hex
    if fg and (color := fg.lstrip("#")):
        config.fg_color = (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

    # Set the background color
    if bg is None and hasattr(app, "color_palette"):
        bg = app.color_palette.bg.base_hex
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
