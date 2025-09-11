"""Contain functions which convert data to base64 format."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from euporie.core.convert.registry import register

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.convert.datum import Datum


@register(from_="png", to="base64-png", filter_=True)
@register(from_="jpeg", to="base64-jpeg", filter_=True)
@register(from_="pdf", to="base64-pdf", filter_=True)
@register(from_="svg", to="base64-svg", filter_=True)
async def bytes_to_base64_py(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert bytes to base64 encoded data."""
    data = datum.data
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode().replace("\n", "").strip()
