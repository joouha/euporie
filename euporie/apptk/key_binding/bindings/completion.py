"""Define editor key-bindings and commands for input completions."""

from __future__ import annotations

import logging

from euporie.apptk.application.current import get_app

from euporie.apptk.commands import add_cmd
from euporie.apptk.completion import Completion
from euporie.apptk.filters import (
    completion_is_selected,
    has_completions,
)

log = logging.getLogger(__name__)


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
