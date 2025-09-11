"""Contain function which convert data to SVG format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core.convert.registry import register
from euporie.core.filters import have_modules

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.convert.datum import Datum


@register(from_="latex", to="svg", filter_=have_modules("ziamath"))
async def latex_to_svg_py_ziamath(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert LaTeX to SVG using :py:mod:`ziamath`."""
    import ziamath as zm

    data = datum.data.strip()
    if not data.startswith("$"):
        data = f"$${data}$$"
    latex = zm.Text(data, color=fg, size=12)
    return latex.svg()
