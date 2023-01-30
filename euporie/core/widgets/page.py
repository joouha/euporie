"""Contains containers which display children at full height vertially stacked."""

from __future__ import annotations

import asyncio
import contextvars
import logging
import weakref
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import is_searching
from prompt_toolkit.layout.containers import (
    Container,
    ScrollOffsets,
    Window,
    WindowRenderInfo,
    to_container,
)
from prompt_toolkit.layout.controls import UIContent
from prompt_toolkit.layout.dimension import Dimension, to_dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType, MouseModifier

from euporie.core.data_structures import DiInt

if TYPE_CHECKING:
    from typing import Callable, Optional, Sequence, Union

    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class BoundedWritePosition(WritePosition):
    """A write position which also hold bounding box information."""

    def __init__(
        self,
        xpos: "int",
        ypos: "int",
        width: "int",
        height: "int",
        bbox: "DiInt",
    ) -> "None":
        """Create a new instance of the write position."""
        super().__init__(xpos, ypos, width, height)
        self.bbox = bbox

    def __repr__(self) -> "str":
        """Return a string representation of the write position."""
        return (
            f"{self.__class__.__name__}("
            f"x={self.xpos}, y={self.ypos=}, "
            f"w={self.width}, h={self.height}, "
            f"bbox={self.bbox})"
        )


class ChildRenderInfo:
    """A class which holds information about a :py:class:`ScrollingContainer` child."""

    def __init__(self, parent: "ScrollingContainer", child: "AnyContainer") -> "None":
        """Initiates the :py:class:`ChildRenderInfo` object.

        Args:
            parent: The parent scrolling container this relates to
            child: The child container (notebook cell) this information concerns

        """
        self.parent = parent
        self.child = weakref.proxy(child)
        self.container = to_container(child)

        self.screen = Screen(default_char=Char(char=" "))
        self.mouse_handlers = MouseHandlers()

        self.height = 0
        self.width = 0

        self.refresh = True

    def render(
        self,
        available_width: "int",
        available_height: "int",
        style: "str" = "",
    ) -> "None":
        """Renders the child container at a given size.

        Args:
            available_width: The height available for rendering
            available_height: The width available for rendering
            style: The parent style to apply when rendering

        """
        if self.refresh:
            self.refresh = False
            # log.debug("Re-rendering cell %s", self.child.index)
            self.height = self.container.preferred_height(
                available_width, available_height
            ).preferred
            # TODO - allow horizontal scrolling too
            # self.width = self.container.preferred_width(available_width).width
            self.width = available_width

            self.container.write_to_screen(
                self.screen,
                self.mouse_handlers,
                WritePosition(
                    0,
                    0,
                    self.width,
                    self.height,
                ),
                style,
                erase_bg=True,
                z_index=0,
            )
            self.screen.draw_all_floats()

    def blit(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        left: "int",
        top: "int",
        cols: "slice",
        rows: "slice",
    ) -> "None":
        """Copies the rendered child from the local screen to the main screen.

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

        """
        layout = get_app().layout

        # Copy write positions
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
            screen.visible_windows_to_write_positions[win] = new_wp

            # Modify render info
            info = win.render_info
            if info is not None:
                visible_line_to_row_col = {
                    line: (y + info._y_offset, new_wp.xpos + info._x_offset)
                    for line, y in enumerate(
                        range(new_wp.ypos, new_wp.ypos + new_wp.height)
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
                    # visible_line_to_row_col=info.visible_line_to_row_col,
                    visible_line_to_row_col=visible_line_to_row_col,
                    rowcol_to_yx={
                        (row, col): (y + top, x + left)
                        for (row, col), (y, x) in info._rowcol_to_yx.items()
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

        mouse_handler_wrappers: "dict[MouseHandler, MouseHandler]" = {}

        def _wrap_mouse_handler(
            handler: "Callable",
        ) -> "MouseHandler":
            if mouse_handler := mouse_handler_wrappers.get(handler):
                return mouse_handler
            else:

                def wrapped_mouse_handler(
                    mouse_event: "MouseEvent",
                ) -> "NotImplementedOrNone":
                    response: "NotImplementedOrNone" = NotImplemented
                    new_event = MouseEvent(
                        position=Point(
                            x=mouse_event.position.x - left,
                            y=mouse_event.position.y - top,
                        ),
                        event_type=mouse_event.event_type,
                        button=mouse_event.button,
                        modifiers=mouse_event.modifiers,
                    )

                    if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                        response = self.parent.scroll(-1)
                    elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                        response = self.parent.scroll(1)

                    else:
                        response = handler(new_event)

                    # Refresh the child if there was a response
                    if response is None:
                        self.refresh = True
                        return response

                    # This would work if windows returned NotImplemented when scrolled
                    # to the start or end
                    # if response is NotImplemented:
                    #     if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                    #         response = self.parent.scroll(-1)
                    #     elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                    #         response = self.parent.scroll(1)

                    # Select the clicked child if clicked
                    if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                        index = self.parent._children.index(self.child)
                        if mouse_event.modifiers & {
                            MouseModifier.SHIFT,
                            MouseModifier.CONTROL,
                        }:
                            self.parent.select(index, extend=True)
                        else:
                            self.parent.select(index, extend=False)
                        response = None
                        self.refresh = True

                        # Attempt to focus the container
                        layout.focus(self.child)

                    return response

                mouse_handler_wrappers[handler] = wrapped_mouse_handler
                return wrapped_mouse_handler

        # Copy screen contents
        input_db = self.screen.data_buffer
        input_zwes = self.screen.zero_width_escapes
        input_mhs = self.mouse_handlers.mouse_handlers
        output_dbs = screen.data_buffer
        output_zwes = screen.zero_width_escapes
        output_mhs = mouse_handlers.mouse_handlers
        for y in range(max(0, rows.start), min(rows.stop, self.height)):
            output_dbs_row = output_dbs[top + y]
            output_zwes_row = output_zwes[top + y]
            output_mhs_row = output_mhs[top + y]
            input_db_row = input_db[y]
            input_zwes_row = input_zwes[y]
            input_mhs_row = input_mhs[y]
            for x in range(max(0, cols.start), min(cols.stop, self.width)):
                # Data
                output_dbs_row[left + x] = input_db_row[x]
                # Escape sequences
                output_zwes_row[left + x] = input_zwes_row[x]
                # Mouse handlers
                output_mhs_row[left + x] = _wrap_mouse_handler(input_mhs_row[x])

        # Copy cursors
        if self.screen.show_cursor:
            for window, point in self.screen.cursor_positions.items():
                if layout.current_control == window.content:
                    assert window.render_info is not None
                    if (
                        window.render_info.ui_content.show_cursor
                        and not window.always_hide_cursor()
                    ):
                        if point.x in range(cols.start, cols.stop) and point.y in range(
                            rows.start, rows.stop
                        ):
                            screen.cursor_positions[window] = Point(
                                x=left + point.x, y=top + point.y
                            )
                            screen.show_cursor = True
        # Copy menu positions
        for window, point in self.screen.menu_positions.items():
            screen.menu_positions[window] = Point(x=left + point.x, y=top + point.y)


class ScrollingContainer(Container):
    """A scrollable container which renders only the currently visible children."""

    def __init__(
        self,
        children: "Callable[[], Sequence[AnyContainer]]|Sequence[AnyContainer]",
        height: "AnyDimension" = None,
        width: "AnyDimension" = None,
        style: "Union[str, Callable[[], str]]" = "",
    ) -> "None":
        """Initiates the `ScrollingContainer`."""
        if callable(children):
            _children_func = children
        else:

            def _children_func() -> "Sequence[AnyContainer]":
                """Return the pass sequence of children."""
                assert not callable(children)
                return children

        self.children_func = _children_func
        self._children: "list[AnyContainer]" = []
        self.refresh_children = True
        self.pre_rendered = 0.0

        self._selected_slice = slice(
            0, 1
        )  # The index of the currently selected children
        self._selected_child_render_infos: "list[ChildRenderInfo]"
        self.selected_child_position: "int" = 0

        self.child_render_infos: "dict[int, ChildRenderInfo]" = (
            {}
        )  # Holds child container wrappers
        self.visible_indicies: "set[int]" = {0}
        self.index_positions: "dict[int, Optional[int]]" = {}

        self.last_write_position = WritePosition(0, 0, 0, 0)

        self.width = to_dimension(width).preferred
        self.height = to_dimension(height).preferred
        self.style = style

        self.scroll_to_cursor = False
        self.scrolling = 0

    def pre_render_children(self, width: "int", height: "int") -> "None":
        """Render all unrendered children in a background thread."""
        # Copy the current context so ``get_app()`` works in the thread
        ctx = contextvars.copy_context()

        def render_in_thread() -> "None":
            """Create a new event loop in the thread."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def render_run_in_loop() -> "None":
                """Render all children sequentially."""
                n_children = len(self.children)
                for i in range(n_children):
                    if i < len(self.children):
                        self.get_child_render_info(i).render(width, height)
                        self.pre_rendered = i / n_children
                    get_app().invalidate()
                self.pre_rendered = 1.0
                get_app().invalidate()

            loop.run_until_complete(render_run_in_loop())

        async def trigger_render() -> "None":
            """Use an executor thread from the current event loop."""
            await asyncio.get_event_loop().run_in_executor(
                None, ctx.run, render_in_thread
            )

        get_app().create_background_task(trigger_render())

    def reset(self) -> "None":
        """Reset the state of this container and all the children."""
        meta_data = list(self.child_render_infos.values())
        for meta in meta_data:
            meta.container.reset()
            meta.refresh = True

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Do not provide a preferred width - grow to fill the available space."""
        if self.width is not None:
            return Dimension(min=1, preferred=self.width, weight=1)
        return Dimension(weight=1)

    def preferred_height(self, width: int, max_available_height: int) -> "Dimension":
        """Return the preferred height only if one is provided."""
        if self.height is not None:
            return Dimension(min=1, preferred=self.height, weight=1)
        return Dimension(weight=1)

    @property
    def children(
        self,
    ) -> "Sequence[AnyContainer]":  # Sequence[Union[Container, MagicContainer]]":
        """Return the current children of this container instance."""
        if self.refresh_children:
            self._children = list(self.children_func())
            self.refresh_children = False
            # Clean up metacache
            for child_hash in set(self.child_render_infos) - set(
                map(hash, self._children)
            ):
                del self.child_render_infos[child_hash]
            # Clean up positions
            self.index_positions = {
                i: pos
                for i, pos in self.index_positions.items()
                if i < len(self._children)
            }
        return self._children

    def _set_selected_slice(
        self, new_slice: "slice", force: "bool" = False, scroll: "bool" = True
    ) -> None:
        # Only update the selected child if it was not selected before
        if force or new_slice != self._selected_slice:
            app = get_app()
            self.refresh_children = True
            # Ensure new selected slice is valid
            new_slice = self.validate_slice(new_slice)
            # Scroll into view
            if scroll:
                self.scroll_to(new_slice.start)
            # Request a refresh of the previously selected children
            render_info: "Optional[ChildRenderInfo]"
            for render_info in self._selected_child_render_infos:
                if render_info:
                    render_info.refresh = True
            # If a child currently has focus, request to refresh it
            for child in self.children:
                if (
                    render_info := self.child_render_infos.get(hash(child))
                ) is not None:
                    if app.layout.has_focus(render_info.child):
                        render_info.refresh = True
                        break
            # Get the first selected child and focus it
            child = self.children[new_slice.start]
            if not app.layout.has_focus(child):
                try:
                    app.layout.focus(child)
                except ValueError:
                    pass
            # Track which child was selected
            self._selected_slice = new_slice

    @property
    def selected_slice(self) -> "slice":
        """Returns the currently selected slice."""
        return self._selected_slice

    @selected_slice.setter
    def selected_slice(self, new_slice: "slice") -> "None":
        """Sets the currently selected child index.

        Args:
            new_slice: The slice of the children to select.
        """
        self._set_selected_slice(new_slice)

    def validate_slice(self, slice_: "slice") -> "slice":
        """Ensures a slice describes a valid range of children."""
        start = min(max(slice_.start, 0), len(self.children) - 1)
        stop = slice_.stop
        if stop == -1:
            stop = None
        if stop is not None:
            stop = min(max(slice_.stop, int(start == 0)), len(self.children))
        return slice(start, stop, slice_.step)

    @property
    def selected_indices(self) -> "list[int]":
        """Returns in indices of the currently selected children."""
        return list(range(*self.selected_slice.indices(len(self._children))))

    def get_child_render_info(self, index: "Optional[int]" = None) -> "ChildRenderInfo":
        """Return a rendered instance of the child at the given index.

        If no index is given, the currently selected child is returned.

        Args:
            index: The index of the child to return.

        Returns:
            A rendered instance of the child.

        """
        if index is None:
            index = self._selected_slice.start
        child = self.children[index]
        child_hash = hash(child)
        if child_hash not in self.child_render_infos:
            child_render_info = ChildRenderInfo(self, child)
            self.child_render_infos[child_hash] = child_render_info
        else:
            child_render_info = self.child_render_infos[child_hash]
        return child_render_info

    def select(
        self,
        index: "int",
        extend: "bool" = False,
        position: "Optional[int]" = None,
        scroll: "bool" = True,
    ) -> "None":
        """Selects a child or adds it to the selection.

        Args:
            index: The index of the cell to select
            extend: If true, the selection will be extended to include the cell
            position: An optional cursor position index to apply to the cell input
            scroll: Whether to scroll the page
        """
        # Update the selected slice if we are extending the child selection
        if extend:
            slice_ = self._selected_slice
            stop = -1 if slice_.stop is None else slice_.stop
            step = slice_.step
            if step == -1 and index <= stop:
                stop += 2
                step = 1
            elif step == -1 and index >= stop:
                pass
            elif step in (1, None) and index < stop:
                step = 1
            elif step in (1, None) and index >= stop:
                step = -1
                stop -= 2
            self._set_selected_slice(slice(index, stop, step), scroll=scroll)
        # Otherwise set the cell selection to the given cell index
        else:
            self._set_selected_slice(slice(index, index + 1), scroll=scroll)

    def scroll(self, n: "int") -> "NotImplementedOrNone":
        """Scrolls up or down a number of rows.

        Args:
            n: The number of rows to scroll, negative for up, positive for down

        Returns:
            :py:const:`NotImplemented` is scrolling is not allowed, otherwise
                :py:const:`None`

        """
        # self.refresh_children = True
        if n > 0:
            if min(self.visible_indicies) == 0 and self.index_positions[0] is not None:
                n = min(n, 0 - self.index_positions[0] - self.scrolling)
                if self.index_positions[0] + self.scrolling + n > 0:
                    return NotImplemented
        elif n < 0:
            bottom_index = len(self.children) - 1
            if bottom_index in self.visible_indicies:
                bottom_child = self.get_child_render_info(bottom_index)
                bottom_pos = self.index_positions[bottom_index]
                if bottom_pos is not None:
                    n = max(
                        n,
                        self.last_write_position.height
                        - (bottom_pos + bottom_child.height + self.scrolling),
                    )
                    if (
                        bottom_pos + bottom_child.height + self.scrolling + n
                        < self.last_write_position.height
                    ):
                        return NotImplemented

        # Very basic scrolling acceleration
        self.scrolling += n
        return None

    def mouse_scroll_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        """A mouse handler to scroll the pane."""
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            return self.scroll(-1)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            return self.scroll(1)
        else:
            return NotImplemented
        return None

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> "None":
        """Write the actual content to the screen.

        Children are rendered only if they are visible and have changed, and the output
        is cached to a separate screen object stored in a :py::class:`ChildRenderInfo`. The
        cached rendering of the children which are actually visible are then copied to
        the screen. This results in faster rendering of the scrolling container, and
        makes scrolling more performant.

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
        ypos = write_position.ypos
        xpos = write_position.xpos

        available_width = write_position.width
        available_height = write_position.height

        # Trigger pre-rendering of children
        if not self.pre_rendered:
            self.pre_render_children(available_width, available_height)

        # Update screen height
        screen.height = max(screen.height, ypos + write_position.height)

        # Record children which are currently visible
        visible_indicies = set()

        # Force the selected children to refresh
        selected_indices = self.selected_indices
        self._selected_child_render_infos = []
        for index in selected_indices:
            render_info = self.get_child_render_info(index)
            # Do not bother to re-render children if we are scrolling
            if not self.scrolling:
                render_info.refresh = True
            self._selected_child_render_infos.append(render_info)
            self.index_positions[index] = None

        # Refresh all children if the width has changed
        if self.last_write_position.width != write_position.width:
            for child_render_info in self.child_render_infos.values():
                child_render_info.refresh = True

        # Refresh visible children if searching
        if is_searching():
            for index in self.visible_indicies:
                self.get_child_render_info(index).refresh = True

        # Scroll to make the cursor visible
        if self.scroll_to_cursor:
            selected_child_render_info = self._selected_child_render_infos[0]
            selected_child_render_info.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
            )
            current_window = get_app().layout.current_window
            cursor_position = selected_child_render_info.screen.cursor_positions.get(
                current_window
            )
            if cursor_position:
                cursor_row = self.selected_child_position + cursor_position.y
                if cursor_row < 0:
                    self.selected_child_position -= cursor_row
                elif available_height <= cursor_row:
                    self.selected_child_position -= cursor_row - available_height + 1
            # Set this to false again, allowing us to scroll the cursor out of view
            self.scroll_to_cursor = False

        # Adjust scrolling offset
        if self.scrolling:
            heights = [
                # Ensure unrendered cells have at least some height
                self.get_child_render_info(index).height or 1
                for index in range(len(self._children))
            ]
            heights_above = sum(heights[: self._selected_slice.start])
            new_child_position = self.selected_child_position + self.scrolling
            # Do not allow scrolling if there is no overflow
            if sum(heights) < available_height:
                self.selected_child_position = heights_above
            else:
                # Prevent overscrolling at the top of the document
                overscroll = heights_above - new_child_position
                if overscroll < 0:
                    # Scroll as far as we are able without overscrolling
                    self.scrolling = max(0, self.scrolling + overscroll)
                # Prevent underscrolling at the bottom
                elif overscroll > 0:
                    heights_below = sum(heights[self._selected_slice.start :])
                    underscroll = new_child_position + heights_below - available_height
                    if underscroll < 0:
                        # Scroll as far as we are able without underscrolling
                        self.scrolling = min(0, self.scrolling - underscroll)
            self.selected_child_position += self.scrolling

        # Blit first selected child and those below it that are on screen
        line = self.selected_child_position
        for i in range(self._selected_slice.start, len(self.children)):
            child_render_info = self.get_child_render_info(i)
            child_render_info.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
            )
            if 0 < line + child_render_info.height and line < available_height:
                self.index_positions[i] = line
                child_render_info.blit(
                    screen=screen,
                    mouse_handlers=mouse_handlers,
                    left=xpos,
                    top=ypos + line,
                    cols=slice(0, available_width),
                    rows=slice(
                        max(0, 0 - line),
                        min(child_render_info.height, available_height - line),
                    ),
                )
                visible_indicies.add(i)
            line += child_render_info.height
            if line >= available_height:
                break
        else:
            if line < available_height:
                Window(char=" ").write_to_screen(
                    screen,
                    mouse_handlers,
                    WritePosition(
                        xpos, ypos + line, available_width, available_height - line
                    ),
                    parent_style,
                    erase_bg,
                    z_index,
                )
                for y in range(ypos + line, ypos + available_height):
                    for x in range(xpos, xpos + available_width):
                        mouse_handlers.mouse_handlers[y][x] = self.mouse_scroll_handler
        # Blit children above the selected that are on screen
        line = self.selected_child_position
        for i in range(self._selected_slice.start - 1, -1, -1):
            child_render_info = self.get_child_render_info(i)
            child_render_info.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
            )
            line -= child_render_info.height
            if 0 < line + child_render_info.height and line < available_height:
                self.index_positions[i] = line
                child_render_info.blit(
                    screen=screen,
                    mouse_handlers=mouse_handlers,
                    left=xpos,
                    top=ypos + line,
                    cols=slice(0, available_width),
                    rows=slice(
                        max(0, 0 - line),
                        min(child_render_info.height, available_height - line),
                    ),
                )
                visible_indicies.add(i)
            if line <= 0:
                break
        else:
            if line > 0:
                Window(char=" ").write_to_screen(
                    screen,
                    mouse_handlers,
                    WritePosition(xpos, ypos, available_width, line),
                    parent_style,
                    erase_bg,
                    z_index,
                )
                for y in range(ypos, ypos + line):
                    for x in range(xpos, xpos + available_width):
                        mouse_handlers.mouse_handlers[y][x] = self.mouse_scroll_handler

        # Dont bother drawing floats
        # screen.draw_all_floats()

        # Ensure the focused child is always in the layout
        visible_indicies.add(self._selected_slice.start)

        # Update which children will appear in the layout
        self.visible_indicies = visible_indicies
        # Record where the contain was last drawn so we can determine if cell outputs
        # are partially obscured
        self.last_write_position = write_position

        # Calculate scrollbar info
        sizes = self.known_sizes
        avg_size = sum(sizes.values()) / len(sizes)
        n_children = len(self.children)
        for i in range(n_children):
            if i not in sizes:
                sizes[i] = int(avg_size)
        content_height = max(sum(sizes.values()), 1)

        # Mock up a WindowRenderInfo so we can draw a scrollbar margin
        self.render_info = WindowRenderInfo(
            window=cast("Window", self),
            ui_content=UIContent(line_count=content_height),
            horizontal_scroll=0,
            vertical_scroll=self.vertical_scroll,
            window_width=available_width,
            window_height=available_height,
            configured_scroll_offsets=ScrollOffsets(),
            visible_line_to_row_col={i: (i, 0) for i in range(available_height)},
            rowcol_to_yx={},
            x_offset=xpos,
            y_offset=ypos,
            wrap_lines=False,
        )
        # Signal that we are no longer scrolling
        self.scrolling = 0

    @property
    def vertical_scroll(self) -> "int":
        """The best guess at the absolute vertical scroll position."""
        return (
            sum(list(self.known_sizes.values())[: self._selected_slice.start])
            - self.selected_child_position
        )

    @vertical_scroll.setter
    def vertical_scroll(self, value: "int") -> "None":
        """Set the absolute vertical scroll position."""
        self.selected_child_position = (
            sum(list(self.known_sizes.values())[: self._selected_slice.start]) - value
        )

    def get_children(self) -> "list[Container]":
        """Return the list of currently visible children to include in the layout."""
        return [
            self.get_child_render_info(i).container
            for i in self.visible_indicies
            if i < len(self.children)
        ]

    def get_child(self, index: "Optional[int]" = None) -> "AnyContainer":
        """Return a rendered instance of the child at the given index.

        If no index is given, the currently selected child is returned.

        Args:
            index: The index of the child to return.

        Returns:
            A rendered instance of the child.

        """
        if index is None:
            index = self.selected_slice.start
        return self.children[index]

    def scroll_to(self, index: "int") -> "None":
        """Scroll a child into view.

        Args:
            index: The child index to scroll into view

        """
        child_render_info = self.get_child_render_info(index)

        if index in self.visible_indicies:
            new_top = self.index_positions[index]
        else:
            if index < self._selected_slice.start:
                # new_top = 0
                new_top = max(
                    0, child_render_info.height - self.last_write_position.height
                )
            elif index == self._selected_slice.start:
                new_top = self.selected_child_position
            elif index > self._selected_slice.start:
                last_index = max(
                    k for k, v in self.index_positions.items() if v is not None
                )
                new_top = max(
                    min(
                        self.last_write_position.height,
                        (self.index_positions[last_index] or 0)
                        + self.get_child_render_info(last_index).height,
                    ),
                    0,
                )

        if new_top is None or new_top < 0:
            self.selected_child_position = min(
                0, self.last_write_position.height - child_render_info.height
            )
        elif new_top > self.last_write_position.height - child_render_info.height:
            self.selected_child_position = max(
                0,
                self.last_write_position.height - child_render_info.height,
            )
        else:
            self.selected_child_position = new_top

    @property
    def known_sizes(self) -> "dict[int, int]":
        """A dictionary mapping child indices to height values."""
        sizes = {}
        for i, child in enumerate(self.children):
            child_hash = hash(child)
            if child_render_info := self.child_render_infos.get(child_hash):
                if child_render_info.height:
                    sizes[i] = child_render_info.height
        return sizes

    def _scroll_up(self) -> "None":
        """Scroll up one line: for compatibility with :py:class:`Window`."""
        self.scroll(1)

    def _scroll_down(self) -> "None":
        """Scroll down one line: for compatibility with :py:class:`Window`."""
        self.scroll(-1)


class PrintingContainer(Container):
    """A container which displays all it's children in a vertical list."""

    def __init__(
        self,
        children: "Union[Callable, Sequence[AnyContainer]]",
        width: "AnyDimension" = None,
        key_bindings: "Optional[KeyBindingsBase]" = None,
    ) -> "None":
        """Initiate the container."""
        self.width = width
        self.rendered = False
        self._children = children
        self.key_bindings = key_bindings

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Return the container's key bindings."""
        return self.key_bindings

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
