"""Define basic key-bindings for entering text."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.bindings.basic import (
    load_basic_bindings as ptk_load_basic_bindings,
)

from euporie.apptk.commands import add_cmd, get_cmd
from euporie.apptk.filters import (
    buffer_has_focus,
)
from euporie.apptk.filters.buffer import (
    char_after_cursor,
    cursor_at_end_of_line,
    has_matching_bracket,
)
from euporie.apptk.filters.modes import insert_mode, replace_mode
from euporie.apptk.key_binding.utils import if_no_repeat

if TYPE_CHECKING:
    from euporie.apptk.key_binding import KeyBindings, KeyPressEvent

# Commands

## Typing keys


@add_cmd(filter=buffer_has_focus, save_before=if_no_repeat, hidden=True)
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
        name=f"complete-bracket-{left}{right}",
        filter=buffer_has_focus
        & insert_mode
        & (char_after_cursor(" ") | cursor_at_end_of_line),
        save_before=if_no_repeat,
        hidden=True,
    )(partial(_complete_bracket, right))
    add_cmd(
        name=f"close-bracket-{left}{right}",
        filter=buffer_has_focus
        & insert_mode
        & char_after_cursor(right)
        & has_matching_bracket,
        save_before=if_no_repeat,
        hidden=True,
    )(partial(_skip_close_bracket, right))


def load_basic_bindings() -> KeyBindings:
    """Load basic key-bindings for text entry."""
    kb = ptk_load_basic_bindings()
    for cmd_name, keys in {
        # Typing bindings
        "type-key": "<any>",
        # Text surround bindings
        "complete-bracket-()": "(",
        "complete-bracket-[]": "[",
        "complete-bracket-{}": "{",
        "close-bracket-()": ")",
        "close-bracket-[]": "]",
        "close-bracket-{}": "}",
        # Completion bindings
        "next-completion": "c-i",
        "previous-completion": "s-tab",
        "cancel-completion": "escape",
        "accept-completion": "enter",
    }.items():
        get_cmd(cmd_name).bind(kb, keys)
    return kb
