"""Contain a tab for displaying JSON data."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.layout.scroll import ScrollingContainer
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import Tab
from euporie.core.widgets.tree import JsonView

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class JsonTab(Tab):
    """Tab class for JSON data."""

    name = "JSON Viewer"
    mime_types: ClassVar[set[str]] = {"*json"}
    file_types: ClassVar[dict[str, None]] = {".json": None}

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

        data = json.load(self.path.open())

        return VSplit(
            [
                scroll := ScrollingContainer(
                    children=[JsonView(data, title=self.path.name, expanded=True)]
                ),
                MarginContainer(ScrollbarMargin(), target=scroll),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )
