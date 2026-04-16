from collections.abc import Callable, Iterable, Sequence
from typing import NamedTuple

from apptk.document import Document
from apptk.filters import FilterOrBool
from apptk.formatted_text import AnyFormattedText

from .base import CompleteEvent, Completer, Completion
from .word_completer import WordCompleter

__all__ = [
    "FuzzyCompleter",
    "FuzzyWordCompleter",
]

class _FuzzyMatch(NamedTuple):
    match_length: int
    start_pos: int
    completion: Completion

class FuzzyCompleter(Completer):
    completer: Completer
    pattern: str | None
    WORD: bool
    enable_fuzzy: FilterOrBool
    def __init__(
        self,
        completer: Completer,
        WORD: bool = False,
        pattern: str | None = None,
        enable_fuzzy: FilterOrBool = True,
    ) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    def _get_pattern(self) -> str: ...
    def _get_fuzzy_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    def _get_display(
        self,
        fuzzy_match: _FuzzyMatch,
        word_before_cursor: str,
    ) -> AnyFormattedText: ...

class FuzzyWordCompleter(Completer):
    words: Sequence[str] | Callable[[], Sequence[str]]
    meta_dict: dict[str, str] | None
    WORD: bool
    word_completer: WordCompleter
    fuzzy_completer: FuzzyCompleter
    def __init__(
        self,
        words: Sequence[str] | Callable[[], Sequence[str]],
        meta_dict: dict[str, str] | None = None,
        WORD: bool = False,
    ) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
