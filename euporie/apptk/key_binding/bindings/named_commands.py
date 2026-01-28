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

# Convert legacy named commands into Commands
for name, binding in _readline_commands.items():
    add_cmd(name=name)(binding.handler)

# Update some commands

get_cmd("menu-complete").update(
    hidden=True,
    aliases=["next-completion"],
    description="Show the completion menu and select the next completion.",
).add_keys(
    keys=["c-i"],
    filter=buffer_has_focus & insert_mode & ~has_selection & ~cursor_in_leading_ws,
)

get_cmd("menu-complete-backward").update(
    hidden=True,
    aliases=["previous-completion"],
    description="Show the completion menu and select the previous completion.",
).add_keys(
    keys=["s-tab"],
    filter=buffer_has_focus
    & completion_is_selected
    & insert_mode
    & ~has_selection
    & ~cursor_in_leading_ws,
)
