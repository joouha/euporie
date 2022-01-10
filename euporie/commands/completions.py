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
from euporie.filters import insert_mode

add(
    keys="c-i",
    filter=buffer_has_focus & insert_mode & ~has_selection,
    name="next-completion",
)(menu_complete)
add(
    keys="s-tab",
    filter=buffer_has_focus & insert_mode & ~has_selection,
    name="previous-completion",
)(menu_complete_backward)


@add(keys="escape", filter=has_completions, eager=True)
def cancel_completion() -> "None":
    """Cancel a completion with the escape key."""
    get_app().current_buffer.cancel_completion()


@add(keys="enter", filter=completion_is_selected)
def accept_completion() -> "None":
    """Cancel a completion with the escape key."""
    buffer = get_app().current_buffer
    complete_state = buffer.complete_state
    if complete_state:
        if isinstance(complete_state.current_completion, Completion):
            buffer.apply_completion(complete_state.current_completion)
