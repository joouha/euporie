from apptk.document import Document
from apptk.validation import Validator

from .compiler import _CompiledGrammar

__all__ = [
    "GrammarValidator",
]

class GrammarValidator(Validator):
    compiled_grammar: _CompiledGrammar
    validators: dict[str, Validator]
    def __init__(
        self,
        compiled_grammar: _CompiledGrammar,
        validators: dict[str, Validator],
    ) -> None: ...
    def validate(self, document: Document) -> None: ...
