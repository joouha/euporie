"""Contains functions which can be used to convert data to multiple formats."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from euporie.app.current import get_base_app as get_app
from euporie.convert.util import call_subproc

if TYPE_CHECKING:
    from typing import Any, Optional, Union

log = logging.getLogger(__name__)


def base64_to_bytes_py(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Converts base64 encoded data to bytes."""
    return base64.b64decode(data)


def imagemagick_convert(
    output_format: "str",
    data: "Union[str, bytes]",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "Union[str, bytes]":
    """Converts image data to PNG bytes using ``imagemagick``."""
    cmd: "list[Any]" = ["convert"]
    if cols is not None:
        px, _ = get_app().term_info.cell_size_px
        cmd += ["-geometry", f"{int(cols * px)}"]
    bg = bg or get_app().color_palette["bg"][-1]
    if bg is not None:
        cmd += ["-background", bg]
    cmd += ["-", f"{output_format}:-"]
    result: "Union[bytes, str]" = call_subproc(data, cmd)
    if output_format in {"sixel", "svg"} and isinstance(result, bytes):
        result = result.decode()
    return result


def chafa_convert(
    output_format: "str",
    data: "Union[bytes, str]",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "Union[str, bytes]":
    """Converts image data to ANSI text using :command:`chafa`."""
    cmd: "list[Any]" = ["chafa", f"--format={output_format}"]
    if cols is not None and rows is not None:
        cmd += [f"--size={cols}x{rows}"]
    cmd += ["--stretch", "-"]
    return call_subproc(data, cmd).decode()
