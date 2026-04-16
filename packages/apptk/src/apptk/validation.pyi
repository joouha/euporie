from abc import abstractmethod
from collections.abc import Callable

from .document import Document
from .filters import FilterOrBool

__all__ = [
    "ConditionalValidator",
    "DummyValidator",
    "DynamicValidator",
    "ThreadedValidator",
    "ValidationError",
    "Validator",
]

class ValidationError(Exception):
    cursor_position: int
    message: str
    def __init__(self, cursor_position: int = 0, message: str = "") -> None: ...
    def __repr__(self) -> str: ...

class Validator:
    @abstractmethod
    def validate(self, document: Document) -> None: ...
    async def validate_async(self, document: Document) -> None: ...
    @classmethod
    def from_callable(
        cls,
        validate_func: Callable[[str], bool],
        error_message: str = "Invalid input",
        move_cursor_to_end: bool = False,
    ) -> Validator: ...

class _ValidatorFromCallable(Validator):
    func: Callable[[str], bool]
    error_message: str
    move_cursor_to_end: bool
    def __init__(
        self,
        func: Callable[[str], bool],
        error_message: str,
        move_cursor_to_end: bool,
    ) -> None: ...
    def validate(self, document: Document) -> None: ...
    def __repr__(self) -> str: ...

class ThreadedValidator(Validator):
    validator: Validator
    def __init__(self, validator: Validator) -> None: ...
    def validate(self, document: Document) -> None: ...
    async def validate_async(self, document: Document) -> None: ...

class DummyValidator(Validator):
    def validate(self, document: Document) -> None: ...

class ConditionalValidator(Validator):
    validator: Validator
    filter: FilterOrBool
    def __init__(self, validator: Validator, filter: FilterOrBool) -> None: ...
    def validate(self, document: Document) -> None: ...

class DynamicValidator(Validator):
    get_validator: Callable[[], Validator | None]
    def __init__(self, get_validator: Callable[[], Validator | None]) -> None: ...
    def validate(self, document: Document) -> None: ...
    async def validate_async(self, document: Document) -> None: ...
