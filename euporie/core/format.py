"""Contain functions to automatically format code cell input."""

from __future__ import annotations

import logging
import subprocess
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from euporie.core.filters import command_exists

if TYPE_CHECKING:
    from pathlib import Path


log = logging.getLogger(__name__)


class Formatter(metaclass=ABCMeta):
    """Text formatter class which reformats text."""

    def __init__(self, languages: set[str] | None = None) -> None:
        """Initialize a new formatter."""
        self.languages = languages or set()

    def _format(self, text: str, language: str) -> str:
        """Check the language matches, then format the input."""
        log.debug("Formatting using %s", self)
        if not self.languages or language in self.languages:
            return self.format(text)
        return text

    @abstractmethod
    def format(self, text: str) -> str:
        """Format the string."""
        return text


class CliFormatter(Formatter):
    """Format using an external command."""

    def __init__(self, command: list[str], languages: set[str] | None = None) -> None:
        """Create a new command formatter."""
        self.command = command
        self.filter = command_exists(command[0])
        super().__init__(languages=languages)

    def _format(self, text: str, language: str) -> str:
        """Check the filter value early."""
        if self.filter():
            return super()._format(text, language)
        return text

    def format(self, text: str) -> str:
        """Pass the text to the command over stdin and return the output."""
        try:
            proc = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except Exception:
            return text
        try:
            output, _error = proc.communicate(text)
        except Exception:
            return text
        else:
            return output



