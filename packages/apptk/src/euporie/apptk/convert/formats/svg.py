"""Contain function which convert data to SVG format."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from euporie.apptk.convert.formats.common import (
    mermaid_cli_cmd,
    mermaid_rs_renderer_cmd,
)
from euporie.apptk.convert.registry import register
from euporie.apptk.filters.environment import command_exists, have_modules

if TYPE_CHECKING:
    from typing import Any

    from euporie.apptk.convert.datum import Datum


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


register(
    from_=("mermaid"),
    to="svg",
    filter_=command_exists("mmdr"),
)(partial(mermaid_rs_renderer_cmd, "svg"))

register(
    from_=("mermaid"),
    to="svg",
    filter_=command_exists("mmdc"),
)(partial(mermaid_cli_cmd, "svg"))
