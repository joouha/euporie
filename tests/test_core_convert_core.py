"""Test core format conversion functions."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import magic
from fsspec.implementations.http import HTTPFileSystem
from upath import UPath

from euporie.core.convert.core import get_format, get_mime
from euporie.core.path import HTTPPath

if TYPE_CHECKING:
    from typing import Any


def test_get_mime() -> None:
    """Mime types are identified correctly."""
    # Test data-uris
    assert get_mime("data:text/plain;charset=UTF-8;page=21,the%20data") == "text/plain"
    assert (
        get_mime("data:text/vnd-example+xyz;foo=bar;base64,R0lGODdh")
        == "text/vnd-example+xyz"
    )
    assert (
        get_mime("data:image/jpeg;base64,/9j/4AAQSkZJRgABAgAAZABkAAD") == "image/jpeg"
    )

    # Test getting mime-type from file extension
    assert get_mime("tests/data/notebooks/test.ipynb") == "application/x-ipynb+json"
    assert get_mime("tests/data/images/test.png") == "image/png"
    assert get_mime("tests/data/html/test.html") == "text/html"

    # Test file content using python-magic
    def mock_open_gif(*args: Any, **kwargs: Any) -> BytesIO:
        return BytesIO(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01"
            b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )

    with patch.object(Path, "open", mock_open_gif):
        path = Path("tests/data/images/none")
        assert get_mime(path) == "image/gif"

    # Test http paths
    url = "http://127.0.0.1/path"

    def mock_open_empty(*args: Any, **kwargs: Any) -> BytesIO:
        return BytesIO(b"")

    async def mock_response(*args: Any, **kwargs: Any) -> Any:
        return Mock(url=url, headers={"Content-Type": "image/png"})

    session = MagicMock(head=mock_response, get=mock_response)

    with patch.object(HTTPPath, "open", mock_open_empty):
        with patch.object(magic, "from_buffer", return_value=None):
            with patch.object(HTTPFileSystem, "set_session", return_value=session):
                path = UPath(url)
                assert get_mime(path) == "image/png"


def test_get_format() -> None:
    """Test format detection."""
    assert get_format("tests/data/images/test.png") == "png"
    assert get_format("tests/data/html/test.html") == "html"
    assert get_format("tests/data/text/test.txt") == "ansi"
