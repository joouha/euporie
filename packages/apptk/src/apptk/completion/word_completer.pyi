from collections.abc import Callable, Iterable, Mapping, Sequence
from re import Pattern

from apptk.completion import CompleteEvent, Completer, Completion
from apptk.document import Document
from apptk.formatted_text import AnyFormattedText

__all__ = [
    "WordCompleter",
]

class WordCompleter(Completer):
    words: Sequence[str] | Callable[[], Sequence[str]]
    ignore_case: bool
    display_dict: Mapping[str, AnyFormattedText] | None
    meta_dict: Mapping[str, AnyFormattedText] | None
    WORD: bool
    sentence: bool
    match_middle: bool
    pattern: Pattern[str] | None
    def __init__(
        self,
        words: Sequence[str] | Callable[[], Sequence[str]],
        ignore_case: bool = False,
        display_dict: Mapping[str, AnyFormattedText] | None = None,
        meta_dict: Mapping[str, AnyFormattedText] | None = None,
        WORD: bool = False,
        sentence: bool = False,
        match_middle: bool = False,
        pattern: Pattern[str] | None = None,
    ) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
