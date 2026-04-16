from collections.abc import Iterable

from apptk.completion import CompleteEvent, Completer, Completion
from apptk.document import Document

from .compiler import Match, _CompiledGrammar

__all__ = [
    "GrammarCompleter",
]

class GrammarCompleter(Completer):
    compiled_grammar: _CompiledGrammar
    completers: dict[str, Completer]
    def __init__(
        self,
        compiled_grammar: _CompiledGrammar,
        completers: dict[str, Completer],
    ) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    def _get_completions_for_match(
        self,
        match: Match,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...
    def _remove_duplicates(
        self, items: Iterable[Completion]
    ) -> Iterable[Completion]: ...
