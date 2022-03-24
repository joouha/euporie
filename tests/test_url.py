"""Test cases for :py:mod:`euporie.url` module."""

from euporie.url import load_url


def test_loading_base64_url() -> "None":
    """Decodes a base64 data-url."""
    url = "data:text/plain;base64,VGhpcyBpcyBhIHRlc3Q="
    assert load_url(url) == b"This is a test"
