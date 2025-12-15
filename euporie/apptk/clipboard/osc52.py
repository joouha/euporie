"""Module concerning clipboard access and manipulation."""

from __future__ import annotations

import logging

from euporie.apptk.application.current import get_app
from euporie.apptk.clipboard.base import Clipboard, ClipboardData
from euporie.apptk.selection import SelectionType

log = logging.getLogger(__name__)


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
