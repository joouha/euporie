"""Contains functions which convert data to markdown format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.core.convert.base import register
from euporie.core.convert.utils import have_modules

if TYPE_CHECKING:
    from typing import Optional

    from upath import UPath

log = logging.getLogger(__name__)

_HTML2TEXT_TABLE_RE = r"(?:(?:.*\|)+[^|]*?(?:\n|$))+"


@register(
    from_="html",
    to="markdown",
    filter_=have_modules("html2text"),
)
def html_to_markdown_py_html2text(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "str":
    """Convert HTML to markdown tables using :py:mod:`html2text`."""
    import re

    from html2text import HTML2Text

    parser = HTML2Text(bodywidth=0)
    markup = data.decode() if isinstance(data, bytes) else data
    result = parser.handle(markup)

    # Fix for html2text issue with empty first cells in table rows
    remaining_result = result
    replaced = ""
    for match in re.finditer(_HTML2TEXT_TABLE_RE, result, re.MULTILINE):
        # Add string before the table
        replaced += remaining_result[
            : match.start() - (len(result) - len(remaining_result))
        ]
        remaining_result = result[match.end() :]
        table = result[match.start() : match.end()]
        table_rows = table.strip().split("\n")
        row_lens = [len(row.split("|")) for row in table_rows]
        max_row_len = max(row_lens)
        table = "\n".join(
            "|" * (max_row_len - row_lens[i] + 1) + row
            for i, row in enumerate(table_rows)
        )
        replaced += table + "\n"
    replaced += remaining_result
    result = replaced

    return result


@register(
    from_="html",
    to="markdown",
    filter_=have_modules("mtable", "html5lib"),
)
def html_to_markdown_py_mtable(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "str":
    """Convert HTML tables to markdown tables using :py:mod:`mtable`."""
    from mtable import MarkupTable

    markup = data.decode() if isinstance(data, bytes) else data
    return "\n\n".join([table.to_md() for table in MarkupTable.from_html(markup)])
