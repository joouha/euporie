"""Contain various data format conversion functions.

They are grouped into sub-modules based on output format.
"""

from . import (
    ansi,
    base64,
    ft,
    html,
    jpeg,
    markdown,
    pdf,
    pil,
    png,
    rich,
    sixel,
    svg,
)

__all__ = [
    "BASE64_FORMATS",
    "ansi",
    "base64",
    "ft",
    "html",
    "jpeg",
    "markdown",
    "pdf",
    "pil",
    "png",
    "rich",
    "sixel",
    "svg",
]

BASE64_FORMATS = {"png", "jpeg", "pdf", "gif"}
