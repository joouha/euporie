from typing import TYPE_CHECKING

from apptk.filters import (
    Condition,
)
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.key_binding.utils import if_no_repeat

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindingsBase

E = KeyPressEvent

__all__ = [
    "load_basic_bindings",
]

def if_no_repeat(event: E) -> bool: ...

has_text_before_cursor: Condition
in_quoted_insert: Condition

def load_basic_bindings() -> KeyBindingsBase: ...
def type_key(event: KeyPressEvent) -> None: ...
