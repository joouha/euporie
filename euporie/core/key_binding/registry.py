"""Defines default key-bindings."""

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings

from euporie.core.commands import get_cmd

if TYPE_CHECKING:

    from typing import Dict, List, Tuple, Union

    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.keys import Keys

    KeyBindingDefs = Dict[
        str,
        Union[
            List[Union[Tuple[Union[Keys, str], ...], Keys, str]],
            Union[Tuple[Union[Keys, str], ...], Keys, str],
        ],
    ]

BINDINGS: "Dict[str, KeyBindingDefs]" = {}


def register_bindings(bindings: "Dict[str, KeyBindingDefs]") -> "None":
    """Updates the key-binding registry."""
    for group, items in bindings.items():
        if group not in BINDINGS:
            BINDINGS[group] = {}
        for command, keys in items.items():
            BINDINGS[group][command] = keys


def load_registered_bindings(*names: "str") -> "KeyBindingsBase":
    """Assign key-bindings to commands based on a dictionary."""
    kb = KeyBindings()
    for name in names:
        binding_dict = BINDINGS.get(name, {})
        # TODO - augment with bindings from config
        for command, keys in binding_dict.items():
            get_cmd(command).bind(kb, keys)
    return kb
