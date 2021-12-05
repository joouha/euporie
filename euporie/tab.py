# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

import logging
from abc import ABCMeta
from pathlib import Path
from typing import Callable, Optional

from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout.containers import AnyContainer
from prompt_toolkit.layout.dimension import Dimension, to_dimension

log = logging.getLogger(__name__)


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    def __init__(self):
        """Called when the tab is created."""
        self.container = None
        self.file: "Path" = None

    def statusbar_fields(
        self,
    ) -> "tuple[list[AnyFormattedText], list[AnyFormattedText])":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([], [])

    def close(self, cb: "Optional[Callable]") -> "None":
        """Function to close a tab with a callback.

        Args:
            cb: A function to call after the tab is closed.

        """
        if callable(cb):
            cb()

    def focus(self) -> "None":
        """Focuses the tab."""
        try:
            get_app().layout.focus(self.container)
        except:
            pass

    def __pt_container__(self) -> "AnyContainer":
        """Return the main container object."""
        if hasattr(self.container, "width"):
            d = to_dimension(self.container.width)
            self.container.width = Dimension(
                min=d.min, max=d.max, preferred=d.preferred, weight=1
            )
        if hasattr(self.container, "height"):
            d = to_dimension(self.container.height)
            self.container.height = Dimension(
                min=d.min, max=d.max, preferred=d.preferred, weight=1
            )
        return self.container
