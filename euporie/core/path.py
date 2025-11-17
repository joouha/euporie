"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from upath import UPath
from upath.implementations.memory import MemoryPath

if TYPE_CHECKING:
    from collections.abc import Mapping
    from os import PathLike
    from typing import Any


log = logging.getLogger(__name__)


# Define custom universal_pathlib path implementations


class UntitledPath(MemoryPath):
    """A path for untitled files, as needed for LSP servers."""

    @classmethod
    def _parse_storage_options(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Parse storage_options from the urlpath."""
        return {}

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        """Untitled files are unsaved and do not exist."""
        return False


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
