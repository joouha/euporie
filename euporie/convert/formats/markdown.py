"""Contains functions which convert data to markdown format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.convert.base import register
from euporie.convert.util import have_modules

if TYPE_CHECKING:
    from typing import Optional


@register(
    from_="html",
    to="markdown",
    filter_=have_modules("mtable", "html5lib"),
)
def html_to_markdown_py_mtable(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert HTML tables to markdown tables using :py:mod:`mtable`."""
    from mtable import MarkupTable  # type: ignore

    return "\n\n".join([table.to_md() for table in MarkupTable.from_html(data)])
