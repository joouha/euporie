"""Define basic key-bindings for entering text."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters import (
    buffer_has_focus,
)

from euporie.core.commands import add_cmd
from euporie.core.filters import (
    char_after_cursor,
    cursor_at_end_of_line,
    has_matching_bracket,
    insert_mode,
    replace_mode,
)
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.key_binding.utils import if_no_repeat

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase, KeyPressEvent

    from euporie.core.config import Config

log = logging.getLogger(__name__)


class TextEntry:
    """Basic key-bindings for text entry."""

    # Register default bindings for micro edit mode
    register_bindings(
        {
            "euporie.core.key_binding.bindings.basic:TextEntry": {
                "type-key": "<any>",
                "complete-bracket-()": "(",
                "complete-bracket-[]": "[",
                "complete-bracket-{}": "{",
                "close-bracket-()": ")",
                "close-bracket-[]": "]",
                "close-bracket-{}": "}",
            },
        }
    )


def load_basic_bindings(config: Config | None = None) -> KeyBindingsBase:
    """Load basic key-bindings for text entry."""
    # Load additional key definitions
    from euporie.core import keys  # noqa: F401

    return load_registered_bindings(
        "euporie.core.key_binding.bindings.basic:TextEntry", config=config
    )


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
