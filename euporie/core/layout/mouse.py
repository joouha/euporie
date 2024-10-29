"""Defines a container which displays all children at full height vertially stacked."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    Container,
    to_container,
)
from prompt_toolkit.mouse_events import MouseEventType

from euporie.core.app.current import get_app

if TYPE_CHECKING:
    from typing import Callable

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition
    from prompt_toolkit.mouse_events import MouseEvent

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class DisableMouseOnScroll(Container):
    """A container which disables mouse support on unhandled scroll up events.

    This enables the terminal scroll-back buffer to be scrolled if there is nothing in
    the application which is scrollable.
    """

    def __init__(
        self,
        content: AnyContainer,
    ) -> None:
        """Initiate the container."""
        self.content = to_container(content)

        # Wrap app mouse support filter
        app = get_app()
        self.mouse_support = app.mouse_support()
        filter_ = Condition(lambda: self.mouse_support)
        app.mouse_support &= filter_
        app.renderer.mouse_support &= filter_

    def reset(self) -> None:
        """Reset the state of this container."""
        self.content.reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the desired width for this container."""
        return self.content.preferred_width(max_available_width)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the desired height for this container."""
        return self.content.preferred_height(width, max_available_height)

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

        Wrap mouse handelrs, hooking unhandled scroll up events so the terminal can be
        scrolled if the scroll event is not handled.

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
        self.mouse_support = True
        self.content.write_to_screen(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
            z_index,
        )

        @lru_cache
        def _wrap_mouse_handler(handler: Callable) -> MouseHandler:
            def wrapped_mouse_handler(mouse_event: MouseEvent) -> NotImplementedOrNone:
                response = handler(mouse_event)
                # Disable mouse support if scrolling is not implemented
                if (
                    mouse_event.event_type == MouseEventType.SCROLL_UP
                    and response is NotImplemented
                ):
                    self.mouse_support = False
                    return None

                    # async def _reactivate_mouse_support() -> None:
                    #     import asyncio
                    #     await asyncio.sleep(1)
                    #     get_app().need_mouse_support = True
                    #     get_app().invalidate()
                    # get_app().create_background_task(_reactivate_mouse_support())

                return response

            return wrapped_mouse_handler

        # Wrap mouse handlers
        mhs = mouse_handlers.mouse_handlers
        for y in range(
            write_position.ypos, write_position.ypos + write_position.height
        ):
            row = mhs[y]
            for x in range(
                write_position.xpos, write_position.xpos + write_position.width
            ):
                row[x] = _wrap_mouse_handler(row[x])

    def get_children(self) -> list[Container]:
        """Return a list of all child containers."""
        return [self.content]
