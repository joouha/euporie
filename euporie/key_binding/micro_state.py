# -*- coding: utf-8 -*-
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Optional

    from prompt_toolkit.key_bindings.key_processor import KeyPress

__all__ = [
    "MicroState",
]


class InputMode(str, Enum):
    value: str

    INSERT = "insert"
    REPLACE = "replace"


class MicroState:
    """Mutable class to hold Micro specific state."""

    def __init__(self) -> None:
        # Simple macro recording for micro mode
        self.macro: "Optional[List[KeyPress]]" = []
        self.current_recording: "Optional[List[KeyPress]]" = None
        self.input_mode: "InputMode" = InputMode.INSERT

    def reset(self) -> None:
        self.input_mode = InputMode.INSERT
        self.current_recording = None

    @property
    def is_recording(self) -> bool:
        "Tell whether we are recording a macro."
        return self.current_recording is not None

    def start_macro(self) -> None:
        "Start recording macro."
        self.current_recording = []

    def end_macro(self) -> None:
        "End recording macro."
        self.macro = self.current_recording
        self.current_recording = None
