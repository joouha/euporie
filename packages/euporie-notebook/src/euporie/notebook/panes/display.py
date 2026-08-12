"""Contain a tab for displaying files."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, ClassVar

from apptk.convert.datum import Datum
from apptk.convert.mime import MIME_FORMATS, get_format
from apptk.layout.containers import MarginContainer, VSplit
from apptk.layout.dimension import Dimension
from apptk.layout.display import Display
from apptk.layout.margins import ScrollbarMargin

from euporie.core.panes.base import Pane
from euporie.core.path import safe_write

if TYPE_CHECKING:
    from pathlib import Path

    from apptk.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class DisplayPane(Pane):
    """Pane class for displaying files."""

    name = "File Viewer"
    mime_types: ClassVar[set[str]] = set(MIME_FORMATS.keys())

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        super().__init__(app, path)
        self.datum = Datum(
            data="(No data to display)",
            format="ansi",
            path=self.path,
        )

        # Load file and container in background
        def _load() -> None:
            self.container = self.load_container()
            if self.path is not None:
                self.read_file(self.path)
            self.app.layout.focus(self.container)
            self.app.invalidate()

        app.create_background_task(asyncio.to_thread(_load))

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        return ([str(self.path)], [])

    @property
    def title(self) -> str:
        """Return the tab title."""
        if self.path is not None:
            return str(self.path.name) or str(self.path)
        else:
            return "<file>"

    def load_container(self) -> AnyContainer:
        """Abcract method for loading the notebook's main container."""
        assert self.path is not None

        self.display = Display(
            self.datum,
            expand_height=True,
            focusable=True,
            focus_on_click=True,
            always_hide_cursor=True,
            scrollbar=False,
        )
        return VSplit(
            [
                self.display,
                MarginContainer(ScrollbarMargin(), target=self.display.window),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )

    def read_file(self, path: Path) -> None:
        """Read file data from a path.

        Args:
            path: A path from which to read the file

        """
        try:
            data = path.read_bytes()
        except (FileNotFoundError, NotImplementedError):
            return
        self.datum = Datum(data=data, format=get_format(path), path=path)
        self.display.datum = self.datum

    def write_file(self, path: Path) -> None:
        """Write the file's text data to a path.

        Args:
            path: An path at which to save the file

        """
        data = self.display.datum.data
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, bytes):
            with safe_write(path, mode="wb") as open_file:
                open_file.write(data)
        else:
            raise NotImplementedError(f"Cannot save '{self.display.datum.format}' file")
