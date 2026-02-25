"""Shim for prompt_toolkit auto-suggest key bindings.

This module wraps the prompt_toolkit auto-suggest bindings to load them through
the command system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.bindings.auto_suggest import (
    load_auto_suggest_bindings as ptk_load_auto_suggest_bindings,
)

from euporie.apptk.commands import commands_from_key_bindings
from euporie.apptk.key_binding.key_bindings import KeyBindingsBase

if TYPE_CHECKING:
    pass

__all__ = ["load_auto_suggest_bindings"]


def load_auto_suggest_bindings() -> KeyBindingsBase:
    """Load auto-suggest key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system.
    """
    return commands_from_key_bindings(
        ptk_load_auto_suggest_bindings(),
        prefix="auto-suggest",
        hidden=True,
    )
