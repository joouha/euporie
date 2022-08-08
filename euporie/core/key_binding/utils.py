"""Utility functions for formatting key-bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.key_bindings import _parse_key

from euporie.core.keys import Keys

if TYPE_CHECKING:
    from typing import Union

    from euporie.core.key_binding.registry import AnyKeys


KEY_ALIASES: "dict[Union[str, Keys], str]" = {
    Keys.ControlH: "backspace",
    Keys.ControlM: "enter",
    Keys.ControlI: "tab",
    Keys.ControlUnderscore: "c-/",
    Keys.ControlAt: "c-space",
}


def parse_keys(keys: "AnyKeys") -> "list[tuple[Union[str, Keys], ...]]":
    """Parse a list of keys."""
    output: "list[tuple[Union[str, Keys], ...]]" = []
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys:
        if isinstance(key, Keys):
            output.append((key,))
        elif isinstance(key, tuple):
            output.append(tuple(_parse_key(k) for k in key))
        else:
            output.append((_parse_key(key),))
    return output


def _format_key_str(key: "str") -> "str":
    if key:
        key = key.replace("c-", "Ctrl+").replace("s-", "Shift+")
        parts = key.split("+")
        if parts[-1].isupper():
            parts.insert(-1, "Shift")
            key = "+".join(parts)
    return key.title()


def format_keys(keys: "list[tuple[Union[str, Keys], ...]]") -> "list[str]":
    """Converts a list of tuples of keys to a string."""
    s: "list[str]" = []

    # Add duplicate key aliases to the list
    keys_: "list[tuple[Union[str, Keys], ...]]" = []
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
