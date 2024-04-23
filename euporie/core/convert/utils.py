"""Utility functions for format converters."""

from __future__ import annotations

import asyncio
import logging
import subprocess  # S404 - Security implications have been considered
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

log = logging.getLogger(__name__)


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
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tfile.write(data)
        tfile.close()
        cmd.append(tfile.name)
        stdinput = None
    else:
        stdinput = data

    log.debug("Running external command `%s`", cmd)
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
