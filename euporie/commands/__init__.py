"""Defines a centralized command system."""

from euporie.commands import (  # search,
    buffer,
    cell,
    completions,
    config,
    notebook,
    suggestions,
    tui,
)
from euporie.commands.base import Command
from euporie.commands.registry import add, commands, get

__all__ = [
    "Command",
    "add",
    "get",
    "commands",
    "config",
    "tui",
    "buffer",
    "cell",
    "completions",
    "notebook",
    # "search",
    "suggestions",
]
