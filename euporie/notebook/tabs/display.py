"""Contain a tab for displaying files."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.convert.datum import Datum
from euporie.core.convert.mime import MIME_FORMATS, get_format
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import Tab
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class DisplayTab(Tab):
    """Tab class for displaying files."""

    name = "File Viewer"
    mime_types: ClassVar[set[str]] = set(MIME_FORMATS.keys())

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        super().__init__(app, path)

        # Load file and container in background
        if self.path is not None:

            def _load() -> None:
                self.container = self.load_container()
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
            Datum(
                data=self.path.read_bytes(),
                format=get_format(self.path),
                path=self.path,
            ),
            focusable=True,
            focus_on_click=True,
            always_hide_cursor=True,
            dont_extend_height=False,
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

    def write_file(self, path: Path) -> None:
        """Write the file's text data to a path.

        Args:
            path: An path at which to save the file

        """
        data = self.display.datum.data
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            raise NotImplementedError(f"Cannot save '{self.display.datum.format}' file")
