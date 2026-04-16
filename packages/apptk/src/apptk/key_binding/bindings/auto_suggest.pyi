from typing import TYPE_CHECKING

from apptk.key_binding.key_processor import KeyPressEvent

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindingsBase

E = KeyPressEvent

__all__ = [
    "load_auto_suggest_bindings",
]

def load_auto_suggest_bindings() -> KeyBindingsBase: ...
