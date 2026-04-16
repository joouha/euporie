import logging

from apptk.key_binding.key_processor import KeyPressEvent

E = KeyPressEvent
log = logging.getLogger(__name__)

__all__ = [
    "display_completions_like_readline",
    "generate_completions",
]

def generate_completions(event: E) -> None: ...
def display_completions_like_readline(event: E) -> None: ...
def cancel_completion() -> None: ...
def accept_completion() -> None: ...
