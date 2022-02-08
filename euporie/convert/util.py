"""Utility functions for format convertors."""

from __future__ import annotations

import logging
import os
import subprocess  # noqa S404 - Security implications have been considered
import tempfile
from functools import partial, reduce
from importlib import import_module
from shutil import which
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition, to_filter

if TYPE_CHECKING:
    from typing import Any, Union

    from prompt_toolkit.filters import Filter

log = logging.getLogger(__name__)


def commands_exist(*cmds: "str") -> "Filter":
    """Verifies a list of external commands exist on the system."""
    filters = [Condition(partial(lambda x: bool(which(cmd)), cmd)) for cmd in cmds]
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
    data: "Union[str, bytes]", cmd: "list[Any]", use_tempfile: "bool" = False
) -> "bytes":
    """Call the command as a subprocess and return it's output as bytes.

    Args:
        data: The data to pass to the subprocess
        cmd: The command and arguments to call
        use_tempfile: If True, the command saves its output to a file, not stdout

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
        tfile = tempfile.NamedTemporaryFile(delete=False)
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
    try:
        output_bytes = subprocess.check_output(cmd, input=data)  # noqa S603
    except FileNotFoundError:
        log.error("Could not run external command `%s`", cmd)
        output_bytes = b"[Error drawing output]"

    # TODO Log any stderr

    # Clean up any temporary file
    if use_tempfile:
        tfile.close()
        os.unlink(tfile.name)

    return output_bytes
