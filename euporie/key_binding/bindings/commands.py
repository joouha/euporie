# -*- coding: utf-8 -*-
from prompt_toolkit.key_binding import (
    ConditionalKeyBindings,
    KeyBindings,
    KeyBindingsBase,
)

from euporie.commands import commands


def command_default_bindings() -> "KeyBindings":
    kb = KeyBindings()
    for cmd in commands.values():
        kb._bindings += cmd.key_bindings

    return kb
