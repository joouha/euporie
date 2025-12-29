"""Key bindings which are also known by GNU Readline by the given names.

This module ports the ``prompt_toolkit`` named commands to use the new command registry.
"""

from __future__ import annotations

from prompt_toolkit.key_binding.bindings.named_commands import _readline_commands

from euporie.apptk.commands import add_cmd, get_cmd
from euporie.apptk.filters import (
    buffer_has_focus,
    completion_is_selected,
    has_selection,
)
from euporie.apptk.filters.buffer import cursor_in_leading_ws
from euporie.apptk.filters.modes import insert_mode

__all__ = ["get_by_name"]

# Replace legacy named-command access methods
register = add_cmd
get_by_name = get_cmd

# Comvert existing readline commands to apptk commands
add_cmd(
    filter=buffer_has_focus & insert_mode & ~has_selection & ~cursor_in_leading_ws,
    hidden=True,
    name="next-completion",
    aliases=["menu-complete"],
    description="Show the completion menu and select the next completion.",
)(_readline_commands.pop("menu-complete").handler)


add_cmd(
    filter=buffer_has_focus
    & completion_is_selected
    & insert_mode
    & ~has_selection
    & ~cursor_in_leading_ws,
    hidden=True,
    name="previous-completion",
    aliases=["menu-complete-backward"],
    description="Show the completion menu and select the previous completion.",
)(_readline_commands.pop("menu-complete-backward").handler)

# Convert legacy named commands into Commands
for name, binding in _readline_commands.items():
    add_cmd(name=name)(binding.handler)
