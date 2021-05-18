# -*- coding: utf-8 -*-
"""Defines KeyBindings wrapper which keeps track of key binding descriptions."""
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, cast

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import T


class KeyBindingsInfo(KeyBindings):
    """Wraps `prompt_toolkit.key_binding.KeyBinding` recording helpful deatils.

    Each key binding can be given a group and a description, which can be used to
    display a help message about which key bindings are available to the user.
    """

    details: "dict[str, dict[str, dict[tuple[Union[Keys, str]], None]]]" = {}

    def add(
        self,
        *keys: "Union[Keys, str]",
        key_str: "Optional[tuple[str]]" = None,
        group: "str" = "None",
        desc: "Optional[str]" = None,
        **kwargs: "Any",
    ) -> "Callable[[T], T]":
        """Decorator for adding a key bindings.

        As per `prompt_toolkit.key_binding.KeyBinding`, with additional arguments.

        Args:
            *keys: Keys to pass to `prompt_toolkit.key_binding.KeyBinding.add`.
            key_str: A string which can be user to over-ride the bound key sequence in
                the binding's description.
            group: The name of the group to which this key binding belongs.
            desc: A description of what this key-binding does.
            **kwargs: Key word arguments to pass to prompt_toolkit.key_binding.KeyBinding.add`.

        """
        if desc is not None:
            key = cast("tuple[Union[Keys, str]]", key_str or keys)
            self.details.setdefault(group, {}).setdefault(desc, {})[key] = None
        return super().add(*keys, **kwargs)
