"""Contains the `ScrollingContainer` class, which renders children on the fly."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import (
    AnyContainer,
    Container,
    Window,
    to_container,
)
from prompt_toolkit.layout.dimension import AnyDimension, Dimension, to_dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Screen, WritePosition

if TYPE_CHECKING:
    from typing import Callable, Optional, Sequence, Union

__all__ = ["PrintingContainer"]

log = logging.getLogger(__name__)


class PrintingContainer(Container):
    """A container which displays all it's children in a vertical list."""

    def __init__(
        self,
        children: "Union[Callable, Sequence[AnyContainer]]",
        width: "AnyDimension" = None,
    ):
        """Initiate the container."""
        self.width = width
        self.rendered = False
        self._children = children

    @property
    def children(self) -> "Sequence[AnyContainer]":
        """Returns the container's children."""
        if callable(self._children):
            children = self._children()
        else:
            children = self._children
        return children or [Window()]

    def get_children(self) -> "list[Container]":
        """Returns a list of all child containers."""
        return list(map(to_container, self.children))

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

        children = self.get_children()
        for child in children:
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
            return Dimension(max_available_width)

    def reset(self) -> "None":
        """Reset the state of this container and all the children.

        Does nothing as this container is used for dumping output.
        """
        pass
