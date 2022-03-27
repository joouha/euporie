"""Contains functions which convert data to markdown format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.convert.base import register
from euporie.convert.util import have_modules

if TYPE_CHECKING:
    from typing import Optional

log = logging.getLogger(__name__)

_HTML2TEXT_TABLE_FIRST_CELL_RE = r"^((\|\s+[^\|]+\s+)((\|\s+[^\|]+\s+|:?-+:?\|)(\|\s+[^\|]+\s+|:?-+:?\|))*:?-+:?\|:?-+:?\s*$)"  # noqa B950


@register(
    from_="html",
    to="markdown",
    filter_=have_modules("html2text"),
)
def html_to_markdown_py_html2text(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert HTML to markdown tables using :py:mod:`html2text`."""
    import re

    from html2text import HTML2Text  # type: ignore

    parser = HTML2Text()
    result = parser.handle(data)

    # Fix for html2text issue with empty first cells in tables
    # https://github.com/Alir3z4/html2text/pull/380
    result = re.sub(_HTML2TEXT_TABLE_FIRST_CELL_RE, r"|  \1", result, 0, re.MULTILINE)

    return result


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
