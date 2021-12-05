# -*- coding: utf-8 -*-
"""Contains the `ScrollingContainer` class, which renders children on the fly."""
from __future__ import annotations

import logging
from collections import namedtuple
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Sequence, Union, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.layout.containers import (
    AnyContainer,
    Container,
    Window,
    to_container,
)
from prompt_toolkit.layout.dimension import (
    AnyDimension,
    Dimension,
    max_layout_dimensions,
    to_dimension,
)
from prompt_toolkit.layout.mouse_handlers import MouseHandler, MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import to_str

from euporie.box import Border
from euporie.cell import Cell
from euporie.config import config
from euporie.keys import KeyBindingsInfo

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

    from euporie.app import App

log = logging.getLogger(__name__)


class PrintingContainer(Container):
    """A container which displays all it's children in a vertical list."""

    def __init__(
        self,
        children: "list[Union[Callable, AnyContainer]]",
        width: "AnyDimension" = None,
    ):
        """Initiate the container."""
        self.width = width
        self.rendered = False
        self._children = children

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
    ) -> "None":
        """Render the container to a `Screen` instance.

        All children are rendered vertically in sequence.

        Args:
            screen: The :class:`~prompt_toolkit.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`prompt_toolkit.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`prompt_toolkit.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`prompt_toolkit.layout.containers.HSplit` can use it to pass
                their style down to the windows that they contain.
            z_index: Used for propagating z_index from parent to child.

        """
        xpos = write_position.xpos
        ypos = write_position.ypos

        for child in self.get_children():
            height = child.preferred_height(write_position.width, 999999).preferred
            child.write_to_screen(
                screen,
                mouse_handlers,
                WritePosition(xpos, ypos, write_position.width, height),
                parent_style,
                erase_bg,
                z_index,
            )
            ypos += height

    @property
    def children(self) -> "list[AnyContainer]":
        if callable(self._children):
            return self._children()
        else:
            return self._children

    def get_children(self) -> "list[Container]":
        """Returns a list of all child containers."""
        return map(to_container, self.children)

    def preferred_height(self, width: int, max_available_height: int) -> "Dimension":
        """Returns the preferred height, equal to the sum of the child heights."""
        return Dimension(
            min=1,
            preferred=sum(
                [
                    c.preferred_height(width, max_available_height).preferred
                    for c in self.get_children()
                ]
            ),
        )

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Calculates and returns the desired width for this container."""
        if self.width is not None:
            dim = to_dimension(self.width).preferred
            return Dimension(max=dim, preferred=dim)
        else:
            return Dimension()

    def reset(self) -> "None":
        """Reset the state of this container and all the children.

        Does nothing as this container is used for dumping output.
        """
        pass
