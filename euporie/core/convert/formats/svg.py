"""Contain function which convert data to SVG format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core.convert.registry import register
from euporie.core.convert.utils import have_modules

if TYPE_CHECKING:
    from euporie.core.convert.datum import Datum


@register(from_="latex", to="svg", filter_=have_modules("ziamath"))
async def latex_to_svg_py_ziamath(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    extend: bool = True,
) -> str:
    """Convert LaTeX to SVG using :py:mod:`ziamath`."""
    import ziamath as zm

    data = datum.data.strip()
    if not data.startswith("$"):
        data = f"$${data}$$"
    latex = zm.Text(data, color=datum.fg, size=12)
    return latex.svg()
