"""Defines a container which displays all children at full height vertially stacked."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.layout.containers import (
    Container,
    Window,
    to_container,
)
from prompt_toolkit.layout.dimension import Dimension, to_dimension

from euporie.core.layout.screen import BoundedWritePosition

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
    )
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition
    from prompt_toolkit.mouse_events import MouseEvent

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class PrintingContainer(Container):
    """A container which displays all it's children in a vertical list."""

    def __init__(
        self,
        children: Callable | Sequence[AnyContainer],
        width: AnyDimension = None,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None:
        """Initiate the container."""
        self.width = width
        self._children = children
        self._render_count = -1
        self._cached_children: Sequence[AnyContainer] | None = None
        self.key_bindings = key_bindings

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Return the container's key bindings."""
        return self.key_bindings

    @property
    def children(self) -> Sequence[AnyContainer]:
        """Return the container's children."""
        # Only load the children from a callable once per render cycle
        if callable(self._children):
            if (
                self._cached_children is None
                or self._render_count != get_app().render_counter
            ):
                self._cached_children = self._children()
                self._render_count = get_app().render_counter
            children = self._cached_children
        else:
            children = self._children
        return children or [Window()]

    def get_children(self) -> list[Container]:
        """Return a list of all child containers."""
        return list(map(to_container, self.children))

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
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
                BoundedWritePosition(xpos, ypos, write_position.width, height),
                parent_style,
                erase_bg,
                z_index,
            )
            ypos += height

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the preferred height, equal to the sum of the child heights."""
        return Dimension(
            min=1,
            preferred=sum(
                [
                    c.preferred_height(width, max_available_height).preferred
                    for c in self.get_children()
                ]
            ),
        )

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Calculate and returns the desired width for this container."""
        if self.width is not None:
            dim = to_dimension(self.width).preferred
            return Dimension(max=dim, preferred=dim)
        else:
            return Dimension(max_available_width)

    def reset(self) -> None:
        """Reset the state of this container and all the children.

        Does nothing as this container is used for dumping output.
        """
