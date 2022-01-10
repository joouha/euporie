"""Defines functions to manage the command registry."""

from typing import TYPE_CHECKING

from euporie.commands.base import Command

if TYPE_CHECKING:
    from typing import Any, Callable, Dict


commands: "Dict[str, Command]" = {}


def add(**kwargs: "Any") -> "Callable":
    """Adds a command to the centralized command system."""

    def decorator(handler: "Callable") -> "Callable":
        cmd = Command(handler, **kwargs)
        commands[cmd.name] = cmd
        return handler

    return decorator


def get(name: "str") -> "Command":
    """Get a command from the centralized command system by name."""
    try:
        return commands[name]
    except KeyError as e:
        raise KeyError("Unknown command: %r" % name) from e
