"""A terminal tab."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from ptterm import Terminal
from upath import UPath

from euporie.core.tabs.base import Tab

if TYPE_CHECKING:
    from pathlib import Path

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class TerminalTab(Tab):
    """Tab class for an interactive terminal."""

    name = "Terminal"

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        self._untitled_count += 1
        path = UPath(f"untitled:/terminal-{self._untitled_count}")

        super().__init__(app, path)

        self.terminal = Terminal(
            command=[os.getenv("SHELL") or "/bin/sh"],
            done_callback=lambda: self.app.close_tab(self),
        )
        # Kill terminal process on tab close
        self.on_close += lambda tab: self.terminal.terminal_control.process.kill()

        self.container = self.terminal

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        return (
            [
                self.terminal.terminal_control.process.screen.title
                or self.terminal.terminal_control.process.get_cwd(),
            ],
            [],
        )

    @property
    def title(self) -> str:
        """Return the tab title."""
        if self.path is not None:
            return str(self.path.name) or str(self.path)
        else:
            return "<terminal>"
