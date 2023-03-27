"""Test cases for :py:mod:`euporie.url` module."""

from euporie.core.path import DataPath


def test_loading_base64_url() -> "None":
    """Decodes a base64 data-url."""
    url = "data:text/plain;base64,VGhpcyBpcyBhIHRlc3Q="
    assert DataPath(url).read_bytes() == b"This is a test"
