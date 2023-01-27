"""Contains functions which can be used to convert data to multiple formats."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from euporie.core.app import get_app
from euporie.core.convert.utils import call_subproc

if TYPE_CHECKING:
    from typing import Any, Optional, Union

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


def chafa_convert(
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
