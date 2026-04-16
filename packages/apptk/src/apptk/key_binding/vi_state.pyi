from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING

from apptk.clipboard import ClipboardData

if TYPE_CHECKING:
    from .bindings.vi import TextObject
    from .key_processor import KeyPressEvent

__all__ = [
    "CharacterFind",
    "InputMode",
    "ViState",
]

class InputMode(str, Enum):
    value: str
    INSERT = "vi-insert"
    INSERT_MULTIPLE = "vi-insert-multiple"
    NAVIGATION = "vi-navigation"  # Normal mode.
    REPLACE = "vi-replace"
    REPLACE_SINGLE = "vi-replace-single"

class CharacterFind:
    character: str
    backwards: bool
    def __init__(self, character: str, backwards: bool = False) -> None: ...

class ViState:
    input_mode = InputMode.NAVIGATION
    last_character_find: CharacterFind | None
    operator_func: None | Callable[[KeyPressEvent, TextObject], None]
    operator_arg: int | None
    named_registers: dict[str, ClipboardData]
    __input_mode = InputMode.NAVIGATION
    waiting_for_digraph = False
    digraph_symbol1: str | None
    tilde_operator = False
    recording_register: str | None
    current_recording: str
    temporary_navigation_mode = False
    def __init__(self) -> None: ...
    def reset(self) -> None: ...
