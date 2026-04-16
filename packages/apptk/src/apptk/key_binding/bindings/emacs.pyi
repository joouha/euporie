from typing import TYPE_CHECKING

from apptk.filters import (
    Condition,
)
from apptk.key_binding.key_processor import KeyPressEvent

from ..key_bindings import KeyBindingsBase

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindingsBase

E = KeyPressEvent

__all__ = [
    "load_emacs_bindings",
    "load_emacs_search_bindings",
    "load_emacs_shift_selection_bindings",
]

is_returnable: Condition
is_arg: Condition

def load_emacs_bindings() -> KeyBindingsBase: ...
def load_emacs_search_bindings() -> KeyBindingsBase: ...
def load_emacs_shift_selection_bindings() -> KeyBindingsBase: ...
