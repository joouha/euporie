"""Add additional keys to the prompt_toolkit vi key-bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from prompt_toolkit.buffer import indent, unindent
from prompt_toolkit.filters.app import vi_insert_mode
from prompt_toolkit.key_binding.bindings.vi import (
    load_vi_bindings as load_ptk_vi_bindings,
)

from euporie.core.filters import cursor_in_leading_ws

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import (
        ConditionalKeyBindings,
        KeyBindings,
        KeyBindingsBase,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent


def load_vi_bindings() -> KeyBindingsBase:
    """Load vi keybindings from PTK, adding additional bindings."""
    # We know the type of the vi bindings
    vi_bindings = cast(
        "KeyBindings",
        cast("ConditionalKeyBindings", load_ptk_vi_bindings()).key_bindings,
    )
    handle = vi_bindings.add

    @handle("c-i", filter=vi_insert_mode & cursor_in_leading_ws)
    def _indent(event: KeyPressEvent) -> None:
        """Indent lines."""
        buffer = event.current_buffer
        current_row = buffer.document.cursor_position_row
        indent(buffer, current_row, current_row + event.arg)

    @handle("s-tab", filter=vi_insert_mode & cursor_in_leading_ws)
    def _unindent(event: KeyPressEvent) -> None:
        """Unindent lines."""
        current_row = event.current_buffer.document.cursor_position_row
        unindent(event.current_buffer, current_row, current_row + event.arg)

    return vi_bindings
