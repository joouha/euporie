"""Utility functions for loading key-bindings."""

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings, KeyBindingsBase
from prompt_toolkit.keys import Keys

from euporie.commands.registry import get

if TYPE_CHECKING:
    from typing import Dict, List, Tuple, Union

    from euporie.commands.base import AnyKeys

__all__ = ["dict_bindings"]


KEY_ALIASES: "Dict[Union[str, Keys], str]" = {
    Keys.ControlH: "backspace",
    Keys.ControlM: "enter",
    Keys.ControlI: "tab",
    Keys.ControlUnderscore: "c-/",
    Keys.ControlAt: "c-space",
}


def dict_bindings(binding_dict: "Dict[str, AnyKeys]") -> "KeyBindingsBase":
    """Assign key-bindings to commands based on a dictionary."""
    kb = KeyBindings()
    for command, keys in binding_dict.items():
        get(command).bind(kb, keys)
    return kb


def _format_key_str(key: "str") -> "str":
    key = key.replace("c-", "Ctrl+").replace("s-", "Shift+")
    if min(map(len, key.split("+"))) > 1:
        key = key.title()
    return key


def format_keys(keys: "List[Tuple[Union[str, Keys], ...]]") -> "List[str]":
    """Converts a list of tuples of keys to a string."""
    s: "List[str]" = []

    # Add duplicate key aliases to the list
    keys_: "List[Tuple[Union[str, Keys], ...]]" = []
    for key in keys:
        if len(key) == 1 and key[0] in KEY_ALIASES:
            keys_.append((KEY_ALIASES[key[0]],))
        keys_.append(key)

    # Format the key text
    for key in keys_:
        if isinstance(key, tuple):
            s.append(
                ", ".join([_format_key_str(k) for k in key])
                .replace("Escape, ", "Alt+")
                .replace("Alt+Ctrl+m", "Ctrl+Alt+Enter")
            )
        elif isinstance(key, str):
            s.append(_format_key_str(key))
        else:
            s.append(_format_key_str(key.value))

    # Remove duplicate entries but keep the order
    keys_ = list(dict(zip(keys, range(len(keys)))).keys())

    return s
