"""Defines default key-bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings

from euporie.core.commands import get_cmd
from euporie.core.config import Config
from euporie.core.current import get_app
from euporie.core.keys import Keys

if TYPE_CHECKING:

    from typing import Dict, List, Optional, Tuple, Union

    from prompt_toolkit.key_binding import KeyBindingsBase

    AnyKey = Union[Tuple[Union[Keys, str], ...], Keys, str]
    AnyKeys = Union[List[AnyKey], AnyKey]

    KeyBindingDefs = Dict[str, AnyKeys]

BINDINGS: "dict[str, KeyBindingDefs]" = {}


def register_bindings(bindings: "dict[str, KeyBindingDefs]") -> "None":
    """Updates the key-binding registry."""
    for group, items in bindings.items():
        if group not in BINDINGS:
            BINDINGS[group] = {}
        for command, keys in items.items():
            BINDINGS[group][command] = keys


def load_registered_bindings(
    *names: "str", config: "Optional[Config]" = None
) -> "KeyBindingsBase":
    """Assign key-bindings to commands based on a dictionary."""
    from euporie.core.app import BaseApp

    app = get_app()
    if config is None and isinstance(app, BaseApp):
        config = app.config

    kb = KeyBindings()
    for name in names:
        binding_dict = BINDINGS.get(name, {})
        # Augment with bindings from config
        if config is not None:
            binding_dict.update(config.key_bindings.get(name, {}))
        for command, keys in binding_dict.items():
            get_cmd(command).bind(kb, keys)
    return kb
