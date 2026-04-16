import asyncio
import logging
from abc import abstractmethod
from collections import deque
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple

from apptk.cache import SimpleCache

from .document import Document
from .filters import Filter

if TYPE_CHECKING:
    from apptk.buffer import Buffer
    from apptk.document import Document
    from apptk.filters import Filter
    from apptk.history import History

    from .buffer import Buffer

log = logging.getLogger(__name__)

__all__ = [
    "AutoSuggest",
    "AutoSuggestFromHistory",
    "ConditionalAutoSuggest",
    "DummyAutoSuggest",
    "DynamicAutoSuggest",
    "Suggestion",
    "ThreadedAutoSuggest",
]

class Suggestion:
    text: str
    def __init__(self, text: str) -> None: ...
    def __repr__(self) -> str: ...

class AutoSuggest:
    @abstractmethod
    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None: ...
    async def get_suggestion_async(
        self,
        buff: Buffer,
        document: Document,
    ) -> Suggestion | None: ...

class ThreadedAutoSuggest(AutoSuggest):
    auto_suggest: AutoSuggest
    def __init__(self, auto_suggest: AutoSuggest) -> None: ...
    def get_suggestion(self, buff: Buffer, document: Document) -> Suggestion | None: ...
    async def get_suggestion_async(
        self,
        buff: Buffer,
        document: Document,
    ) -> Suggestion | None: ...

class DummyAutoSuggest(AutoSuggest):
    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None: ...

class AutoSuggestFromHistory(AutoSuggest):
    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None: ...

class ConditionalAutoSuggest(AutoSuggest):
    auto_suggest: AutoSuggest
    filter: bool | Filter
    def __init__(self, auto_suggest: AutoSuggest, filter: bool | Filter) -> None: ...
    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None: ...

class DynamicAutoSuggest(AutoSuggest):
    get_auto_suggest: Callable[[], AutoSuggest | None]
    def __init__(self, get_auto_suggest: Callable[[], AutoSuggest | None]) -> None: ...
    def get_suggestion(self, buff: Buffer, document: Document) -> Suggestion | None: ...
    async def get_suggestion_async(
        self,
        buff: Buffer,
        document: Document,
    ) -> Suggestion | None: ...

class ConditionalAutoSuggestAsync(ConditionalAutoSuggest):
    auto_suggest: AutoSuggest
    filter: bool | Filter
    def __init__(self, auto_suggest: AutoSuggest, filter: bool | Filter) -> None: ...
    async def get_suggestion_async(
        self,
        buffer: Buffer,
        document: Document,
    ) -> Suggestion | None: ...

class HistoryPosition(NamedTuple):
    idx: int  # Index in history
    context_start: int  # Position where context starts
    context_end: int  # Position where context ends

class SimpleHistoryAutoSuggest(AutoSuggest):
    history: History
    cache_size: int
    cache_keys: deque[str]
    cache: dict[str, Suggestion]
    def __init__(self, history: History, cache_size: int = 100000) -> None: ...
    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None: ...
    def lookup_suggestion(self, line: str) -> Suggestion | None: ...

class SmartHistoryAutoSuggest(AutoSuggest):
    _context_lines = 10
    _max_line_len = 200
    _max_item_lines = 1000
    history: History
    n_texts = 0
    _processing_task: asyncio.Task | None
    prefix_tree: dict[str, list[int]]
    suffix_data: list[tuple[str, HistoryPosition]]
    calculate_similarity = lru_cache(maxsize=128)(self._calculate_similarity)
    match_cache: SimpleCache[tuple[str, int, int], Suggestion | None]
    def __init__(self, history: History) -> None: ...
    def process_history(self) -> None: ...
    async def _process_history_async(self) -> None: ...
    def _calculate_similarity(self, text_1: str, text_2: str) -> float: ...
    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None: ...
    def _find_match(self, line: str, document_text: str) -> Suggestion | None: ...
