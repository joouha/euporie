from collections.abc import Iterable, Mapping
from typing import Any

from apptk.completion import CompleteEvent, Completer, Completion
from apptk.document import Document

NestedDict = Mapping[str, Any | set[str] | None | Completer]

__all__ = [
    "NestedCompleter",
]

class NestedCompleter(Completer):
    options: dict[str, Completer | None]
    ignore_case: bool
    def __init__(
        self,
        options: dict[str, Completer | None],
        ignore_case: bool = True,
    ) -> None: ...
    @classmethod
    def from_nested_dict(cls, data: NestedDict) -> NestedCompleter: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    def __repr__(self) -> str: ...
