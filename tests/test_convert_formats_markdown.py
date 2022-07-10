"""Test cases for :py:mod:`euporie.convert.formats.markdown` module."""

from euporie.core.convert.formats.markdown import html_to_markdown_py_html2text


def test_loading_base64_url() -> "None":
    """Tables with an empty first cell are correctly converted."""
    data = "<table><tr><td></td><td>A</td></tr></table>"
    result = html_to_markdown_py_html2text(data)
    stripped_result = "".join(result.split())

    assert stripped_result == "||A|---|---"
