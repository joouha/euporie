# -*- coding: utf-8 -*-
"""Test cases for __init__ module."""
from euporie import __version__


def test_version() -> None:
    """Version is correct."""
    assert __version__ == "0.1.11"
