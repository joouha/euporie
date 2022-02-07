"""Contains function which convert base64 encoded strings to other formats."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from euporie.convert.base import register

if TYPE_CHECKING:
    from typing import Optional


@register(
    from_="base64",
    to="png",
    filter_=True,
)
@register(
    from_="base64",
    to="jpg",
    filter_=True,
)
def base64_to_bytes_py(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Converts base64 encoded data to bytes."""
    return base64.b64decode(data)


@register(
    from_="png",
    to="base64",
    filter_=True,
)
@register(
    from_="jpg",
    to="base64",
    filter_=True,
)
def bytes_to_base64_py(
    data: "bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts bytes to base64 encoded data."""
    return base64.b64encode(data).decode().replace("\n", "").strip()
