# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.key_binding import KeyBindings, KeyBindingsBase

from euporie.commands import get

log = logging.getLogger(__name__)


def dict_bindings(binding_dict: "dict[str, str]") -> "KeyBindingsBase":
    kb = KeyBindings()
    for command, keys in binding_dict.items():
        get(command).bind(kb, keys)
    return kb
