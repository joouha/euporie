"""Define basic key-bindings for entering text.

This module wraps the prompt_toolkit basic bindings to load them through
the command system, and adds additional custom bindings.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.bindings.basic import (
    load_basic_bindings as ptk_load_basic_bindings,
)

from euporie.apptk.commands import add_cmd, commands_from_key_bindings, get_cmd
from euporie.apptk.filters import (
    buffer_has_focus,
)
from euporie.apptk.filters.buffer import (
    char_after_cursor,
    cursor_at_end_of_line,
    has_matching_bracket,
)
from euporie.apptk.filters.modes import insert_mode, replace_mode
from euporie.apptk.key_binding.bindings import named_commands as named_commands
from euporie.apptk.key_binding.utils import if_no_repeat

if TYPE_CHECKING:
    from euporie.apptk.key_binding.key_bindings import KeyBindings, KeyBindingsBase
    from euporie.apptk.key_binding.key_processor import KeyPressEvent

__all__ = ["load_basic_bindings"]

# Commands

## Typing keys


@add_cmd(keys=["<any>"], filter=buffer_has_focus, save_before=if_no_repeat, hidden=True)
def type_key(event: KeyPressEvent) -> None:
    """Enter a key."""
    # Do not insert escape sequences
    if not event.data.startswith("\x1b"):
        event.current_buffer.insert_text(
            event.data * event.arg, overwrite=replace_mode()
        )


## Add automatic bracket completion


def _complete_bracket(right: str, event: KeyPressEvent) -> None:
    """Automatically insert a closing bracket."""
    event.current_buffer.insert_text(right, move_cursor=False)
    event.key_processor.feed(event.key_sequence[0], first=True)


def _skip_close_bracket(right: str, event: KeyPressEvent) -> None:
    """Skip typing a close bracket if it already exists."""
    event.current_buffer.cursor_position += 1


for left, right in [("(", ")"), ("[", "]"), ("{", "}")]:
    add_cmd(
        keys=[left],
        name=f"complete-bracket-{left}{right}",
        filter=buffer_has_focus
        & insert_mode
        & (char_after_cursor(" ") | cursor_at_end_of_line),
        save_before=if_no_repeat,
        hidden=True,
    )(partial(_complete_bracket, right))
    add_cmd(
        keys=[right],
        name=f"close-bracket-{left}{right}",
        filter=buffer_has_focus
        & insert_mode
        & char_after_cursor(right)
        & has_matching_bracket,
        save_before=if_no_repeat,
        hidden=True,
    )(partial(_skip_close_bracket, right))


def load_basic_bindings() -> KeyBindingsBase:
    """Load basic key bindings through the command system.

    Returns:
        A KeyBindings object with bindings loaded through the command system,
        plus additional custom bindings.
    """
    # Load ptk basic bindings through the command system
    kb: KeyBindings = commands_from_key_bindings(
        ptk_load_basic_bindings(),
        prefix="basic",
        hidden=True,
    )

    # Add custom bindings
    for name in (
        # Typing bindings
        "type-key",
        # Text surround bindings
        "complete-bracket-()",
        "complete-bracket-[]",
        "complete-bracket-{}",
        "close-bracket-()",
        "close-bracket-[]",
        "close-bracket-{}",
        # Completion bindings
        "menu-complete",
        "menu-complete-backward",
        "cancel-completion",
        "accept-completion",
    ):
        get_cmd(name).bind(kb)

    return kb
