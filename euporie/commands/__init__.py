"""Defines a centralized command system."""

from euporie.commands import (  # search,
    app,
    buffer,
    cell,
    cell_output,
    completions,
    config,
    notebook,
    pager,
    search,
    suggestions,
)
from euporie.commands.base import Command
from euporie.commands.registry import add, commands, get

__all__ = [
    "Command",
    "add",
    "get",
    "commands",
    "config",
    "app",
    "buffer",
    "cell",
    "cell_output",
    "completions",
    "notebook",
    "pager",
    "search",
    "suggestions",
]
