"""Contain main format conversion function."""

from __future__ import annotations

import logging
import mimetypes
from functools import lru_cache
from typing import TYPE_CHECKING

from upath import UPath
from upath._stat import UPathStatResult
from upath.implementations.http import HTTPPath

if TYPE_CHECKING:
    from pathlib import Path


log = logging.getLogger(__name__)


MIME_FORMATS = {
    "image/svg+xml": "svg",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/gif": "gif",
    "application/pdf": "pdf",
    "text/html": "html",
    "text/latex": "latex",
    "application/x-latex": "latex",
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
    "text/*": "ansi",
    "stream/std*": "ansi",
    "*": "ansi",
}


@lru_cache
def get_mime(path: Path | str) -> str | None:
    """Attempt to determine the mime-type of a path."""
    if isinstance(path, str):
        path = UPath(path)
    try:
        path = path.resolve()
    except Exception:
        log.debug("Cannot resolve '%s'", path)

    mime = None

    # Read from path of data URI
    if path.exists() and isinstance(stat := path.stat(), UPathStatResult):
        mime = stat.as_info().get("mimetype")

    # If we have a web-address, ensure we have a url
    # Check http-headers and ensure we have a url
    if not mime and isinstance(path, HTTPPath) and path._url is not None:
        from fsspec.asyn import sync

        # Get parsed url
        url = path._url.geturl()
        # Get the fsspec fs
        fs = path.fs
        # Ensure we have a session
        session = sync(fs.loop, fs.set_session)
        # Use HEAD requests if the server allows it, falling back to GETs
        for method in (session.head, session.get):
            r = sync(fs.loop, method, url, allow_redirects=True)
            try:
                r.raise_for_status()
            except Exception:
                log.debug("Request failed: %s", r)
                continue
            else:
                content_type = r.headers.get("Content-Type")
                if content_type is not None:
                    mime = content_type.partition(";")[0]
                    break
    # Try using magic
    if not mime:
        try:
            import magic
        except ModuleNotFoundError:
            pass
        else:
            try:
                with path.open(mode="rb") as f:
                    mime = magic.from_buffer(f.read(2048), mime=True)
            except FileNotFoundError:
                pass

    # Guess from file-extension
    if not mime and path.suffix:
        # Check for Jupyter notebooks by extension
        if path.suffix == ".ipynb":
            return "application/x-ipynb+json"
        else:
            mime, _ = mimetypes.guess_type(path)

    return mime


@lru_cache
def get_format(path: Path | str, default: str = "") -> str:
    """Attempt to guess the format of a path."""
    if isinstance(path, str):
        path = UPath(path)
    if not default:
        default = "html" if isinstance(path, HTTPPath) else "ansi"
    mime = get_mime(path)
    return MIME_FORMATS.get(mime, default) if mime else default
