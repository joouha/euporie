"""Shim for prompt_toolkit Emacs key bindings.

This module wraps the prompt_toolkit Emacs bindings to load them through
the command system, and adds additional custom bindings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.bindings.emacs import (
    load_emacs_bindings as ptk_load_emacs_bindings,
    load_emacs_search_bindings as ptk_load_emacs_search_bindings,
    load_emacs_shift_selection_bindings as ptk_load_emacs_shift_selection_bindings,
)

from euporie.apptk.commands import commands_from_key_bindings
from euporie.apptk.key_binding.key_bindings import KeyBindingsBase

if TYPE_CHECKING:
    pass

__all__ = [
    "load_emacs_bindings",
    "load_emacs_search_bindings",
    "load_emacs_shift_selection_bindings",
]


def load_emacs_bindings() -> KeyBindingsBase:
    """Load Emacs key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system.
    """
    return commands_from_key_bindings(
        ptk_load_emacs_bindings(),
        prefix="emacs",
        hidden=True,
    )


def load_emacs_search_bindings() -> KeyBindingsBase:
    """Load Emacs search key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system.
    """
    return commands_from_key_bindings(
        ptk_load_emacs_search_bindings(),
        prefix="emacs-search",
        hidden=True,
    )


def load_emacs_shift_selection_bindings() -> KeyBindingsBase:
    """Load Emacs shift selection key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system.
    """
    return commands_from_key_bindings(
        ptk_load_emacs_shift_selection_bindings(),
        prefix="emacs-shift",
        hidden=True,
    )
