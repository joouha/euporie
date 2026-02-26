"""Test cases for :py:mod:`euporie.convert.formats.markdown` module."""

from __future__ import annotations

import pytest
from apptk.convert.datum import Datum

try:
    from apptk.convert.formats.markdown import html_to_markdown_py_html2text

    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False


@pytest.mark.skipif(not HAS_HTML2TEXT, reason="html2text not installed")
async def test_html_to_markdown_py_html2text_table_empty_cells() -> None:
    """Tables with an empty first cell are correctly converted."""
    data = "<table><tr><td></td><td>A</td></tr></table>"
    result = await html_to_markdown_py_html2text(Datum(data, format="html"))
    stripped_result = "".join(result.split())

    assert stripped_result == "||A|---|---"
