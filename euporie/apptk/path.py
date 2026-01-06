"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from upath import UPath

if TYPE_CHECKING:
    from os import PathLike


log = logging.getLogger(__name__)


def parse_path(path: str | PathLike, resolve: bool | None = None) -> Path:
    """Parse and resolve a path."""
    if resolve is None:
        from upath.implementations.http import HTTPPath

        if isinstance(path, HTTPPath):
            resolve = True
        else:
            resolve = False
    if not isinstance(path, Path):
        path = UPath(path)
    try:
        path = path.expanduser()
    except NotImplementedError:
        pass
    if resolve:
        try:
            path = path.resolve()
        except (AttributeError, NotImplementedError, Exception):
            log.info("Path %s not resolvable", path)
    else:
        try:
            path = path.absolute()
        except NotImplementedError:
            pass
    return path
