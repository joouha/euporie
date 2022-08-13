"""Test cases for :py:mod:`euporie.core.formatted_text.html` module."""

from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import to_plain_text

from euporie.core.formatted_text.html import HTML


def test_inline_whitespace() -> "None":
    """Whitespace between inline elements is correctly collapsed."""
    data = "a b  c \n d"
    ft = to_formatted_text(HTML(data))
    assert to_plain_text(ft) == "a b c d"
