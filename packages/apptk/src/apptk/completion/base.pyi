from abc import abstractmethod
from collections.abc import AsyncGenerator, Callable, Iterable, Sequence

from apptk.document import Document
from apptk.filters import FilterOrBool
from apptk.formatted_text import AnyFormattedText, StyleAndTextTuples

__all__ = [
    "CompleteEvent",
    "Completer",
    "Completion",
    "ConditionalCompleter",
    "DummyCompleter",
    "DynamicCompleter",
    "ThreadedCompleter",
    "get_common_complete_suffix",
    "merge_completers",
]

class Completion:
    text: str
    start_position: int
    _display_meta: AnyFormattedText | None
    display: AnyFormattedText | None
    style: str
    selected_style: str
    def __init__(
        self,
        text: str,
        start_position: int = 0,
        display: AnyFormattedText | None = None,
        display_meta: AnyFormattedText | None = None,
        style: str = "",
        selected_style: str = "",
    ) -> None: ...
    @property
    def display_text(self) -> str: ...
    @property
    def display_meta(self) -> StyleAndTextTuples: ...
    @property
    def display_meta_text(self) -> str: ...
    def new_completion_from_position(self, position: int) -> Completion: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def __repr__(self) -> str: ...

class CompleteEvent:
    text_inserted: bool
    completion_requested: bool
    def __init__(
        self,
        text_inserted: bool = False,
        completion_requested: bool = False,
    ) -> None: ...
    def __repr__(self) -> str: ...

class Completer:
    @abstractmethod
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    async def get_completions_async(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> AsyncGenerator[Completion]: ...

def merge_completers(
    completers: Sequence[Completer],
    deduplicate: bool = False,
) -> Completer: ...
def get_common_complete_suffix(
    document: Document,
    completions: Sequence[Completion],
) -> str: ...

class ThreadedCompleter(Completer):
    completer: Completer
    def __init__(self, completer: Completer) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    async def get_completions_async(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> AsyncGenerator[Completion]: ...
    def __repr__(self) -> str: ...

class DummyCompleter(Completer):
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    def __repr__(self) -> str: ...

class DynamicCompleter(Completer):
    get_completer: Callable[[], Completer | None]
    def __init__(self, get_completer: Callable[[], Completer | None]) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    async def get_completions_async(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> AsyncGenerator[Completion]: ...
    def __repr__(self) -> str: ...

class ConditionalCompleter(Completer):
    completer: Completer
    filter: FilterOrBool
    def __init__(self, completer: Completer, filter: FilterOrBool) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    async def get_completions_async(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> AsyncGenerator[Completion]: ...
    def __repr__(self) -> str: ...

class _MergedCompleter(Completer):
    completers: Sequence[Completer]
    def __init__(self, completers: Sequence[Completer]) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    async def get_completions_async(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> AsyncGenerator[Completion]: ...
