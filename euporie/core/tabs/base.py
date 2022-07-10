"""Contains the main class for a notebook file."""

from __future__ import annotations

import logging
from abc import ABCMeta
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import Window, _Split
from prompt_toolkit.layout.dimension import Dimension, to_dimension

from euporie.core.app import get_app

if TYPE_CHECKING:
    from os import PathLike
    from typing import Callable, Optional, Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app import EuporieApp

log = logging.getLogger(__name__)


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    container: "AnyContainer"

    def __init__(
        self, app: "Optional[EuporieApp]" = None, path: "Optional[PathLike]" = None
    ):
        """Called when the tab is created."""
        self.app: "EuporieApp" = app or get_app()
        self.app.container_statuses[self] = self.statusbar_fields
        self.container = Window()

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([], [])

    @property
    def title(self) -> "str":
        """Return the tab title."""
        return ""

    def save(self) -> "None":
        """Save the tab."""

    def close(self, cb: "Optional[Callable]" = None) -> "None":
        """Function to close a tab with a callback.

        Args:
            cb: A function to call after the tab is closed.

        """
        if self in self.app.container_statuses:
            del self.app.container_statuses[self]
        if callable(cb):
            cb()

    def focus(self) -> "None":
        """Focuses the tab (or make it visible)."""
        self.app.focus_tab(self)

    def __pt_container__(self) -> "AnyContainer":
        """Return the main container object."""
        container = self.container
        # Ensure tab dimensions are equally weighted
        if isinstance(container, _Split):
            d = to_dimension(container.width)
            container.width = Dimension(
                min=d.min, max=d.max, preferred=d.preferred, weight=1
            )
            d = to_dimension(container.height)
            container.height = Dimension(
                min=d.min, max=d.max, preferred=d.preferred, weight=1
            )
        return container
