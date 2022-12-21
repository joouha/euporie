"""Relating to lexers."""

from typing import TYPE_CHECKING

from pygments.lexers import (
    get_lexer_for_filename,
    guess_lexer,
    guess_lexer_for_filename,
)
from pygments.util import ClassNotFound

if TYPE_CHECKING:
    from pygments.lexer import Lexer as PygmentsLexerCls
    from upath import UPath


def detect_lexer(text: "str" = "", path: "UPath|None" = None) -> "PygmentsLexerCls":
    """Detect the pygments lexer for a file."""
    lexer = None
    if path is not None:
        try:
            lexer = get_lexer_for_filename(path)
        except ClassNotFound:
            try:
                lexer = guess_lexer_for_filename(path, text)
            except ClassNotFound:
                pass
    if lexer is None:
        try:
            lexer = guess_lexer(text)
        except ClassNotFound:
            pass
    return lexer
