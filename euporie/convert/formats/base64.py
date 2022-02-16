"""Contains functions which convert data to base64 format."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from euporie.convert.base import register

if TYPE_CHECKING:
    from typing import Optional, Union


@register(
    from_="png",
    to="base64-png",
    filter_=True,
)
@register(
    from_="jpeg",
    to="base64-jpeg",
    filter_=True,
)
@register(
    from_="pdf",
    to="base64-pdf",
    filter_=True,
)
@register(
    from_="svg",
    to="base64-svg",
    filter_=True,
)
def bytes_to_base64_py(
    data: "Union[str, bytes]",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts bytes to base64 encoded data."""
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode().replace("\n", "").strip()
