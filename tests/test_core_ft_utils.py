"""Various unit tests for formatted text utility functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text.base import FormattedText as Ft
from prompt_toolkit.formatted_text.utils import to_plain_text

from euporie.core.data_structures import DiBool
from euporie.core.ft import utils

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples


def test_fragment_list_width() -> None:
    """Test for utils.fragment_list_width function."""
    ft = Ft([("", "AB")])
    length = utils.fragment_list_width(ft)
    assert length == 2

    ft = Ft([("", "A"), ("", "B")])
    length = utils.fragment_list_width(ft)
    assert length == 2

    ft = Ft([("", "A"), ("[ZeroWidthEscape]", "B"), ("", "C")])
    length = utils.fragment_list_width(ft)
    assert length == 2

    ft = Ft([("", "A"), ("[ReverseOverwrite]", "B"), ("", "C")])
    length = utils.fragment_list_width(ft)
    assert length == 2

    ft = Ft([("", "⭐")])
    length = utils.fragment_list_width(ft)
    assert length == 2


def test_max_line_width() -> None:
    """Test for utils.max_line_width function."""
    ft = Ft([("", "AAAAA\nBBBB\nCCC")])
    length = utils.max_line_width(ft)
    assert length == 5

    ft = Ft([("", "A\n"), ("", "BB"), ("", "\nCCC")])
    width = utils.max_line_width(ft)
    assert width == 3

    ft = Ft([("", "A\n"), ("", "BB"), ("[ZeroWidthEscape]", "\nCCC")])
    width = utils.max_line_width(ft)
    assert width == 2

    ft = Ft([("", "A\n"), ("", "⭐")])
    width = utils.max_line_width(ft)
    assert width == 2


def test_last_char() -> None:
    """Test for utils.last_char function."""
    ft = Ft([("", "A\n"), ("", "BB"), ("", "\nCCC")])
    last = utils.last_char(ft)
    assert last == "C"


def test_fragment_list_to_words() -> None:
    """Test for utils.fragment_list_to_words function."""
    ft = Ft([("fg -> None:red", "This is"), ("fg -> None:blue", " an example")])
    words = list(utils.fragment_list_to_words(ft))
    assert words == [
        [("fg -> None:red", "This ")],
        [("fg -> None:red", "is"), ("fg -> None:blue", " ")],
        [("fg -> None:blue", "an ")],
        [("fg -> None:blue", "example")],
    ]


def test_apply_style() -> None:
    """Test for utils.apply_style function."""
    ft = Ft([("class:foo", "A"), ("class:bar", "B")])
    styled_ft = utils.apply_style(ft, "class:baz")
    assert styled_ft == [
        ("class:foo class:baz", "A"),
        ("class:bar class:baz", "B"),
    ]


def test_strip() -> None:
    """Test for utils.strip function."""
    ft = Ft([("class:foo", "   A  "), ("class:bar", " B  ")])
    stripped_ft = utils.strip(ft, chars=None)
    assert stripped_ft == [
        ("class:foo", "A  "),
        ("class:bar", " B"),
    ]


def test_strip_one_trailing_newline() -> None:
    """Test for utils.strip_one_trailing_newline function."""
    ft = Ft([("", "A\n"), ("", "B")])
    stripped_ft = utils.strip_one_trailing_newline(ft)
    assert stripped_ft == [("", "A\n"), ("", "B")]

    ft = Ft([("", "A\n"), ("", "B\n")])
    stripped_ft = utils.strip_one_trailing_newline(ft)
    assert stripped_ft == [("", "A\n"), ("", "B")]

    ft = Ft([("", "A\n"), ("", "B\n\n\n")])
    stripped_ft = utils.strip_one_trailing_newline(ft)
    assert stripped_ft == [("", "A\n"), ("", "B\n\n")]


def test_truncate() -> None:
    """Test for utils.truncate function."""
    ft = Ft([("class:foo", "This is a long sentence")])
    truncated_ft = utils.truncate(ft, 12, placeholder="...")
    assert truncated_ft == [
        ("class:foo", "This is a"),
        ("class:foo", "..."),
    ]
    assert utils.fragment_list_width(truncated_ft) == 12

    ft = Ft([("class:foo", "This is a long sentence")])
    truncated_ft = utils.truncate(ft, 12, style="class:bar", placeholder="...")
    assert truncated_ft == [
        ("class:foo", "This is a"),
        ("class:bar", "..."),
    ]


def test_substring() -> None:
    """Test for utils.substring function."""
    ft = Ft([("", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")])
    sub_ft = utils.substring(ft, start=23)
    assert sub_ft == [("", "XYZ")]
    sub_ft = utils.substring(ft, end=3)
    assert sub_ft == [("", "ABC")]
    sub_ft = utils.substring(ft, start=9, end=13)
    assert sub_ft == [("", "JKLM")]


def test_wrap() -> None:
    """Test for utils.wrap function."""
    ft = Ft([("class:foo", "This is a long sentence")])
    wrapped_ft = utils.wrap(ft, 7, style="class:baz", placeholder="...")
    assert wrapped_ft == [
        ("class:foo", "This "),
        ("", "\n"),
        ("class:foo", "is "),
        ("class:foo", "a "),
        ("", "\n"),
        ("class:foo", "long "),
        ("", "\n"),
        ("class:foo", "sent"),
        ("class:baz", "..."),
    ]


def test_align() -> None:
    """Test for utils.align function."""
    ft = Ft(
        [
            ("class:foo", "A\n"),
            ("class:bar", "BB\n"),
            ("class:baz", "CCC"),
        ]
    )
    aligned_ft = utils.align(
        ft,
        how=utils.FormattedTextAlign.CENTER,
        width=20,
        style="class:qux",
    )
    assert aligned_ft == [
        ("class:qux nounderline", "         "),
        ("class:foo", "A"),
        ("class:qux nounderline", "          "),
        ("class:qux nounderline", "\n"),
        ("class:qux nounderline", "         "),
        ("class:foo", ""),
        ("class:bar", "BB"),
        ("class:qux nounderline", "         "),
        ("class:qux nounderline", "\n"),
        ("class:qux nounderline", "        "),
        ("class:bar", ""),
        ("class:baz", "CCC"),
        ("class:qux nounderline", "         "),
    ]


def test_valign() -> None:
    """Test for utils.valign function."""
    ft = Ft([("", "A")])
    aligned = to_plain_text(
        utils.valign(ft, how=utils.FormattedTextVerticalAlign.TOP, height=3)
    )
    assert aligned == "A\n \n "

    aligned = to_plain_text(
        utils.valign(ft, how=utils.FormattedTextVerticalAlign.MIDDLE, height=3)
    )
    assert aligned == " \nA\n "

    aligned = to_plain_text(
        utils.valign(ft, how=utils.FormattedTextVerticalAlign.BOTTOM, height=3)
    )
    assert aligned == " \n \nA"

    ft = Ft([("class:foo", "A\n"), ("class:bar", "B")])
    aligned_ft = utils.valign(
        ft,
        how=utils.FormattedTextVerticalAlign.MIDDLE,
        height=5,
        style="class:baz",
    )
    assert aligned_ft == [
        ("class:baz", " \n"),
        ("class:foo", "A\n"),
        ("class:bar", "B"),
        ("class:baz", "\n \n "),
    ]


def test_join_lines() -> None:
    """Test for utils.join_lines function."""
    lines: list[StyleAndTextTuples] = [
        [("class:foo", "Sample"), ("class:bar", "Text")],
        [("class:baz", "Python"), ("class:qux", "Rocks")],
    ]
    joined = utils.join_lines(lines)
    assert joined == [
        ("class:foo", "Sample"),
        ("class:bar", "Text"),
        ("", "\n"),
        ("class:baz", "Python"),
        ("class:qux", "Rocks"),
    ]


def test_pad() -> None:
    """Test for utils.pad function."""
    ft = Ft(
        [
            ("class:a", "AAA"),
            ("class:b", "\nBB"),
            ("class:c", "\nC"),
        ]
    )
    padded_ft = utils.pad(ft, width=5, char=" ", style="class:padding")
    assert padded_ft == [
        ("class:a", "AAA"),
        ("class:padding nounderline", "  "),
        ("", "\n"),
        ("class:b", "BB"),
        ("class:padding nounderline", "   "),
        ("", "\n"),
        ("class:c", "C"),
        ("class:padding nounderline", "    "),
    ]


def test_paste() -> None:
    """Test for utils.paste function."""
    bottom_ft = Ft([("class:foo", "ABC"), ("class:bar", "DEF")])
    top_ft = Ft([("class:baz", "XYZ")])
    pasted_ft = utils.paste(top_ft, bottom_ft, row=0, col=2, transparent=False)
    assert pasted_ft == [("class:foo", "AB"), ("class:baz", "XYZ"), ("class:bar", "F")]


def test_concat() -> None:
    """Concatenating formatted text results in correct placements."""
    ft_a = Ft([])
    ft_b = Ft([])
    result = utils.concat(ft_a, ft_b, 0, 0)
    assert result == ([], 0)

    ft_a = Ft([("class:a", "line1\n"), ("class:b", "line2")])
    ft_b = Ft([("class:c", "line3\n"), ("class:d", "line4")])
    result_ft, result_baseline = utils.concat(ft_a, ft_b, 0, 1)
    assert to_plain_text(result_ft) == "     line3\nline1line4\nline2"
    assert result_baseline == 1

    result_ft, result_baseline = utils.concat(ft_a, ft_b, 0, 2)
    assert to_plain_text(result_ft) == "     line3\n     line4\nline1\nline2"
    assert result_baseline == 2

    result_ft, result_baseline = utils.concat(ft_a, ft_b, 1, 0)
    assert to_plain_text(result_ft) == "line1\nline2line3\n     line4"
    assert result_baseline == 1

    result_ft, result_baseline = utils.concat(ft_a, ft_b, 2, 0)
    assert to_plain_text(result_ft) == "line1\nline2\n     line3\n     line4"
    assert result_baseline == 2


def test_indent() -> None:
    """Formatted text is indented as expected."""
    ft = Ft([("fg:red", "A b c d")])
    result = utils.indent(ft, margin="#", style="fg:blue")
    assert result == [("fg:blue", "#"), ("fg:red", "A b c d")]

    ft = Ft([("", "A b\nc d")])
    result = utils.indent(ft, margin="#", skip_first=True)
    assert to_plain_text(result) == "A b\n#c d"


def test_add_border() -> None:
    """Borders are added around formatted text."""
    ft = Ft([("", "A")])

    result = to_plain_text(utils.add_border(ft))
    assert result == "┌─┐\n│A│\n└─┘"

    result = to_plain_text(utils.add_border(ft, width=5))
    assert result == "┌───┐\n│A  │\n└───┘"

    result = to_plain_text(utils.add_border(ft, padding=1))
    assert result == "┌───┐\n│   │\n│ A │\n│   │\n└───┘"

    result = to_plain_text(
        utils.add_border(ft, border_visibility=DiBool(False, True, False, True))
    )
    assert result == "│A│"

    result = to_plain_text(
        utils.add_border(ft, border_visibility=DiBool(True, False, True, False))
    )
    assert result == "─\nA\n─"


def test_apply_reverse_overwrites() -> None:
    """Applying reverse overwrites replaces previous characters."""
    ft = Ft([("", "ABCD"), ("[ReverseOverwrite]", "XYZ"), ("", "EFG")])
    result = utils.apply_reverse_overwrites(ft)
    assert result == [("", "A"), ("", "XYZ"), ("", "EFG")]
