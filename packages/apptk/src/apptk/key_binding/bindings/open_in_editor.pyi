from ..key_bindings import KeyBindings, KeyBindingsBase

__all__ = [
    "load_emacs_open_in_editor_bindings",
    "load_open_in_editor_bindings",
    "load_vi_open_in_editor_bindings",
]

def load_open_in_editor_bindings() -> KeyBindingsBase: ...
def load_emacs_open_in_editor_bindings() -> KeyBindings: ...
def load_vi_open_in_editor_bindings() -> KeyBindings: ...
