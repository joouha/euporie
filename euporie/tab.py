"""Contains the main class for a notebook file."""

from __future__ import annotations

import logging
from abc import ABCMeta
from typing import TYPE_CHECKING

from prompt_toolkit.layout.dimension import Dimension, to_dimension

from euporie.app.current import get_base_app as get_app

if TYPE_CHECKING:
    from typing import Callable, Optional, Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer, _Split

log = logging.getLogger(__name__)

__all__ = ["Tab"]


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    container: "_Split"

    def __init__(self):
        """Called when the tab is created."""
        get_app().container_statuses[self] = self.statusbar_fields

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([], [])

    @property
    def title(self) -> "str":
        """Return the tab title."""
        return ""

    def close(self, cb: "Optional[Callable]") -> "None":
        """Function to close a tab with a callback.

        Args:
            cb: A function to call after the tab is closed.

        """
        app = get_app()
        if self in app.container_statuses:
            del app.container_statuses[self]
        if callable(cb):
            cb()

    def focus(self) -> "None":
        """Focuses the tab."""
        try:
            get_app().layout.focus(self.container)
        except Exception:
            log.debug("Could not focus %s", self)

    def __pt_container__(self) -> "AnyContainer":
        """Return the main container object."""
        container = self.container
        # Ensure tab dimensions are equally weighted
        if hasattr(container, "width"):
            d = to_dimension(container.width)
            container.width = Dimension(
                min=d.min, max=d.max, preferred=d.preferred, weight=1
            )
        if hasattr(container, "height"):
            d = to_dimension(container.height)
            container.height = Dimension(
                min=d.min, max=d.max, preferred=d.preferred, weight=1
            )
        return container
