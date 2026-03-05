"""Helix editor state management."""

from __future__ import annotations

import logging
from enum import Enum

from apptk.key_binding.vi_state import CharacterFind as CharacterFind
from apptk.key_binding.vi_state import InputMode as InputMode
from apptk.key_binding.vi_state import ViState

__all__ = ["CharacterFind", "HelixMode", "HelixState", "InputMode"]

log = logging.getLogger(__name__)


class HelixMode(Enum):
    """Helix sub-modes for modal editing."""

    NORMAL = "normal"
    GOTO = "goto"
    MATCH = "match"
    VIEW = "view"
    WINDOW = "window"
    SPACE = "space"


class HelixState(ViState):
    """Mutable class to hold the state of Helix navigation.

    Extends ``ViState`` with Helix-specific sub-modes (goto, match, view,
    window, space) layered on top of the standard Vi input modes.

    Attributes:
        mode: The current Helix sub-mode.
        waiting_for_char: Character command being waited for (f/F/t/T).
        select_mode: Whether explicit select mode is active (via ``v``).
    """

    def __init__(self) -> None:
        """Initialize Helix state."""
        super().__init__()

        # Helix-specific state
        self._mode: HelixMode = HelixMode.NORMAL
        self._waiting_for_char: str | None = None
        self._select_mode: bool = False

    @property
    def mode(self) -> HelixMode:
        """Get the current Helix sub-mode."""
        return self._mode

    @mode.setter
    def mode(self, value: HelixMode) -> None:
        """Set the current Helix sub-mode."""
        self._mode = value

    @property
    def waiting_for_char(self) -> str | None:
        """Get the character command being waited for."""
        return self._waiting_for_char

    @waiting_for_char.setter
    def waiting_for_char(self, value: str | None) -> None:
        """Set the character command being waited for."""
        self._waiting_for_char = value

    @property
    def goto_mode(self) -> bool:
        """Check if in goto mode."""
        return self._mode == HelixMode.GOTO

    @goto_mode.setter
    def goto_mode(self, value: bool) -> None:
        """Set goto mode."""
        if value:
            self._mode = HelixMode.GOTO
        elif self._mode == HelixMode.GOTO:
            self._mode = HelixMode.NORMAL

    @property
    def match_mode(self) -> bool:
        """Check if in match mode."""
        return self._mode == HelixMode.MATCH

    @match_mode.setter
    def match_mode(self, value: bool) -> None:
        """Set match mode."""
        if value:
            self._mode = HelixMode.MATCH
        elif self._mode == HelixMode.MATCH:
            self._mode = HelixMode.NORMAL

    @property
    def view_mode(self) -> bool:
        """Check if in view mode."""
        return self._mode == HelixMode.VIEW

    @view_mode.setter
    def view_mode(self, value: bool) -> None:
        """Set view mode."""
        if value:
            self._mode = HelixMode.VIEW
        elif self._mode == HelixMode.VIEW:
            self._mode = HelixMode.NORMAL

    @property
    def window_mode(self) -> bool:
        """Check if in window mode."""
        return self._mode == HelixMode.WINDOW

    @window_mode.setter
    def window_mode(self, value: bool) -> None:
        """Set window mode."""
        if value:
            self._mode = HelixMode.WINDOW
        elif self._mode == HelixMode.WINDOW:
            self._mode = HelixMode.NORMAL

    @property
    def space_mode(self) -> bool:
        """Check if in space mode."""
        return self._mode == HelixMode.SPACE

    @space_mode.setter
    def space_mode(self, value: bool) -> None:
        """Set space mode."""
        if value:
            self._mode = HelixMode.SPACE
        elif self._mode == HelixMode.SPACE:
            self._mode = HelixMode.NORMAL

    @property
    def select_mode(self) -> bool:
        """Check if explicitly in select mode (via ``v``)."""
        return self._select_mode

    @select_mode.setter
    def select_mode(self, value: bool) -> None:
        """Set explicit select mode."""
        self._select_mode = value

    def reset(self) -> None:
        """Reset state, go back to INSERT mode."""
        super().reset()

        # Reset Helix-specific state.
        self._mode = HelixMode.NORMAL
        self._waiting_for_char = None
        self._select_mode = False

    def exit_submode(self) -> None:
        """Exit current sub-mode and return to normal."""
        self._mode = HelixMode.NORMAL
