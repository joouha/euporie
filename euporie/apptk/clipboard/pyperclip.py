"""Module concerning clipboard access and manipulation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pyperclip
from prompt_toolkit.clipboard.pyperclip import (
    PyperclipClipboard as PtkPyperclipClipboard,
)

if TYPE_CHECKING:
    from euporie.apptk.clipboard.base import ClipboardData

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
