"""Module concerning clipboard access and manipulation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.clipboard.base import Clipboard, ClipboardData
from prompt_toolkit.clipboard.in_memory import InMemoryClipboard
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.selection import SelectionType
from pyperclip import determine_clipboard

from euporie.core.config import add_setting
from euporie.core.io import Vt100_Output

if TYPE_CHECKING:
    from euporie.core.app import BaseApp
    from euporie.core.config import Setting
    from euporie.core.terminal import TerminalQuery

log = logging.getLogger(__name__)


class Osc52Clipboard(Clipboard):
    """Clipboard that syncs with the system clipboard using OSC52 escape codes."""

    def __init__(self, app: BaseApp) -> None:
        """Create a new instance of the clipboard."""
        self.app = app
        term_clipboard_data = app.term_info.clipboard_data
        term_clipboard_data.event += self._update_clipboard
        self._data = ClipboardData(text=term_clipboard_data.value)

    def set_data(self, data: ClipboardData) -> None:
        """Set clipboard data."""
        output = self.app.output
        if isinstance(output, Vt100_Output):
            output.set_clipboard(data.text)
            output.flush()
        self._data = data

    def get_data(self) -> ClipboardData:
        """Retrieve clipboard data."""
        # Send clipboard query
        output = self.app.output
        if isinstance(output, Vt100_Output):
            output.get_clipboard()
            output.flush()
            self.app.term_info.clipboard_data.await_response()
        return self._data

    def _update_clipboard(self, query: TerminalQuery) -> None:
        """Update the last known clipboard data."""
        text = query.value
        if text != self._data.text:
            self._data = ClipboardData(
                text=text,
                type=SelectionType.LINES if "\n" in text else SelectionType.CHARACTERS,
            )


class EuporieClipboard(Clipboard):
    """Use a clipboard determined by euporie's configuration."""

    _clipboard: Clipboard

    def __init__(self, app: BaseApp) -> None:
        """Create a new clipboard instance."""
        self.app = app
        clipboard_config = app.config.settings["clipboard"]
        self.get_clipboard(clipboard_config)
        clipboard_config.event += self.get_clipboard

    def get_clipboard(self, setting: Setting) -> None:
        """Determine which clipboard to use."""
        clipboard: Clipboard | None = None
        if setting.value == "external" and determine_clipboard()[0]:
            log.debug("Using pyperclip clipboard")
            clipboard = PyperclipClipboard()
        if not clipboard:
            if setting.value == "terminal":
                log.debug("Using terminal clipboard")
                clipboard = Osc52Clipboard(self.app)
            else:
                log.debug("Using in-memory clipboard")
                clipboard = InMemoryClipboard()
        self._clipboard = clipboard

    def set_data(self, data: ClipboardData) -> None:
        """Set data to the clipboard."""
        self._clipboard.set_data(data)

    def set_text(self, text: str) -> None:
        """Shortcut for setting plain text on clipboard."""
        self._clipboard.set_text(text)

    def rotate(self) -> None:
        """For Emacs mode, rotate the kill ring."""
        self._clipboard.rotate()

    def get_data(self) -> ClipboardData:
        """Return clipboard data."""
        return self._clipboard.get_data()

    # ################################### Settings ####################################w

    add_setting(
        name="clipboard",
        flags=["--clipboard"],
        choices=["external", "internal", "terminal"],
        type_=str,
        default="external",
        help_="The preferred clipboard access method",
        description="""
        The clipboard access method to use.
        - ``external``: Data is saved to the system clipboard using OS native tooling.
        - ``internal``: Clipboard data is only stored and usable inside euporie - it is
            not saved to the system clipboard.
        - ``terminal``: uses OSC52 escape sequences to retrieve and set the clipboard
            contents. Requires your terminal emulator to support OSC52. Works over SSH.

    """,
    )
