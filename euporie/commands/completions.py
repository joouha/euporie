"""Defines commands relating to completions."""

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

from euporie.commands.registry import add
from euporie.filters import cell_is_code, cursor_in_leading_ws, insert_mode

add(
    keys="c-i",
    filter=buffer_has_focus
    & insert_mode
    & ~has_selection
    & cell_is_code
    & ~cursor_in_leading_ws,
    hidden=True,
    name="next-completion",
    group="completion",
    description="Show the completion menu and select the next completion.",
)(menu_complete)
add(
    keys="s-tab",
    filter=buffer_has_focus
    & completion_is_selected
    & insert_mode
    & ~has_selection
    & ~cursor_in_leading_ws,
    hidden=True,
    name="previous-completion",
    group="completion",
    description="Show the completion menu and select the previous completion.",
)(menu_complete_backward)


@add(
    keys="escape",
    filter=completion_is_selected & has_completions,
    hidden=True,
    group="completion",
    eager=True,
)
def cancel_completion() -> "None":
    """Cancel a completion."""
    get_app().current_buffer.cancel_completion()


@add(keys="enter", filter=completion_is_selected, hidden=True, group="completion")
def accept_completion() -> "None":
    """Accept a selected completion."""
    buffer = get_app().current_buffer
    complete_state = buffer.complete_state
    if complete_state:
        if isinstance(complete_state.current_completion, Completion):
            buffer.apply_completion(complete_state.current_completion)
            get_app().layout.focus(buffer)
