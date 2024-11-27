"""Define editor key-bindings and commands for input completions."""

from __future__ import annotations

import logging

from prompt_toolkit.application import get_app
from prompt_toolkit.completion import Completion
from prompt_toolkit.filters import (
    buffer_has_focus,
    completion_is_selected,
    has_completions,
    has_selection,
)
from prompt_toolkit.key_binding.bindings.named_commands import (
    menu_complete,
    menu_complete_backward,
)

from euporie.core.commands import add_cmd
from euporie.core.filters import cursor_in_leading_ws, insert_mode
from euporie.core.key_binding.registry import register_bindings

log = logging.getLogger(__name__)


add_cmd(
    filter=buffer_has_focus & insert_mode & ~has_selection & ~cursor_in_leading_ws,
    hidden=True,
    name="next-completion",
    description="Show the completion menu and select the next completion.",
)(menu_complete)


add_cmd(
    filter=buffer_has_focus
    & completion_is_selected
    & insert_mode
    & ~has_selection
    & ~cursor_in_leading_ws,
    hidden=True,
    name="previous-completion",
    description="Show the completion menu and select the previous completion.",
)(menu_complete_backward)


@add_cmd(
    filter=has_completions,
    hidden=True,
    eager=True,
)
def cancel_completion() -> None:
    """Cancel a completion."""
    get_app().current_buffer.cancel_completion()


@add_cmd(filter=completion_is_selected, hidden=True)
def accept_completion() -> None:
    """Accept a selected completion."""
    buffer = get_app().current_buffer
    complete_state = buffer.complete_state
    if complete_state and isinstance(complete_state.current_completion, Completion):
        buffer.apply_completion(complete_state.current_completion)


register_bindings(
    {
        "euporie.core.app.app:BaseApp": {
            "next-completion": "c-i",
            "previous-completion": "s-tab",
            "cancel-completion": "escape",
            "accept-completion": "enter",
        }
    }
)
