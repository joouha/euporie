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
    from collections.abc import Callable

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition
    from prompt_toolkit.mouse_events import MouseEvent

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class MouseHandlerWrapper(Container):
    """A container which wraps mouse events to add a mouse handler."""

    def __init__(self, content: AnyContainer, handler: MouseHandler) -> None:
        """Wrap a container and invoke `handler` when a mouse click occurs.

        Args:
            content: The inner container to display.
            handler: A callback function which will be invoked with the
                MouseEvent whenever a click occurs.
        """
        self.content = to_container(content)
        self.handler = handler
        self.last_write_position: WritePosition | None = None

    def reset(self) -> None:
        """Reset the state of the container."""
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
        """Render the container and wrap mouse handlers to invoke the click callback."""
        self.content.write_to_screen(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
            z_index,
        )
        self.last_write_position = write_position

        @lru_cache
        def _wrap_mouse_handler(handler: Callable) -> MouseHandler:
            def wrapped_mouse_handler(mouse_event: MouseEvent) -> NotImplementedOrNone:
                result = handler(mouse_event)
                try:
                    handler_result = self.handler(mouse_event)
                except Exception:
                    log.exception("Error in MouseHandlerWarapper click handler")
                else:
                    if result is NotImplemented:
                        result = handler_result
                return result

            return wrapped_mouse_handler

        def _wrap_mhs() -> None:
            """Wrap mouse handlers corresponding to write position."""
            mhs = mouse_handlers.mouse_handlers
            for y in range(
                write_position.ypos, write_position.ypos + write_position.height
            ):
                row = mhs[y]
                for x in range(
                    write_position.xpos, write_position.xpos + write_position.width
                ):
                    row[x] = _wrap_mouse_handler(row[x])

        if z_index is None or z_index == 0:
            _wrap_mhs()
        else:
            # Postpone wrapping mouse handlers in floats, otherwise wrap now
            screen.draw_with_z_index(z_index=(z_index or 0) + 1, draw_func=_wrap_mhs)

    def get_children(self) -> list[Container]:
        """Return the list of contained children."""
        return [self.content]


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

        Wrap mouse handlers, hooking unhandled scroll up events so the terminal can be
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
