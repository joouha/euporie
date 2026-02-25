"""Define common filters."""

from __future__ import annotations

import os
from functools import cache, partial, reduce
from importlib.util import find_spec
from shutil import which
from typing import TYPE_CHECKING

from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.utils import to_filter

if TYPE_CHECKING:
    from prompt_toolkit.filters import Filter


@cache
def command_exists(*cmds: str) -> Filter:
    """Verify a list of external commands exist on the system."""
    filters = [
        Condition(partial(lambda x: bool(which(cmd)), cmd))  # noqa: B023
        for cmd in cmds
    ]
    return reduce(lambda a, b: a & b, filters, to_filter(True))


@cache
def have_modules(*modules: str) -> Filter:
    """Verify a list of python modules are importable."""

    def try_import(module: str) -> bool:
        loader = find_spec(module)
        return loader is not None

    filters = [Condition(partial(try_import, module)) for module in modules]
    return reduce(lambda a, b: a & b, filters, to_filter(True))


# Determine if euporie is running inside a multiplexer.
in_screen = to_filter(os.environ.get("TERM", "").startswith("screen"))
in_tmux = to_filter(os.environ.get("TMUX") is not None)
in_mplex = in_tmux | in_screen
