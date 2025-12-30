"""Test cases for :py:mod:`euporie.apptk.formatted_text.html` module."""

from __future__ import annotations

from euporie.apptk.formatted_text.base import to_formatted_text

from euporie.apptk.formatted_text.html import HTML
from euporie.apptk.formatted_text.utils import to_plain_text


def test_inline_whitespace() -> None:
    """Whitespace between inline elements is correctly collapsed."""
    data = "a b  c \n d\ne"
    expected = "a b c d e"
    result = to_plain_text(to_formatted_text(HTML(data, width=9)))
    assert result == expected


def test_inline_block_whitespace() -> None:
    """Whitespace is collapsed between two inline elements."""
    data = '<span style="display: inline-block">X</span> Y'
    expected = "X Y"
    result = to_plain_text(HTML(data, width=3))
    assert result == expected


def test_nested_list_linebreaks() -> None:
    """There are no extra linebreaks in nested lists."""
    data = "<ol><li>a<ul><li>a</li><li>b</li></ul></li><li>b</li></ol>"
    expected = "        \n 1. a   \n     ○ a\n     ○ b\n 2. b   \n        "
    result = to_plain_text(HTML(data, width=8))
    assert result == expected

    data = "<ul><li>a<ol><li>a</li><li>b</li></ol></li><li>b</li></ul>"
    expected = "        \n • a    \n    1. a\n    2. b\n • b    \n        "
    result = to_plain_text(HTML(data, width=8))
    assert result == expected


def test_hidden() -> None:
    """Text with ``visibility: hidden`` is rendered as spaces."""
    data = '<u style="visibility:hidden">a</u>'
    result = to_formatted_text(HTML(data, width=1))
    style, text, *_ = result[0]
    # Hidden attribute is applied
    assert "hidden" in style
    # Text is still rendered
    assert text[0] == "a"
    # Underline attribute is disabled for hidden text
    assert style.find("nounderline") > style.find("underline")


def test_blink() -> None:
    """Text with ``text-decoration: blink`` is rendered as spaces."""
    data = '<span style="text-decoration: blink">a</span>'
    result = to_formatted_text(HTML(data, width=1))
    style, _text, *_ = result[0]
    # Hidden attribute is applied
    assert "blink" in style


def test_hidden_underline_removal() -> None:
    """Underline attribute should be removed from hidden elements."""
    data = 'a <u style="visibility:hidden">b</u> c'
    result = HTML(data, width=5).formatted_text
    assert "underline" not in {x[0] for x in result}


def test_text_wrapping() -> None:
    """Text wraps a word boundaries."""
    data = "aa bb cc"
    expected = "aa bb  \ncc     "
    result = to_plain_text(HTML(data, width=7))
    assert result == expected


def test_inline_element_wrapping() -> None:
    """Text in inline elements is wrapped."""
    data = "aa <span>bb cc dd</span>"
    expected = "aa bb \ncc dd "
    result = to_plain_text(HTML(data, width=6))
    assert result == expected


def test_enclosed_paragraph_newlines() -> None:
    """Enclosed an unenclosed paragraph margins are consistent."""
    data = "<p>a</p><p>b</b><p>c</p>"
    expected = to_plain_text(HTML(f"<div>{data}</div>", width=3))
    result = to_plain_text(HTML(f"{data}", width=3))
    assert result == expected


def test_single_hr() -> None:
    """A single <hr> has its margins stripped."""
    data = "<hr>"
    expected = "   \n───\n   "
    result = to_plain_text(HTML(data, width=3))
    assert result == expected


def test_nested_block_margins() -> None:
    """Margins collapse when no content separates parent and descendants."""
    data = "<hr><div><hr></div><hr>"
    expected = " \n─\n \n─\n \n─\n "
    result = to_plain_text(HTML(data, width=1))
    assert result == expected


def test_details_summary() -> None:
    """A <summary> renders as expected."""
    data = "<details open=''><summary>a a a</summary>b b b</details>"
    expected = "▼ a a a\nb b b  "
    result = to_plain_text(HTML(data, width=7))
    assert result == expected


def test_multiple_css_selectors() -> None:
    """Comma separated CSS selectors are interpreted."""
    data = '<style>.a,.b{font_weight: bold}</style><span class="a">a</span><span class="b">b</span>'
    result = to_formatted_text(HTML(data, width=2))
    assert all("bold" in x[0].split() for x in result)


def test_inline_block_wrapping() -> None:
    """Inline block inside inline elements should be wrapped like text."""
    data = 'A B <span style="display:inline-block">X<br>Y</span> C D'
    ft = to_formatted_text(HTML(data, width=4))
    result = [x.strip() for x in to_plain_text(ft).splitlines()]
    assert result == ["A B", "X", "Y C", "D"]
