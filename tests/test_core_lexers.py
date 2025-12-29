"""Tests for lexer detection."""

from __future__ import annotations

from pathlib import Path

from pygments.lexers.python import PythonLexer
from pygments.lexers.special import TextLexer

from euporie.apptk.lexers.utils import detect_lexer


def test_detect_lexer_with_path() -> None:
    """`detect_lexer` can detect a lexer when given a file path."""
    path = Path("test.py")
    lexer = detect_lexer(path=path)
    assert isinstance(lexer, PythonLexer)


def test_detect_lexer_with_text() -> None:
    """`detect_lexer` can detect a lexer when given text."""
    text = "#!/usr/env python\nprint('Hello, world!')"
    lexer = detect_lexer(text=text)
    assert isinstance(lexer, PythonLexer)


def test_detect_lexer_with_language() -> None:
    """`detect_lexer` can detect a lexer when given a language name."""
    language = "python"
    lexer = detect_lexer(language=language)
    assert isinstance(lexer, PythonLexer)


def test_detect_lexer_returns_textlexer() -> None:
    """`detect_lexer` returns `TextLexer` if it detects text."""
    text = "This is not code."
    lexer = detect_lexer(text=text)
    assert isinstance(lexer, TextLexer)
