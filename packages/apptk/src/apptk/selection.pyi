from enum import Enum

__all__ = [
    "PasteMode",
    "SelectionState",
    "SelectionType",
]

class SelectionType(Enum):
    CHARACTERS = "CHARACTERS"
    LINES = "LINES"
    BLOCK = "BLOCK"

class PasteMode(Enum):
    EMACS = "EMACS"  # Yank like emacs.
    VI_AFTER = "VI_AFTER"  # When pressing 'p' in Vi.
    VI_BEFORE = "VI_BEFORE"  # When pressing 'P' in Vi.

class SelectionState:
    original_cursor_position: int
    type: SelectionType
    shift_mode = False
    def __init__(
        self,
        original_cursor_position: int = 0,
        type: SelectionType = SelectionType.CHARACTERS,
    ) -> None: ...
    def enter_shift_mode(self) -> None: ...
    def __repr__(self) -> str: ...
