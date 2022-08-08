"""Defines KeyBindings wrapper which keeps track of key binding descriptions."""

from __future__ import annotations

from aenum import extend_enum
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.keys import Keys

# Register additional keys
extend_enum(Keys, "ControlEnter", "c-enter")
extend_enum(Keys, "ControlShiftEnter", "c-s-enter")
extend_enum(Keys, "ShiftEnter", "s-enter")

# Assign escape sequences to new keys
ANSI_SEQUENCES["\x1b[27;5;13~"] = Keys.ControlEnter  # type: ignore
ANSI_SEQUENCES["\x1b[13;5u"] = Keys.ControlEnter  # type: ignore

ANSI_SEQUENCES["\x1b[27;2;13~"] = Keys.ShiftEnter  # type: ignore
ANSI_SEQUENCES["\x1b[13;2u"] = Keys.ShiftEnter  # type: ignore

ANSI_SEQUENCES["\x1b[27;6;13~"] = Keys.ControlShiftEnter  # type: ignore
ANSI_SEQUENCES["\x1b[13;6u"] = Keys.ControlShiftEnter  # type: ignore
