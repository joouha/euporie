"""Utility functions for format converters."""

from __future__ import annotations

import io
import logging
import os
import subprocess  # noqa S404 - Security implications have been considered
import tempfile
from functools import partial, reduce
from importlib import import_module
from shutil import which
from typing import TYPE_CHECKING

import imagesize
from prompt_toolkit.filters import Condition, to_filter

from euporie.core.convert.base import convert
from euporie.core.current import get_app

if TYPE_CHECKING:
    from typing import Any, Optional, Union

    from prompt_toolkit.filters import Filter

log = logging.getLogger(__name__)


def commands_exist(*cmds: "str") -> "Filter":
    """Verifies a list of external commands exist on the system."""
    filters = [
        Condition(partial(lambda x: bool(which(cmd)), cmd))  # noqa: B023
        for cmd in cmds
    ]
    return reduce(lambda a, b: a & b, filters, to_filter(True))


def have_modules(*modules: "str") -> "Filter":
    """Verifies a list of python modules are importable."""

    def try_import(module: "str") -> "bool":
        try:
            import_module(module)
        except ModuleNotFoundError:
            return False
        else:
            return True

    filters = [Condition(partial(try_import, module)) for module in modules]
    return reduce(lambda a, b: a & b, filters, to_filter(True))


def call_subproc(
    data: "Union[str, bytes]",
    cmd: "list[Any]",
    use_tempfile: "bool" = False,
    suffix: "str" = "",
) -> "bytes":
    """Call the command as a subprocess and return it's output as bytes.

    Args:
        data: The data to pass to the subprocess
        cmd: The command and arguments to call
        use_tempfile: If True, the command saves its output to a file, not stdout
        suffix: Suffix for the temporary file name

    Returns:
        The data printed to standard out by the subprocess.

    """
    # Convert all command arguments to strings
    cmd = list(map(str, cmd))

    # Convert data to bytes
    if isinstance(data, str):
        data = data.encode()

    if use_tempfile:
        # If the command cannot read from stdin, create a temporary file to pass to
        # the command
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tfile.write(data)
        tfile.close()
        cmd.append(tfile.name)

    # TODO render asynchronously
    # proc = await asyncio.create_subprocess_shell(
    # " ".join(cmd),
    # stdout=asyncio.subprocess.PIPE,
    # stdin=asyncio.subprocess.PIPE,
    # stderr=asyncio.subprocess.DEVNULL,
    # )
    # stdout, stderr = await proc.communicate(data)

    log.debug("Running external command `%s`", cmd)
    error: "Optional[Exception]" = None
    try:
        # Execution of untrusted input has been checked for
        output_bytes = subprocess.check_output(  # noqa S603
            cmd, input=data, stderr=subprocess.DEVNULL
        )
    except FileNotFoundError as error_:
        log.error("Could not run external command `%s`", cmd)
        error = error_
    except subprocess.CalledProcessError as error_:
        log.error("There was an error while running external command `%s`", cmd)
        error = error_
    finally:
        if error is not None:
            # Generate an output stating there was an error
            output_bytes = (
                b"\x1b[33m"  # Set fg to yellow
                b"\xee\x82\xb6"  # Draw left pill side
                b"\x1b[43m\x1b[30m"  # Set fg to black, bg to yellow
                b"\xe2\x9a\xa0"  # Draw warning symbol
                b" Rendering Error"
                b"\x1b[33m\x1b[49m"  # Set fg to yellow, reset bg
                b"\xee\x82\xb4"  # Draw right pill side
                b"\x1b[n"  # Reset style
            )

        # TODO Log any stderr

        # Clean up any temporary file
        if use_tempfile:
            tfile.close()
            os.unlink(tfile.name)

    return output_bytes


def data_pixel_size(
    data: "Any",
    format_: "str",
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "tuple[Optional[int], Optional[int]]":
    """Get the dimensions of an image.

    Foreground and background color are set at this point if they are available, as
    data conversion outputs are cached and re-used.

    Args:
        data: The data to check the dimensions of
        format_: The current format of the data
        fg: The desired foreground color of the data
        bg: The desired background color of the data

    Returns:
        A tuple of the data's width in terminal columns and its aspect ratio, when
            converted to a image.

    """
    px = py = None
    # Do not bother trying if the format is ANSI
    if format_ == "ansi":
        return px, py
    # Try using imagesize to get the size of the output
    if format_ not in {"png", "svg", "jpg", "gif", "tiff"}:
        try:
            data = convert(data, from_=format_, to="png", fg=fg, bg=bg)
        except NotImplementedError:
            pass
    if isinstance(data, str):
        data = data.encode()
    try:
        px_calc, py_calc = imagesize.get(io.BytesIO(data))
    except ValueError:
        pass
    else:
        if px_calc > 0:
            px = px_calc
        if py_calc > 0:
            py = py_calc
    return px, py


def pixels_to_cell_size(
    px: "Optional[int]" = None,
    py: "Optional[int]" = None,
) -> "tuple[int, float]":
    """Get the cell width and aspect ration of a pixel dimension.

    Args:
        px: The desired pixel width of the data if known
        py: The pixel height of the data if known

    Returns:
        A tuple of the data's width in terminal columns and its aspect ratio, when
            converted to a image.

    """
    cols, aspect = 0, 0.0
    if px is not None and py is not None:
        app = get_app()
        if hasattr(app, "term_info"):
            cell_px, cell_py = get_app().term_info.cell_size_px
        else:
            cell_px, cell_py = 10, 20
        cols = max(1, int(px // cell_px))
        aspect = (py / cell_py) / (px / cell_px)
    return cols, aspect
