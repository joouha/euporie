"""Shim for prompt_toolkit Vi key bindings.

This module wraps the prompt_toolkit Vi bindings to load them through
the command system, and adds additional custom bindings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.bindings.vi import (
    load_vi_bindings as ptk_load_vi_bindings,
    load_vi_search_bindings as ptk_load_vi_search_bindings,
)

from euporie.apptk.buffer import indent, unindent
from euporie.apptk.commands import add_cmd, commands_from_key_bindings, get_cmd
from euporie.apptk.filters.app import vi_insert_mode
from euporie.apptk.filters.buffer import cursor_in_leading_ws
from euporie.apptk.key_binding.key_bindings import KeyBindingsBase

if TYPE_CHECKING:
    from euporie.apptk.key_binding.key_bindings import KeyBindings
    from euporie.apptk.key_binding.key_processor import KeyPressEvent

__all__ = [
    "load_vi_bindings",
    "load_vi_search_bindings",
]


# Custom Vi commands


@add_cmd(
    keys=["c-i"],
    filter=vi_insert_mode & cursor_in_leading_ws,
    hidden=True,
    name="vi-indent",
)
def _vi_indent(event: KeyPressEvent) -> None:
    """Indent lines."""
    buffer = event.current_buffer
    current_row = buffer.document.cursor_position_row
    indent(buffer, current_row, current_row + event.arg)


@add_cmd(
    keys=["s-tab"],
    filter=vi_insert_mode & cursor_in_leading_ws,
    hidden=True,
    name="vi-unindent",
)
def _vi_unindent(event: KeyPressEvent) -> None:
    """Unindent lines."""
    current_row = event.current_buffer.document.cursor_position_row
    unindent(event.current_buffer, current_row, current_row + event.arg)


def load_vi_bindings() -> KeyBindingsBase:
    """Load Vi key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system,
        plus additional custom bindings.
    """
    # Load ptk vi bindings through the command system
    kb: KeyBindings = commands_from_key_bindings(
        ptk_load_vi_bindings(), prefix="vi", hidden=True
    )

    # Add custom vi bindings
    for name in ("vi-indent", "vi-unindent"):
        get_cmd(name).bind(kb)

    return kb


def load_vi_search_bindings() -> KeyBindingsBase:
    """Load Vi search key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system.
    """
    return commands_from_key_bindings(
        ptk_load_vi_search_bindings(), prefix="vi-search", hidden=True
    )
