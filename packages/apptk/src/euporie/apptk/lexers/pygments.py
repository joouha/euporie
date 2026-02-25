"""Adaptor classes for using Pygments lexers within prompt_toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.lexers.pygments import PygmentsLexer as PtkPygmentsLexer

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.document import Document
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples


class PygmentsLexer(PtkPygmentsLexer):
    """Lexer that calls a pygments lexer.

    Ensures lexed text ends in trailing newline.
    """

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        """Create a lexer function."""
        # Ensure lexed text always ends in a newline
        # This enables detection of headings on the last line of the text
        document = document.insert_after("\n")
        return super().lex_document(document)
