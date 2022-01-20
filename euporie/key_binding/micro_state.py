"""Defines the state of the micro editing mode."""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Optional

    from prompt_toolkit.key_binding.key_processor import KeyPress

__all__ = ["InputMode", "MicroState"]


class InputMode(str, Enum):
    """Enum to define edit mode state types."""

    value: "str"
    INSERT = "insert"
    REPLACE = "replace"


class MicroState:
    """Mutable class to hold Micro specific state."""

    def __init__(self) -> "None":
        """Initiates the editing mode state."""
        self.macro: "Optional[List[KeyPress]]" = []
        self.current_recording: "Optional[List[KeyPress]]" = None
        self.input_mode: "InputMode" = InputMode.INSERT

    def reset(self) -> "None":
        """Reset the editing mode state."""
        self.input_mode = InputMode.INSERT
        self.current_recording = None

    @property
    def is_recording(self) -> "bool":
        """Tell whether we are recording a macro."""
        return self.current_recording is not None

    def start_macro(self) -> "None":
        """Start recording a macro."""
        self.current_recording = []

    def end_macro(self) -> "None":
        """End recording a macro."""
        self.macro = self.current_recording
        self.current_recording = None
