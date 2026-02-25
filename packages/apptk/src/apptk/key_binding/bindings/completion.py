"""Define editor key-bindings and commands for input completions."""

from __future__ import annotations

import logging

from apptk.application.current import get_app
from apptk.commands import add_cmd
from apptk.completion import Completion
from apptk.filters import (
    completion_is_selected,
    has_completions,
)

log = logging.getLogger(__name__)


@add_cmd(
    keys=["escape"],
    filter=has_completions,
    hidden=True,
    eager=True,
)
def cancel_completion() -> None:
    """Cancel a completion."""
    get_app().current_buffer.cancel_completion()


@add_cmd(keys=["enter"], filter=completion_is_selected, hidden=True)
def accept_completion() -> None:
    """Accept a selected completion."""
    buffer = get_app().current_buffer
    complete_state = buffer.complete_state
    if complete_state and isinstance(complete_state.current_completion, Completion):
        buffer.apply_completion(complete_state.current_completion)
