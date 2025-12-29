"""Key bindings which are also known by GNU Readline by the given names.

This module ports the ``prompt_toolkit`` named commands to use the new command registry.
"""

from __future__ import annotations

from prompt_toolkit.key_binding.bindings.named_commands import _readline_commands

from euporie.apptk.commands import add_cmd, get_cmd

__all__ = ["get_by_name"]

# Convert legacy named commands into Commands
for name, binding in _readline_commands.items():
    add_cmd(name=name)(binding.handler)

# Replace legacy named-command access methods
register = add_cmd
get_by_name = get_cmd
