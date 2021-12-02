# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

import logging
from abc import ABCMeta
from typing import Callable, Optional

from prompt_toolkit.application.current import get_app
from prompt_toolkit.layout.containers import AnyContainer

log = logging.getLogger(__name__)


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    def __init__(self):
        """Called when the tab is created."""
        self.container = None

    def close(self, cb: "Optional[Callable]") -> "None":
        """Function to close a tab.

        Args:
            cb: A function to call after the tab is closed.

        """
        if callable(cb):
            cb()

    def focus(self) -> "None":
        """Focuses the tab."""
        get_app().layout.focus(self.container)

    def statusbar_fields(self) -> "list[str]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return []

    def __pt_container__(self) -> "AnyContainer":
        """Return the main container object."""
        return self.container
