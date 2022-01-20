"""Load the default bindings assigned to commands."""

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings

from euporie.commands import commands

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase


def command_default_bindings() -> "KeyBindingsBase":
    """Load the default bindings assigned to each command."""
    kb = KeyBindings()
    for cmd in commands.values():
        kb._bindings += cmd.key_bindings

    return kb
