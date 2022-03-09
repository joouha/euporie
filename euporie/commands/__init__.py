"""Defines a centralized command system."""

from euporie.commands import (  # search,
    buffer,
    cell,
    cell_output,
    completions,
    config,
    notebook,
    pager,
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
    "cell_output",
    "completions",
    "notebook",
    "pager",
    # "search",
    "suggestions",
]
