"""Contain functions which can be used to convert data to multiple formats."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, overload

from euporie.apptk.application.current import get_app

from euporie.apptk.convert.utils import call_subproc, scale_to_fit

if TYPE_CHECKING:
    from typing import Any, Literal

    from euporie.apptk.convert.datum import Datum

log = logging.getLogger(__name__)


async def base64_to_bytes_py(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> bytes:
    """Convert base64 encoded data to bytes."""
    data = datum.data
    data_str = data.decode() if isinstance(data, bytes) else data
    return base64.b64decode(data_str)


async def imagemagick_convert(
    output_format: str,
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str | bytes:
    """Convert image data to PNG bytes using ``imagemagick``."""
    cmd: list[Any] = ["magick"]
    if bg:
        cmd += ["-background", bg]
    cmd.extend(["-[0]", "-density", "300"])
    app = get_app()
    if cols is not None and hasattr(app, "cell_size_px"):
        px, _ = app.output.cell_pixel_size
        cmd += ["-geometry", f"{int(cols * px)}"]
    cmd += [f"{output_format}:-"]
    result: bytes | str = await call_subproc(datum.data, cmd)

    if output_format in {"sixel", "svg"} and isinstance(result, bytes):
        result = result.decode()
    return result


async def chafa_convert_cmd(
    output_format: Literal["symbols", "sixels", "kitty", "iterm2"],
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str | bytes:
    """Convert image data to ANSI text using :command:`chafa`."""
    cmd: list[Any] = [
        "chafa",
        f"--format={output_format}",
        "--passthrough=none",
        "--polite=on",
    ]
    if cols is not None or rows is not None:
        size = "--size="
        if cols is not None:
            size = f"{size}{cols}"
        if rows is not None:
            size = f"{size}x{rows}"
        cmd.append(size)
    if bg:
        cmd += ["--bg", bg]
    # cmd += ["--stretch", "/dev/stdin"]
    return (await call_subproc(datum.data, cmd)).decode()


async def chafa_convert_py(
    output_format: Literal["symbols", "sixels", "kitty", "iterm2"],
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str | bytes:
    """Convert image data to ANSI text using ::`chafa.py`."""
    from chafa import Canvas, CanvasConfig, PixelMode, PixelType
    from PIL import Image

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
    data = datum.data
    # Always convert the image, as unconverted images sometime result in an off-by-one
    # line width errors resulting in diagonal image striping for some reason
    data = data.convert("RGBA", palette=Image.Palette.ADAPTIVE, colors=16)
    # Init canvas config
    config = CanvasConfig()
    # Set output mode
    config.pixel_mode = str_to_pixel_mode[output_format]
    # Configure the canvas geometry based on our cell size
    config.width, config.height = await scale_to_fit(datum, cols, rows)

    # Set the foreground color
    if fg and (color := fg.lstrip("#")):
        config.fg_color = (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

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


@overload
async def mermaid_rs_renderer_cmd(
    output_format: Literal["svg"],
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str: ...
@overload
async def mermaid_rs_renderer_cmd(
    output_format: Literal["png"],
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> bytes: ...
async def mermaid_rs_renderer_cmd(output_format, datum, cols, rows, fg, bg, **kwargs):
    """Convert a mermaid diagram to PNG or SVG using :cmd:`mmdr`."""
    cmd: list[Any] = [
        "mmdr",
        "--outputFormat",
        output_format,
        "--output=/dev/stdout",
    ]
    if cols is not None:
        cmd.extend(["--width", cols])
    if rows is not None:
        cmd.extend(["--height", rows])
    return await call_subproc(datum.data, cmd)


@overload
async def mermaid_cli_cmd(
    output_format: Literal["svg"],
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str: ...
@overload
async def mermaid_cli_cmd(
    output_format: Literal["png"],
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> bytes: ...
async def mermaid_cli_cmd(output_format, datum, cols, rows, fg, bg, **kwargs):
    """Convert a mermaid diagram to PNG or SVG using :cmd:`mmdc` (``mermaid-cli``)."""
    cmd: list[Any] = [
        "mmdc",
        "--input",
        "-",
        "--outputFormat",
        output_format,
        "--output",
        "-",
        "--quiet",
    ]
    if cols is not None:
        cmd.extend(["--width", str(cols)])
    if rows is not None:
        cmd.extend(["--height", str(rows)])
    if bg is not None:
        cmd.extend(["--backgroundColor", bg])
    result = await call_subproc(datum.data, cmd)
    if output_format == "svg" and isinstance(result, bytes):
        return result.decode()
    return result
