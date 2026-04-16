from apptk.key_binding.key_bindings import (
    KeyBindingsBase,
)

__all__ = [
    "load_emacs_page_navigation_bindings",
    "load_page_navigation_bindings",
    "load_vi_page_navigation_bindings",
]

def load_page_navigation_bindings() -> KeyBindingsBase: ...
def load_emacs_page_navigation_bindings() -> KeyBindingsBase: ...
def load_vi_page_navigation_bindings() -> KeyBindingsBase: ...
