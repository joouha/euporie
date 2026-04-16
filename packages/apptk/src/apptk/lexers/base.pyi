from abc import abstractmethod
from collections.abc import Callable, Hashable

from apptk.document import Document
from apptk.formatted_text.base import StyleAndTextTuples

__all__ = [
    "DynamicLexer",
    "Lexer",
    "SimpleLexer",
]

class Lexer:
    @abstractmethod
    def lex_document(
        self, document: Document
    ) -> Callable[[int], StyleAndTextTuples]: ...
    def invalidation_hash(self) -> Hashable: ...

class SimpleLexer(Lexer):
    style: str
    def __init__(self, style: str = "") -> None: ...
    def lex_document(
        self, document: Document
    ) -> Callable[[int], StyleAndTextTuples]: ...

class DynamicLexer(Lexer):
    get_lexer: Callable[[], Lexer | None]
    _dummy: SimpleLexer
    def __init__(self, get_lexer: Callable[[], Lexer | None]) -> None: ...
    def lex_document(
        self, document: Document
    ) -> Callable[[int], StyleAndTextTuples]: ...
    def invalidation_hash(self) -> Hashable: ...
