from apptk.key_binding.key_processor import KeyPressEvent

from .layout import Layout

E = KeyPressEvent

__all__ = [
    "create_dummy_layout",
]

def create_dummy_layout() -> Layout: ...
