"""Contain a tab for displaying JSON data."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, ClassVar

from apptk.layout.containers import MarginContainer, VSplit, to_container
from apptk.layout.dimension import Dimension
from apptk.layout.margins import ScrollbarMargin

from euporie.core.panes.base import Pane
from euporie.core.widgets.tree import JsonView

if TYPE_CHECKING:
    from pathlib import Path

    from apptk.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class JsonPane(Pane):
    """Pane class for JSON data."""

    name = "JSON Viewer"
    mime_types: ClassVar[set[str]] = {"*json"}
    file_types: ClassVar[dict[str, None]] = {".json": None}

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        super().__init__(app, path)
        self.data = {}

        async def _load() -> None:
            # Load notebook file
            if self.path is not None:
                self.read_file(self.path)
            # Load and focus container
            prev = self.container
            self.container = self.load_container()
            # Update the focus if the old container had focus
            if self.app.layout.has_focus(prev):
                self.focus()

        self.app.create_background_task(_load())

    def load_container(self) -> AnyContainer:
        """Actually load the main container."""
        view = JsonView(self.data, title=self.title, expanded=True)
        return VSplit(
            [
                view,
                MarginContainer(ScrollbarMargin(), target=to_container(view)),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )

    @property
    def title(self) -> str:
        """Return the tab title."""
        if self.path is not None:
            return str(self.path.name) or str(self.path)
        else:
            return "<file>"

    def read_file(self, path: Path) -> None:
        """Read JSON data from a path.

        Args:
            path: A path from which to read the file

        """
        self.data.clear()
        try:
            with path.open() as f:
                self.data.update(json.load(f))
        except (FileNotFoundError, NotImplementedError):
            pass
        self.app.invalidate()

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        return ([str(self.path)], [])
