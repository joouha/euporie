"""Responsible for loading data from urls."""

from __future__ import annotations

import base64
import binascii
import contextlib
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, overload
from urllib.parse import unquote, urljoin, urlunsplit

import upath
from aiohttp.client_reqrep import ClientResponse
from fsspec.implementations.cached import WholeFileCacheFileSystem
from fsspec.implementations.http import HTTPFileSystem as FsHTTPFileSystem
from fsspec.registry import register_implementation as fs_register_implementation
from upath import UPath
from upath.implementations.http import HTTPPath as _HTTPPath
from upath.implementations.http import _HTTPAccessor
from upath.registry import _registry

if TYPE_CHECKING:
    from io import BufferedRandom, BufferedReader, BufferedWriter, FileIO, TextIOWrapper
    from os import PathLike
    from typing import IO, Any, BinaryIO, Literal
    from urllib.parse import SplitResult

    from _typeshed import (
        OpenBinaryMode,
        OpenBinaryModeReading,
        OpenBinaryModeUpdating,
        OpenBinaryModeWriting,
        OpenTextMode,
    )
    from upath.core import PT


log = logging.getLogger(__name__)


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


def _raise_for_status(self: ClientResponse) -> None:
    """Monkey-patch :py:class:`aiohttp.ClientResponse` not to raise for any status."""


setattr(ClientResponse, "raise_for_status", _raise_for_status)  # noqa B010


class DataPath(upath.core.UPath):
    """A :py:class:`pathlib` compatible class for reading data URIs."""

    @overload
    def open(
        self,
        mode: OpenTextMode = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> TextIOWrapper:
        ...

    # Unbuffered binary mode: returns a FileIO
    @overload
    def open(
        self,
        mode: OpenBinaryMode,
        buffering: Literal[0],
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> FileIO:
        ...

    # Buffering is on: return BufferedRandom, BufferedReader, or BufferedWriter
    @overload
    def open(
        self,
        mode: OpenBinaryModeUpdating,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> BufferedRandom:
        ...

    @overload
    def open(
        self,
        mode: OpenBinaryModeWriting,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> BufferedWriter:
        ...

    @overload
    def open(
        self,
        mode: OpenBinaryModeReading,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> BufferedReader:
        ...

    # Buffering cannot be determined: fall back to BinaryIO
    @overload
    def open(
        self,
        mode: OpenBinaryMode,
        buffering: int = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> BinaryIO:
        ...

    # Fallback if mode is not specified
    @overload
    def open(
        self,
        mode: str,
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]:
        ...

    def open(
        self,
        mode: OpenTextMode
        | OpenBinaryMode
        | OpenBinaryModeReading
        | OpenBinaryModeWriting
        | OpenBinaryModeUpdating
        | str = "r",
        buffering: Literal[-1, 0, 1] | int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]:
        """Return an io object for the data in the URI."""
        assert self._url is not None
        data_format, _, encoded_data = self._url.path.partition(",")
        _mime, *params = data_format.split(";")

        data_bytes = None
        data_str = None

        if "base64" in params:
            try:
                data_bytes = base64.b64decode(encoded_data)
            except binascii.Error:
                log.warning("Failed to decode base64 encoded data")
                data_bytes = b""
        else:
            data_str = unquote(encoded_data)

        if "b" in mode:
            if data_bytes is None:
                assert data_str is not None
                data_bytes = data_str.encode()
            return io.BytesIO(data_bytes)
        else:
            if data_str is None:
                assert data_bytes is not None
                # decode_kwargs: dict[str, str] = {}
                # if encoding is not None:  #:= kwargs.get("encoding"):
                # decode_kwargs["encoding"] = str(encoding)
                data_str = data_bytes.decode()  # **decode_kwargs)
            return io.StringIO(data_str)

    def exists(self, **kwargs: Any) -> bool:
        """Affirm that data URIs always exist."""
        return True

    @property
    def _mime(self) -> str:
        """Return the media type of the data URI."""
        assert self._url is not None
        data_format, _, _encoded_data = self._url.path.partition(",")
        mime, *params = data_format.split(";")
        return mime


_registry.known_implementations["data"] = "euporie.core.path.DataPath"


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


_registry.known_implementations["http"] = "euporie.core.path.HTTPPath"
_registry.known_implementations["https"] = "euporie.core.path.HTTPPath"


class HTTPFileSystem(FsHTTPFileSystem):
    """A :py:class:`HTTPFileSystem` which does not raise exceptions on 404 errors."""

    def _raise_not_found_for_status(self, response: ClientResponse, url: str) -> None:
        """Do not raise an exception for 404 errors."""


fs_register_implementation("http", HTTPFileSystem, clobber=True)
fs_register_implementation("https", HTTPFileSystem, clobber=True)
