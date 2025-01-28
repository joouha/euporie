"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import upath
from aiohttp.client_reqrep import ClientResponse
from fsspec.implementations.http import HTTPFileSystem as FsHTTPFileSystem
from fsspec.implementations.http import get_client
from fsspec.registry import register_implementation as fs_register_implementation
from upath import UPath

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Mapping
    from os import PathLike
    from typing import Any, Callable

    import aiohttp


log = logging.getLogger(__name__)


class NoRaiseClientResponse(ClientResponse):
    """An ``aiohttp`` client response which does not raise on >=400 status responses."""

    @property
    def ok(self) -> bool:
        """Returns ``True`` if ``status`` is probably renderable."""
        return self.status not in {405}


class HTTPFileSystem(FsHTTPFileSystem):
    """A HTTP filesystem implementation which does not raise on errors."""

    def __init__(
        self,
        simple_links: bool = True,
        block_size: int | None = None,
        same_scheme: bool = True,
        size_policy: None = None,
        cache_type: str = "bytes",
        cache_options: dict[str, Any] | None = None,
        asynchronous: bool = False,
        loop: asyncio.AbstractEventLoop | None = None,
        client_kwargs: dict[str, Any] | None = None,
        get_client: Callable[..., aiohttp.ClientSession] = get_client,
        encoded: bool = False,
        **storage_options: Any,
    ) -> None:
        """Defaults to using :py:mod:`NoRaiseClientResponse` for responses."""
        client_kwargs = {
            "response_class": NoRaiseClientResponse,
            **(client_kwargs or {}),
        }
        super().__init__(
            simple_links=simple_links,
            block_size=block_size,
            same_scheme=same_scheme,
            size_policy=size_policy,
            cache_type=cache_type,
            cache_options=cache_options,
            asynchronous=asynchronous,
            loop=loop,
            client_kwargs=client_kwargs,
            get_client=get_client,
            encoded=encoded,
            **storage_options,
        )

    def _raise_not_found_for_status(self, response: ClientResponse, url: str) -> None:
        """Do not raise an exception for 404 errors."""
        response.raise_for_status()


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
