"""Contain functions to automatically format code cell input."""

from __future__ import annotations

import logging
import subprocess
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from euporie.core.filters import command_exists
from euporie.core.lsp import range_to_slice

if TYPE_CHECKING:
    from pathlib import Path

    from euporie.core.lsp import LspClient


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
            output, error = proc.communicate(text)
        except Exception:
            return text
        else:
            if output and not error:
                return output.rstrip("\r\n")
            else:
                return text

    def __repr__(self) -> str:
        """Return representation of the formatter as a string."""
        return f"{self.command[0].title()}Formatter()"


class LspFormatter(Formatter):
    """Format a document using a LSP server."""

    def __init__(
        self, lsp: LspClient, path: Path, languages: set[str] | None = None
    ) -> None:
        """Record the LSP client and file path for formatting."""
        self.lsp = lsp
        self.path = path
        super().__init__(languages=languages)

    def format(self, text: str) -> str:
        """Format the url with the LSP.

        The LSP already knows the contents of the file, which is why we do not pass the
        text to the formatting function.
        """
        # Ensure that the LSP has the latest version of the file contents
        try:
            changes = self.lsp.format(path=self.path)
        except Exception:  # noqa: S110
            pass
        else:
            for change in changes or []:
                if new := change.get("newText"):
                    # Convert line/char to position ranges
                    range_ = change.get("range", {})
                    start = range_.get("start", {})
                    start_line = start.get("line", 0)
                    start_char = start.get("character", 0)
                    end = range_.get("end", {})
                    end_line = end.get("line", 0)
                    end_char = end.get("character", 0)
                    segment = range_to_slice(
                        start_line, start_char, end_line, end_char, text
                    )
                    text = f"{text[: segment.start]}{new}{text[segment.stop :]}"
            text = text.rstrip()

        return text

    def __repr__(self) -> str:
        """Return representation of the formatter as a string."""
        return f"{self.lsp.name.title()}Formatter()"
