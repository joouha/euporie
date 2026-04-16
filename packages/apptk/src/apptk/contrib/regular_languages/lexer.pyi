from collections.abc import Callable

from apptk.document import Document
from apptk.formatted_text.base import StyleAndTextTuples
from apptk.lexers import Lexer

from .compiler import _CompiledGrammar

__all__ = [
    "GrammarLexer",
]

class GrammarLexer(Lexer):
    compiled_grammar: _CompiledGrammar
    default_style: str
    lexers: dict[str, Lexer] | None
    def __init__(
        self,
        compiled_grammar: _CompiledGrammar,
        default_style: str = "",
        lexers: dict[str, Lexer] | None = None,
    ) -> None: ...
    def _get_text_fragments(self, text: str) -> StyleAndTextTuples: ...
    def lex_document(
        self, document: Document
    ) -> Callable[[int], StyleAndTextTuples]: ...
