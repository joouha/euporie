"""Contain functions which convert data to base64 format."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from euporie.core.convert.core import register

if TYPE_CHECKING:
    from pathlib import Path


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
async def bytes_to_base64_py(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> str:
    """Convert bytes to base64 encoded data."""
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode().replace("\n", "").strip()
