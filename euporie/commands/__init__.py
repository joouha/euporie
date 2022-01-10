"""Defines a centralized command system."""

from euporie.commands import (  # search,
    app,
    buffer,
    cell,
    completions,
    notebook,
    suggestions,
)
from euporie.commands.base import Command
from euporie.commands.registry import add, commands, get

__all__ = [
    "Command",
    "add",
    "get",
    "commands",
    "app",
    "buffer",
    "cell",
    "completions",
    "notebook",
    # "search",
    "suggestions",
]
