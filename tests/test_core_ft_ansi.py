"""Test ANSI to formatted text conversion."""

from __future__ import annotations

from prompt_toolkit.formatted_text import to_formatted_text

from euporie.core.ft.ansi import ANSI


def test_ansi_tabs() -> None:
    """Tabs are converted to spaces."""
    value = ANSI("1\t23\t234\t5", tab_size=3)
    assert to_formatted_text(value) == [
        ("", "1"),
        ("", " "),
        ("", " "),
        ("", "2"),
        ("", "3"),
        ("", " "),
        ("", "2"),
        ("", "3"),
        ("", "4"),
        ("", " "),
        ("", " "),
        ("", " "),
        ("", "5"),
    ]


def test_ansi_win_newlines() -> None:
    """Windows newlines are converted to Unix newlines."""
    value = ANSI("a\nb\r\nc")
    assert to_formatted_text(value) == [
        ("", "a"),
        ("", "\n"),
        ("", "b"),
        ("", "\n"),
        ("", "c"),
    ]


def test_ansi_carriage_returns() -> None:
    """Line text preceding carriage returns is removed."""
    value = ANSI("a\nb\rc")
    assert to_formatted_text(value) == [("", "a"), ("", "\n"), ("", "c")]


def test_ansi_remove_hide_show_cursor() -> None:
    """Cursor show/hide commands are removed."""
    value = ANSI("a\x1b[?25hb\x1b[?25lc")
    assert to_formatted_text(value) == [("", "a"), ("", "b"), ("", "c")]


def test_ansi_clear_line() -> None:
    """Line text before clear line commands is removed."""
    value = ANSI("a\nb\x1b[2Kc")
    assert to_formatted_text(value) == [("", "a"), ("", "\n"), ("", "c")]


def test_ansi_zwe() -> None:
    """Escaped text is converted to zero width escape sequence."""
    # Zero width escapes.
    value = ANSI("a\001b\002c")
    assert to_formatted_text(value) == [
        ("", "a"),
        ("[ZeroWidthEscape]", "b"),
        ("", "c"),
    ]


def test_ansi_backspace() -> None:
    """Characters preceding backspace characters are removed."""
    value = ANSI("ab\x08c")
    assert to_formatted_text(value) == [
        ("", "a"),
        ("", "c"),
    ]


def test_ansi_colors() -> None:
    """ANSI color formatting is applied."""
    value = ANSI("\x1b[32mHe\x1b[45mllo")
    assert to_formatted_text(value) == [
        ("ansigreen", "H"),
        ("ansigreen", "e"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "o"),
    ]


def test_ansi_bold() -> None:
    """ANSI color bold is applied."""
    value = ANSI("\x1b[1mhe\x1b[0mllo")
    assert to_formatted_text(value) == [
        ("bold", "h"),
        ("bold", "e"),
        ("", "l"),
        ("", "l"),
        ("", "o"),
    ]


def test_ansi_misc_escape_sequences() -> None:
    """Miscellaneous escape sequence are converted to zero-width-escape sequences."""
    value = ANSI("a\x1b[0cb")
    assert to_formatted_text(value) == [
        ("", "a"),
        ("[ZeroWidthEscape]", "\x1b[0c"),
        ("", "b"),
    ]
