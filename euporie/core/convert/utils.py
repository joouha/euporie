"""Utility functions for format converters."""

from __future__ import annotations

import asyncio
import logging
import subprocess  # S404 - Security implications have been considered
import tempfile
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING

from euporie.core.app.current import get_app

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.convert.datum import Datum

log = logging.getLogger(__name__)


async def scale_to_fit(
    datum: Datum, cols: int | None, rows: int | None
) -> tuple[int, int]:
    """Calculate image size based on aspect ratio, and scale to fit."""
    data = datum.data
    px, py = get_app().cell_size_px

    # Calculate rows based on image aspect ratio
    w, h = data.size
    if rows is None and cols is not None:
        rows = ceil(cols / w * h)
    elif cols is None and rows is not None:
        cols = ceil(rows / h * w)
    elif rows is None and cols is None:
        cols = ceil(w / px)
        rows = ceil(h / py)
    assert rows is not None
    assert cols is not None

    # Scale to fit while maintaining aspect ratio
    _width, aspect = await datum.cell_size_async()
    if cols * aspect < rows:
        rows = ceil(cols * aspect)
    else:
        cols = ceil(rows / aspect)

    return cols, rows


async def call_subproc(
    data: str | bytes,
    cmd: list[Any],
    use_tempfile: bool = False,
    suffix: str = "",
) -> bytes:
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tfile:
            tfile.write(data)
        cmd.append(tfile.name)
        stdinput = None
    else:
        stdinput = data

    if log.level <= 0:
        import shlex

        log.debug("Running external command `%s`", shlex.join(cmd))

    error: Exception | None = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        output_bytes, _ = await proc.communicate(stdinput)
    except FileNotFoundError as error:
        log.error("Could not run external command `%s`", cmd)
        raise error
    except subprocess.CalledProcessError as error:
        log.error("There was an error while running external command `%s`", cmd)
        raise error
    else:
        if (proc.returncode or 0) > 0 or error:
            # Raise an exception if the process failed so we can continue on the the
            # next conversion method
            raise subprocess.CalledProcessError(proc.returncode or 0, cmd)
    finally:
        # Clean up any temporary file
        if use_tempfile:
            tfile.close()
            Path(tfile.name).unlink()

    return output_bytes
