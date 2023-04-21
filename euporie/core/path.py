"""Responible for loading data from urls."""

from __future__ import annotations

import base64
import binascii
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, overload
from urllib.parse import urlunsplit

import upath
from appdirs import user_cache_dir
from fsspec.implementations.cached import WholeFileCacheFileSystem
from upath.implementations.http import HTTPPath, _HTTPAccessor
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


log = logging.getLogger(__name__)


def parse_path(path: str | PathLike) -> Path:
    """Parse and resolve a path."""
    if not isinstance(path, Path):
        path = UPath(path)
    try:
        path = path.expanduser()
    except NotImplementedError:
        pass
    try:
        path = path.resolve()
    except (AttributeError, NotImplementedError):
        pass
    return path


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
            data_str = encoded_data

        if "b" in mode:
            if data_bytes is None:
                assert data_str is not None
                data_bytes = data_str.encode()
            return io.BytesIO(data_bytes)
        else:
            if data_str is None:
                assert data_bytes is not None
                decode_kwargs: dict[str, str] = {}
                if encoding is not None:  #:= kwargs.get("encoding"):
                    decode_kwargs["encoding"] = str(encoding)
                data_str = data_bytes.decode(**decode_kwargs)
            return io.StringIO(data_str)

    @property
    def _mime(self) -> str:
        """Return the media type of the data URI."""
        assert self._url is not None
        data_format, _, _encoded_data = self._url.path.partition(",")
        mime, *params = data_format.split(";")
        return mime


_registry.known_implementations["data"] = "euporie.core.path.DataPath"


# Patch UPath to cache http requests


class CachingHTTPAccessor(_HTTPAccessor):
    """A :py:module:`universal_pathlib` accrssor which caches content."""

    def __init__(self, parsed_url: SplitResult | None, **kwargs: Any) -> None:
        """Load a caching filesystem."""
        cls = WholeFileCacheFileSystem
        assert parsed_url is not None
        url_kwargs = cls._get_kwargs_from_urls(urlunsplit(parsed_url))
        url_kwargs.update(kwargs)
        url_kwargs.setdefault("target_protocol", "http")
        url_kwargs.setdefault(
            "cache_storage", str(Path(user_cache_dir("euporie")) / "web")
        )
        self._fs = cls(**url_kwargs)

    def _format_path(self, path: upath.UPath) -> str:
        if (url := path._url) is not None:
            return url.geturl()
        return super()._format_path(path)


class CachingHTTPPath(HTTPPath):
    """An HTTP path which caches content."""

    _default_accessor = CachingHTTPAccessor


_registry.known_implementations["http"] = "euporie.core.path.CachingHTTPPath"
_registry.known_implementations["https"] = "euporie.core.path.CachingHTTPPath"
