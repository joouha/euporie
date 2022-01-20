"""Utility functions for loading key-bindings."""

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings, KeyBindingsBase

from euporie.commands import get

if TYPE_CHECKING:
    from euporie.commands.base import AnyKeys

__all__ = ["dict_bindings"]


def dict_bindings(binding_dict: "dict[str, AnyKeys]") -> "KeyBindingsBase":
    """Assign key-bindings to commands based on a dictionary."""
    kb = KeyBindings()
    for command, keys in binding_dict.items():
        get(command).bind(kb, keys)
    return kb
