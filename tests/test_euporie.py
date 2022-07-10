"""Test cases for __init__ module."""

from euporie.core import __version__


def test_version() -> "None":
    """Version is correct."""
    assert __version__ == "2.0.0-dev"
