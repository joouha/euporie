"""Defines a container which saves rendered output and re-displays it."""

from __future__ import annotations

import logging
from functools import cache
from typing import TYPE_CHECKING

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.containers import (
    Container,
    Window,
    WindowRenderInfo,
    to_container,
)
from prompt_toolkit.layout.layout import walk
from prompt_toolkit.layout.mouse_handlers import MouseHandlers

from euporie.core.app.current import get_app
from euporie.core.data_structures import DiInt
from euporie.core.layout.screen import BoundedWritePosition, Screen
from euporie.core.mouse_events import MouseEvent

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.mouse_handlers import MouseEvent as PtkMouseEvent
    from prompt_toolkit.layout.screen import Screen as PtkScreen
    from prompt_toolkit.layout.screen import WritePosition
    from prompt_toolkit.utils import Event

    MouseHandler = Callable[[PtkMouseEvent], object]

log = logging.getLogger(__name__)


class CachedContainer(Container):
    """A container which renders its content once and caches the output."""

    def __init__(
        self,
        content: AnyContainer,
        mouse_handler_wrapper: Callable[[MouseHandler, CachedContainer], MouseHandler]
        | None = None,
    ) -> None:
        """Initiate the container."""
        self.content = content
        self.container = to_container(content)
        self.mouse_handler_wrapper = mouse_handler_wrapper

        self.screen = Screen()
        self.mouse_handlers = MouseHandlers()

        self._invalid = True
        self._invalidate_events: set[Event[object]] = set()
        self._layout_hash = 0
        self.render_counter = 0
        self.height = 0
        self.width = 0
        self._rendered_lines: set[int] = set()
        self._rowcols_to_yx: dict[Window, dict[tuple[int, int], tuple[int, int]]] = {}

        self._width_cache: FastDictCache[tuple[int, int], Dimension] = FastDictCache(
            get_value=lambda _render_count,
            max_available_width: self.container.preferred_width(max_available_width)
        )
        self._height_cache: FastDictCache[tuple[int, int, int], Dimension] = (
            FastDictCache(
                get_value=lambda _render_count,
                width,
                max_available_height: self.container.preferred_height(
                    width, max_available_height
                )
            )
        )

    @property
    def layout_hash(self) -> int:
        """Return a hash of the child's current layout."""
        return sum(hash(container) for container in walk(self.container))

    def invalidate(self) -> None:
        """Flag the child's rendering as out-of-date."""
        self._invalid = True

    def _invalidate_handler(self, sender: object) -> None:
        self.invalidate()

    def reset(self) -> None:
        """Reset the state of this container."""
        self.container.reset()
        self.invalidate()

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the desired width for this container."""
        return self._width_cache[self.render_counter, max_available_width]

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the desired height for this container."""
        return self._height_cache[self.render_counter, width, max_available_height]

    def render(
        self,
        available_width: int,
        available_height: int,
        style: str = "",
        start: int | None = None,
        end: int | None = None,
    ) -> None:
        """Render the child container at a given size.

        Args:
            available_width: The height available for rendering
            available_height: The width available for rendering
            style: The parent style to apply when rendering
            bbox: The bounding box for the content to render
            start: Rows between top of output and top of scrollable pane
            end: Rows between top of output and bottom of scrollable pane

        """
        if (
            self._layout_hash != (new_layout_hash := self.layout_hash)
            or self._invalid
            or self.width != available_width
        ):
            self._layout_hash = new_layout_hash
            self._rowcols_to_yx.clear()
            self._rendered_lines.clear()
            self.mouse_handlers.mouse_handlers.clear()
            self.screen = Screen()
            self.render_counter += 1

            # Recalculate child height if this child has been invalidated
            height = self.height = self.container.preferred_height(
                available_width, available_height
            ).preferred

        else:
            height = self.height

        # Calculate which lines are visible and which need rendering
        if start is not None:
            skip_top = max(0, -start)
        elif end is not None:
            skip_top = max(0, -end + height)
        else:
            skip_top = 0
        skip_bottom = max(0, height - available_height - skip_top)

        visible_lines = set(range(skip_top, height - skip_bottom))
        required_lines = visible_lines - self._rendered_lines

        # Refresh if needed
        if required_lines:
            screen = self.screen
            # TODO - allow horizontal scrolling too
            # self.width = self.container.preferred_width(available_width).width
            self.width = available_width

            self._invalid = False

            self.container.write_to_screen(
                screen,
                self.mouse_handlers,
                BoundedWritePosition(
                    xpos=0,
                    ypos=0,
                    width=self.width,
                    height=height,
                    # Only render lines not already on the current screen
                    bbox=DiInt(
                        top=min(required_lines),
                        right=0,
                        bottom=height - max(required_lines) - 1,
                        left=0,
                    ),
                ),
                style,
                erase_bg=True,
                z_index=0,
            )
            screen.draw_all_floats()

            events = set()
            rowcols_to_yx = self._rowcols_to_yx

            for container in walk(self.container):
                if isinstance(container, Window):
                    # Collect invalidation events
                    for event in container.content.get_invalidate_events():
                        event += self._invalidate_handler
                        events.add(event)

                    if (render_info := container.render_info) is not None:
                        # Update row/col to x/y mapping based on the lines we just rendereed
                        if container not in rowcols_to_yx:
                            rowcols_to_yx[container] = {}

                        rowcols_to_yx[container].update(render_info._rowcol_to_yx)
                        render_info._rowcol_to_yx = rowcols_to_yx[container]

            # Update the record of lines that've been rendered to the temporary screen
            self._rendered_lines |= required_lines

            # Remove handler from old invalidation events
            for event in events - set(self._invalidate_events):
                event -= self._invalidate_handler
            # Update the list of handlers
            self._invalidate_events = events

    def write_to_screen(
        self,
        screen: PtkScreen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Render the container to a `Screen` instance.

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
        self.render(
            available_width=write_position.width,
            available_height=write_position.height,
            style=parent_style,
            # start: int | None = None,
            # end: int | None = None,
        )

        left = write_position.xpos
        top = write_position.ypos
        rows = slice(0, write_position.height)
        cols = slice(0, write_position.width)
        self.blit(screen, mouse_handlers, left, top, cols, rows)

    def blit(
        self,
        screen: PtkScreen,
        mouse_handlers: MouseHandlers,
        left: int,
        top: int,
        cols: slice,
        rows: slice,
    ) -> None:
        """Copy the rendered child from the local screen to the main screen.

        All locations are adjusted, allowing the pre-rendered child to be placed at any
        location on the main screen.

        Args:
            screen: The main screen to copy the pre-rendered screen data to
            mouse_handlers: The mouse handler collection to copy the pre-rendered
                handelers to
            left: The left-most column in which to start placing the data
            top: The upper row in which to start placing the data
            cols: The columns to copy
            rows: The rows to copy
                                                                                                                                                                                       .
        """
        # Copy write positions
        new_wps = {}

        for win, wp in self.screen.visible_windows_to_write_positions.items():
            new_wp = BoundedWritePosition(
                xpos=wp.xpos + left,
                ypos=wp.ypos + top,
                width=wp.width,
                height=wp.height,
                bbox=DiInt(
                    top=max(0, rows.start - wp.ypos),
                    right=max(0, wp.width - cols.stop),
                    bottom=max(0, wp.height - (rows.stop - wp.ypos)),
                    left=max(0, wp.width - (cols.stop - wp.xpos)),
                ),
            )
            new_wps[win] = new_wp

            # Modify render info
            info = win.render_info
            if info is not None:
                xpos = new_wp.xpos + info._x_offset
                y_start = new_wp.ypos + info._y_offset
                # Only include visible lines according to the bounding box
                visible_line_to_row_col = {
                    i: (y, xpos)
                    for i, y in enumerate(
                        range(
                            y_start + new_wp.bbox.top,
                            y_start + new_wp.height - new_wp.bbox.bottom,
                        )
                    )
                }
                win.render_info = WindowRenderInfo(
                    window=win,
                    ui_content=info.ui_content,
                    horizontal_scroll=0,
                    vertical_scroll=info.vertical_scroll,
                    window_width=info.window_width,
                    window_height=info.window_height,
                    configured_scroll_offsets=info.configured_scroll_offsets,
                    visible_line_to_row_col=visible_line_to_row_col,
                    # The following is needed to calculate absolute cursor positions
                    rowcol_to_yx={
                        k: (y + top, x + left)
                        for k, (y, x) in info._rowcol_to_yx.items()
                    },
                    x_offset=info._x_offset + left,
                    y_offset=info._y_offset + top,
                    wrap_lines=info.wrap_lines,
                )
                # Set horizontal scroll offset - TODO - fix this upstream
                if (
                    horizontal_scroll := getattr(info, "horizontal_scroll", None)
                ) is not None:
                    setattr(  # noqa B010
                        win.render_info, "horizontal_scroll", horizontal_scroll
                    )

        screen.visible_windows_to_write_positions.update(new_wps)
        screen.height = max(screen.height, self.screen.height)

        @cache
        def _wrap_mouse_handler(handler: Callable) -> MouseHandler:
            def _wrapped(mouse_event: PtkMouseEvent) -> NotImplementedOrNone:
                # Modify mouse events to reflect position of content
                new_event = MouseEvent(
                    position=Point(
                        x=mouse_event.position.x - left,
                        y=mouse_event.position.y - top,
                    ),
                    event_type=mouse_event.event_type,
                    button=mouse_event.button,
                    modifiers=mouse_event.modifiers,
                    cell_position=getattr(mouse_event, "cell_position", None),
                )
                if callable(wrapper := self.mouse_handler_wrapper):
                    return wrapper(handler, self)(new_event)
                return handler(new_event)

            return _wrapped

        # Copy screen contents
        input_db = self.screen.data_buffer
        input_zwes = self.screen.zero_width_escapes
        input_mhs = self.mouse_handlers.mouse_handlers
        output_db = screen.data_buffer
        output_zwes = screen.zero_width_escapes
        output_mhs = mouse_handlers.mouse_handlers

        rows_range = range(max(0, rows.start), rows.stop)
        cols_range = range(max(0, cols.start), cols.stop)

        for y in rows_range:
            input_db_row = input_db[y]
            input_zwes_row = input_zwes[y]
            input_mhs_row = input_mhs[y]
            output_dbs_row = output_db[top + y]
            output_zwes_row = output_zwes[top + y]
            output_mhs_row = output_mhs[top + y]
            for x in cols_range:
                # Data
                output_dbs_row[left + x] = input_db_row[x]
                # Escape sequences
                output_zwes_row[left + x] = input_zwes_row[x]
                # Mouse handlers
                output_mhs_row[left + x] = _wrap_mouse_handler(input_mhs_row[x])

        # Copy cursors
        layout = get_app().layout
        if self.screen.show_cursor:
            for window, point in self.screen.cursor_positions.items():
                if (
                    layout.current_control == window.content
                    and window.render_info is not None
                    and window.render_info.ui_content.show_cursor
                    and not window.always_hide_cursor()
                    and cols.start <= point.x < cols.stop
                    and rows.start <= point.y < rows.stop
                ):
                    screen.cursor_positions[window] = Point(
                        x=left + point.x, y=top + point.y
                    )
                    screen.show_cursor = True

        # Copy menu positions
        screen.menu_positions.update(
            {
                window: Point(x=left + point.x, y=top + point.y)
                for window, point in self.screen.menu_positions.items()
            }
        )

    def get_children(self) -> list[Container]:
        """Return a list of all child containers."""
        return self.container.get_children()
