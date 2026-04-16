import logging

from apptk.key_binding.key_bindings import (
    KeyBindingsBase,
)

log = logging.getLogger(__name__)

__all__ = [
    "load_key_bindings",
]

def load_key_bindings() -> KeyBindingsBase: ...
