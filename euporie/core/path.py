"""Responsible for loading data from urls."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlunsplit

import upath
from aiohttp.client_reqrep import ClientResponse
from fsspec.implementations.cached import WholeFileCacheFileSystem
from fsspec.implementations.http import HTTPFileSystem as FsHTTPFileSystem
from fsspec.registry import register_implementation as fs_register_implementation
from upath import UPath
from upath.implementations.http import HTTPPath as _HTTPPath
from upath.implementations.http import _HTTPAccessor
from upath.registry import register_implementation

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any
    from urllib.parse import SplitResult

    from upath.core import PT


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


class CachingHTTPAccessor(_HTTPAccessor):
    """A :py:module:`universal_pathlib` accessor which caches content."""

    def __init__(self, parsed_url: SplitResult | None, **kwargs: Any) -> None:
        """Load a caching filesystem."""
        cls = WholeFileCacheFileSystem
        assert parsed_url is not None
        url_kwargs = cls._get_kwargs_from_urls(urlunsplit(parsed_url))
        url_kwargs.update(kwargs)
        url_kwargs.setdefault("target_protocol", "http")
        # url_kwargs.setdefault(
        #     "cache_storage", str(Path(user_cache_dir("euporie")) / "web")
        # )
        self._fs = cls(**url_kwargs)

    def _format_path(self, path: upath.UPath) -> str:
        if (url := path._url) is not None:
            return url.geturl()
        return super()._format_path(path)


class HTTPPath(_HTTPPath):
    """An HTTP path which caches content."""

    _hash: int
    _default_accessor = CachingHTTPAccessor

    def __truediv__(self: PT, key: str | PathLike) -> PT:
        """Join a path to a HTTP URI."""
        return self.__class__(urljoin(str(self), str(key)))

    def __str__(self) -> str:
        """Represent the path as a string."""
        try:
            return self._str
        except AttributeError:
            if url := self._url:
                self._str = url.geturl()
            else:
                return super().__str__()
            return self._str

    def __hash__(self) -> int:
        """Provide a unique hash of the path."""
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._url)
            return self._hash


class _DataAccessor(upath.core._FSSpecAccessor):
    def _format_path(self, path: upath.core.UPath) -> str:
        """Return the full URI as a string."""
        return str(path)


class DataPath(upath.core.UPath):
    """A :py:class:`pathlib` compatible class for reading data URIs."""

    _default_accessor = _DataAccessor


register_implementation("data", DataPath, clobber=True)
register_implementation("http", HTTPPath, clobber=True)
register_implementation("https", HTTPPath, clobber=True)


def parse_path(path: str | PathLike, resolve: bool = True) -> Path:
    """Parse and resolve a path."""
    if not isinstance(path, Path):
        path = UPath(path)
    with contextlib.suppress(NotImplementedError):
        path = path.expanduser()
    if resolve:
        try:
            path = path.resolve()
        except (AttributeError, NotImplementedError, Exception):
            log.info("Path %s not resolvable", path)
    return path
