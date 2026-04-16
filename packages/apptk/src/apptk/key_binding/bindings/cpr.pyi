from apptk.key_binding.key_processor import KeyPressEvent

from ..key_bindings import KeyBindings

E = KeyPressEvent

__all__ = [
    "load_cpr_bindings",
]

def load_cpr_bindings() -> KeyBindings: ...
