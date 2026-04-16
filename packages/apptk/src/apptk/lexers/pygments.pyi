from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from apptk.document import Document
from apptk.filters import FilterOrBool
from apptk.formatted_text.base import StyleAndTextTuples

from .base import Lexer

if TYPE_CHECKING:
    from collections.abc import Callable

    from pygments.lexer import Lexer as PygmentsLexerCls

class _TokenCache(dict[tuple[str, ...], str]):
    def __missing__(self, key: tuple[str, ...]) -> str: ...

_token_cache = _TokenCache()

__all__ = [
    "PygmentsLexer",
    "RegexSync",
    "SyncFromStart",
    "SyntaxSync",
]

class SyntaxSync:
    @abstractmethod
    def get_sync_start_position(
        self,
        document: Document,
        lineno: int,
    ) -> tuple[int, int]: ...

class SyncFromStart(SyntaxSync):
    def get_sync_start_position(
        self,
        document: Document,
        lineno: int,
    ) -> tuple[int, int]: ...

class RegexSync(SyntaxSync):
    MAX_BACKWARDS = 500
    FROM_START_IF_NO_SYNC_POS_FOUND = 100
    _compiled_pattern: str
    def __init__(self, pattern: str) -> None: ...
    def get_sync_start_position(
        self,
        document: Document,
        lineno: int,
    ) -> tuple[int, int]: ...
    @classmethod
    def from_pygments_lexer_cls(cls, lexer_cls: PygmentsLexerCls) -> RegexSync: ...

class PygmentsLexer:
    MIN_LINES_BACKWARDS = 50
    REUSE_GENERATOR_MAX_DISTANCE = 100
    pygments_lexer_cls: type[PygmentsLexerCls]
    sync_from_start: FilterOrBool
    pygments_lexer = pygments_lexer_cls(stripnl=False, stripall=False, ensurenl=False)
    syntax_sync: SyntaxSync | None
    def __init__(
        self,
        pygments_lexer_cls: type[PygmentsLexerCls],
        sync_from_start: FilterOrBool = True,
        syntax_sync: SyntaxSync | None = None,
    ) -> None: ...
    @classmethod
    def from_filename(
        cls, filename: str, sync_from_start: FilterOrBool = True
    ) -> Lexer: ...
    def lex_document(
        self, document: Document
    ) -> Callable[[int], StyleAndTextTuples]: ...
