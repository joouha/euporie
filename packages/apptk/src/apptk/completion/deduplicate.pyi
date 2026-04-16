from collections.abc import Iterable
from typing import TYPE_CHECKING

from apptk.document import Document

from .base import CompleteEvent, Completer, Completion

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from apptk.completion.base import CompleteEvent, Completion

__all__ = [
    "DeduplicateCompleter",
]

class DeduplicateCompleter:
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
