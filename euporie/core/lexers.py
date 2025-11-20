"""Relating to lexers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    guess_lexer,
    guess_lexer_for_filename,
)
from pygments.util import ClassNotFound

if TYPE_CHECKING:
    from pathlib import Path

    from pygments.lexer import Lexer as PygmentsLexerCls


def detect_lexer(
    text: str = "", path: Path | None = None, language: str = ""
) -> PygmentsLexerCls | None:
    """Detect the pygments lexer for a file."""
    lexer = None
    if path is not None:
        try:
            lexer = get_lexer_for_filename(path)
        except (ClassNotFound, TypeError):
            try:
                lexer = guess_lexer_for_filename(path, text)
            except (ClassNotFound, TypeError):
                pass
    if lexer is None and language:
        try:
            lexer = get_lexer_by_name(language)
        except ClassNotFound:
            pass
    if lexer is None:
        try:
            lexer = guess_lexer(text)
        except ClassNotFound:
            pass
    return lexer
