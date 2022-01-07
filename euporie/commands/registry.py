# -*- coding: utf-8 -*-
import logging
from inspect import isawaitable, signature

from prompt_toolkit.buffer import indent, unindent
from prompt_toolkit.filters import to_filter
from prompt_toolkit.key_binding.key_bindings import (
    Binding,
    KeyBindings,
    _parse_key,
    key_binding,
)
from prompt_toolkit.keys import Keys

from euporie.commands.base import Command

log = logging.getLogger(__name__)


commands: "dict[str, Command]" = {}


def add(**kwargs: "Any"):
    """Adds a command to the centralized command system."""

    def decorator(handler: "Callable") -> "Callable":
        cmd = Command(handler, **kwargs)
        commands[cmd.name] = cmd
        return handler

    return decorator


def get(name: "str"):
    """Get a command from the centralized command system by name."""
    try:
        return commands[name]
    except KeyError as e:
        raise KeyError("Unknown command: %r" % name) from e
