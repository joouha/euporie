from collections import defaultdict

from ..key_binding import KeyPress
from .base import Input

_buffer: dict[str, list[KeyPress]] = defaultdict(list)

__all__ = [
    "clear_typeahead",
    "get_typeahead",
    "store_typeahead",
]

def store_typeahead(input_obj: Input, key_presses: list[KeyPress]) -> None: ...
def get_typeahead(input_obj: Input) -> list[KeyPress]: ...
def clear_typeahead(input_obj: Input) -> None: ...
