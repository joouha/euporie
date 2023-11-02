"""Test cases for :py:mod:`euporie.convert.formats.markdown` module."""

from __future__ import annotations

from euporie.core.convert.datum import Datum
from euporie.core.convert.formats.markdown import html_to_markdown_py_html2text


async def test_html_to_markdown_py_html2text_table_empty_cells() -> None:
    """Tables with an empty first cell are correctly converted."""
    data = "<table><tr><td></td><td>A</td></tr></table>"
    result = await html_to_markdown_py_html2text(Datum(data, format="html"))
    stripped_result = "".join(result.split())

    assert stripped_result == "||A|---|---"
