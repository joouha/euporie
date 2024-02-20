"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import upath
from aiohttp.client_reqrep import ClientResponse
from fsspec.implementations.http import HTTPFileSystem as FsHTTPFileSystem
from fsspec.registry import register_implementation as fs_register_implementation
from upath import UPath

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any, Mapping


log = logging.getLogger(__name__)


# Monkey-patch `aiohttp` to not raise exceptions on non-200 responses


def _raise_for_status(self: ClientResponse) -> None:
    """Monkey-patch :py:class:`aiohttp.ClientResponse` not to raise for any status."""


setattr(ClientResponse, "raise_for_status", _raise_for_status)  # noqa B010


# Define and register non-raising HTTP filesystem implementation for fsspec


class HTTPFileSystem(FsHTTPFileSystem):
    """A :py:class:`HTTPFileSystem` which does not raise exceptions on 404 errors."""

    def _raise_not_found_for_status(self, response: ClientResponse, url: str) -> None:
        """Do not raise an exception for 404 errors."""


fs_register_implementation("http", HTTPFileSystem, clobber=True)
fs_register_implementation("https", HTTPFileSystem, clobber=True)


# Define custom universal_pathlib path implementations


class UntitledPath(upath.core.UPath):
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


def parse_path(path: str | PathLike, resolve: bool = True) -> Path:
    """Parse and resolve a path."""
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
    return path
