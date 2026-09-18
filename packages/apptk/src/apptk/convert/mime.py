"""Contain main format conversion function."""

from __future__ import annotations

import logging
import mimetypes
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


log = logging.getLogger(__name__)


MIME_FORMATS = {
    "image/svg+xml": "svg",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/gif": "gif",
    "application/pdf": "pdf",
    "text/vnd.mermaid": "mermaid",
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
    from upath import UPath
    from upath._stat import UPathStatResult
    from upath.implementations.http import HTTPPath

    if isinstance(path, str):
        path = UPath(path)
    try:
        path = path.resolve()
    except Exception:
        log.debug("Cannot resolve '%s'", path)

    mime = None

    # Read from path of data URI
    try:
        if path.exists() and isinstance(stat := path.stat(), UPathStatResult):
            mime = stat.as_info().get("mimetype")
    except Exception:
        log.debug("Unable to read metadata for '%s'", path)

    # If we have a web-address, ensure we have a url.
    # Check http-headers and ensure we have a url. Network failures (for
    # example being offline) should not crash mime-type detection, so any
    # connection errors are caught and ignored here.
    if not mime and isinstance(path, HTTPPath) and path._url is not None:
        from fsspec.asyn import sync

        # Get parsed url
        url = path._url.geturl()
        # Get the fsspec fs
        fs = path.fs
        # Ensure we have a session
        session = None
        try:
            session = sync(fs.loop, fs.set_session)
        except Exception:
            log.debug("Unable to open a session for '%s'", url)
        # Use HEAD requests if the server allows it, falling back to GETs
        if session is not None:
            for method in (session.head, session.get):
                try:
                    r = sync(fs.loop, method, url, allow_redirects=True)
                except Exception:
                    log.debug("Request to '%s' failed", url)
                    continue
                try:
                    r.raise_for_status()
                except Exception:
                    log.debug("Request to '%s' was unsuccessful", url)
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
            except Exception:
                log.debug("Unable to read '%s' to detect its mime-type", path)

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
    from upath import UPath
    from upath.implementations.http import HTTPPath

    if isinstance(path, str):
        path = UPath(path)
    if not default:
        default = "html" if isinstance(path, HTTPPath) else "ansi"
    mime = get_mime(path)
    return MIME_FORMATS.get(mime, default) if mime else default
