from apptk.key_binding.key_processor import KeyPressEvent

E = KeyPressEvent

__all__ = [
    "focus_next",
    "focus_previous",
]

def focus_next(event: E) -> None: ...
def focus_previous(event: E) -> None: ...
