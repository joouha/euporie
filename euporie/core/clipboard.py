"""Module concerning clipboard access and manipulation."""

from __future__ import annotations

import logging

import pyperclip
from prompt_toolkit.clipboard.base import Clipboard, ClipboardData
from prompt_toolkit.clipboard.in_memory import InMemoryClipboard
from prompt_toolkit.clipboard.pyperclip import (
    PyperclipClipboard as PtkPyperclipClipboard,
)
from prompt_toolkit.selection import SelectionType

from euporie.core.app.current import get_app

log = logging.getLogger(__name__)


class PyperclipClipboard(PtkPyperclipClipboard):
    """Pyperclip clipboard which suppresses pyperclip exceptions."""

    def set_data(self, data: ClipboardData) -> None:
        """Set the clipboard data, ignoring any clipboard errors."""
        self._data = data
        try:
            pyperclip.copy(data.text)
        except pyperclip.PyperclipException:
            log.exception("Failed to set clipboard data")


class Osc52Clipboard(Clipboard):
    """Clipboard that syncs with the system clipboard using OSC52 escape codes."""

    def __init__(self) -> None:
        """Create a new instance of the clipboard."""
        self._data = ClipboardData()

    def set_data(self, data: ClipboardData) -> None:
        """Set clipboard data."""
        from euporie.core.io import Vt100_Output

        output = get_app().output
        if isinstance(output, Vt100_Output):
            output.set_clipboard(data.text)
            output.flush()
        self._data = data

    def get_data(self) -> ClipboardData:
        """Retrieve clipboard data."""
        from euporie.core.io import Vt100_Output
        from euporie.core.key_binding.key_processor import KeyProcessor

        # Send clipboard query
        app = get_app()
        output = app.output
        # Request clipboard contents from terminal
        if isinstance(output, Vt100_Output):
            from euporie.core.keys import MoreKeys

            output.get_clipboard()
            output.flush()
            # Wait for terminal response
            if isinstance(app.key_processor, KeyProcessor):
                app.key_processor.await_key(MoreKeys.ClipboardDataResponse)
        return self._data

    def sync(self, text: str) -> None:
        """Update the last known clipboard data."""
        if text != self._data.text:
            self._data = ClipboardData(
                text=text,
                type=SelectionType.LINES if "\n" in text else SelectionType.CHARACTERS,
            )


CONFIGURED_CLIPBOARDS = {
    "internal": InMemoryClipboard,
    "external": PyperclipClipboard,
    "terminal": Osc52Clipboard,
}
