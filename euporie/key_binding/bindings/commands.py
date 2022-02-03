"""Load the default bindings assigned to commands."""

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings

from euporie.commands.registry import commands

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.key_binding import KeyBindingsBase


def load_command_bindings(*groups: "Optional[str]") -> "KeyBindingsBase":
    """Loads key-bindings for command belonging to a list of groups."""
    kb = KeyBindings()
    if groups is None:
        groups = []
    for cmd in commands.values():
        if not groups or cmd.group in groups:
            kb._bindings += cmd.key_bindings
    return kb
