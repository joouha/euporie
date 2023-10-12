"""Define basic key-bindings for entering text."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters import (
    buffer_has_focus,
)
from prompt_toolkit.key_binding import ConditionalKeyBindings

from euporie.core.commands import add_cmd
from euporie.core.filters import (
    micro_mode,
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
        "euporie.core.key_binding.bindings.basic.TextEntry": {
            "type-key": "<any>",
        },
    }
)


def load_basic_bindings(config: Config | None = None) -> KeyBindingsBase:
    """Load basic key-bindings for text entry."""
    return ConditionalKeyBindings(
        load_registered_bindings(
            "euporie.core.key_binding.bindings.basic.TextEntry", config=config
        ),
        micro_mode,
    )


# Commands


@add_cmd(
    filter=buffer_has_focus,
    save_before=if_no_repeat,
    hidden=True,
)
def type_key(event: KeyPressEvent) -> None:
    """Enter a key."""
    # Do not insert escape sequences
    if not event.data.startswith("\x1b["):
        event.current_buffer.insert_text(
            event.data * event.arg, overwrite=replace_mode()
        )
