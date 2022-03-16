"""Contains the `ScrollingContainer` class, which renders children on the fly."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.containers import (
    Container,
    ScrollOffsets,
    Window,
    WindowRenderInfo,
    to_container,
)
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension, to_dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from euporie.margins import ScrollbarMargin

if TYPE_CHECKING:
    from typing import Callable, List, Optional, Sequence, Union

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension

    from euporie.cell import Cell

log = logging.getLogger(__name__)

__all__ = ["ChildRenderInfo", "ScrollingContainer", "ScrollbarControl"]


class ChildRenderInfo:
    """A class which holds information about a :py:class:`ScrollingContainer` child."""

    def __init__(self, parent: "ScrollingContainer", child: "Cell") -> "None":
        """Initiates the :py:class:`ChildRenderInfo` object.

        Args:
            parent: The parent scrolling container this relates to
            child: The child container (notebook cell) this information concerns

        """
        self.parent = parent
        self.child = child
        child.meta = self
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
            self.refresh = False

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
            cols: The number of columns top copy
            rows: The number of rows to copy

        """
        # Copy write positions
        for win, wp in self.screen.visible_windows_to_write_positions.items():
            screen.visible_windows_to_write_positions[win] = WritePosition(
                xpos=wp.xpos + left,
                ypos=wp.ypos + top,
                width=wp.width,
                height=max(
                    0,
                    min(
                        wp.height + wp.ypos - max(wp.ypos, rows.start),
                        min(wp.height + wp.ypos, rows.stop) - wp.ypos,
                    ),
                ),
            )

        mouse_handler_wrappers = {}

        def _wrap_mouse_handler(
            handler: "Callable",
        ) -> "Callable[[MouseEvent], object]":
            if handler not in mouse_handler_wrappers:

                def wrapped_mouse_handler(mouse_event: "MouseEvent") -> "None":
                    if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                        self.parent.scroll(-1)
                    elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                        self.parent.scroll(1)
                    elif handler:
                        new_event = MouseEvent(
                            position=Point(
                                x=mouse_event.position.x - left,
                                y=mouse_event.position.y - top,
                            ),
                            event_type=mouse_event.event_type,
                            button=mouse_event.button,
                            modifiers=mouse_event.modifiers,
                        )
                        handler(new_event)

                mouse_handler_wrappers[handler] = wrapped_mouse_handler
            return mouse_handler_wrappers[handler]

        # Copy screen contents
        for y in range(max(0, rows.start), min(rows.stop, self.height)):
            for x in range(max(0, cols.start), min(cols.stop, self.width)):
                # Data
                screen.data_buffer[top + y][left + x] = self.screen.data_buffer[y][x]
                # Escape sequences
                screen.zero_width_escapes[top + y][
                    left + x
                ] = self.screen.zero_width_escapes[y][x]
                # Mouse handlers
                mouse_handlers.mouse_handlers[top + y][left + x] = _wrap_mouse_handler(
                    self.mouse_handlers.mouse_handlers[y][x]
                )
        # Copy cursors
        if self.screen.show_cursor:
            for window, point in self.screen.cursor_positions.items():
                if get_app().layout.current_control == window.content:
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
        children_func: "Callable",
        height: "AnyDimension" = None,
        width: "AnyDimension" = None,
        style: "Union[str, Callable[[], str]]" = "",
    ):
        """Initiates the `ScrollingContainer`."""
        self.children_func = children_func
        self._children: "list[Cell]" = []
        self.refresh_children = True

        self._selected_index = 0  # The index of the currently selected
        self._selected_child_render_info: "ChildRenderInfo"
        self.selected_child_position: "int" = 0

        self.child_render_infos: "dict[int, ChildRenderInfo]" = (
            {}
        )  # Holds child container wrappers
        self.visible_indicies: "set[int]" = set([self._selected_index])
        self.index_positions: "dict[int, int]" = {}

        self.last_write_position = WritePosition(0, 0, 0, 0)

        self.height = to_dimension(height).preferred
        self.width = to_dimension(width).preferred
        self.style = style

    def reset(self) -> "None":
        """Reset the state of this container and all the children."""
        # self.render_info = None
        for meta in self.child_render_infos.values():
            meta.container.reset()
            meta.refresh = True

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Do not provide a preferred width - grow to fill the available space."""
        if self.width is not None:
            return Dimension(min=1, preferred=self.width, weight=1)
        return Dimension()

    def preferred_height(self, width: int, max_available_height: int) -> "Dimension":
        """Return the preferred height only if one is provided."""
        if self.height is not None:
            return Dimension(min=1, preferred=self.height)
        return Dimension()

    @property
    def children(
        self,
    ) -> "Sequence[Cell]":  # Sequence[Union[Container, MagicContainer]]":
        """Return the current children of this container instance."""
        if self.refresh_children:
            self._children = self.children_func()
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

    def _set_selected_index(
        self, new_index: "int", force: "bool" = False, scroll: "bool" = True
    ) -> None:
        # Only update the selected child if it was not selected before
        if force or new_index != self._selected_index:
            self.refresh_children = True
            # Ensure selected index is a valid child
            new_index = min(max(new_index, 0), len(self.children) - 1)
            # Request a refresh of the previously selected child
            self._selected_child_render_info.refresh = True
            # Scroll into view
            if scroll:
                self.scroll_to(new_index)
            # Get the new child and focus it
            child = self.children[new_index]
            app = get_app()
            if not app.layout.has_focus(child):
                app.layout.focus(child)
            # Track which child was selected
            self._selected_index = new_index

    @property
    def selected_index(self) -> "int":
        """Returns in index of the currently selected child."""
        app = get_app()
        # Detect if focused child element has changed
        if app.layout.has_focus(self):
            # Find index of selected child
            index = self._selected_index
            for i, child in enumerate(self.children):
                if app.layout.has_focus(child):
                    self._selected_child = child
                    index = i
                    break
            # This will change the position when a new child is selected
            self.selected_index = index
        return self._selected_index

    @selected_index.setter
    def selected_index(self, new_index: "int") -> "None":
        """Sets the currently selected child index.

        Args:
            new_index: The index of the child to select.

        """
        self._set_selected_index(new_index)

    def get_child_render_info(self, index: "Optional[int]" = None) -> "ChildRenderInfo":
        """Return a rendered instance of the child at the given index.

        If no index is given, the currently selected child is returned.

        Args:
            index: The index of the child to return.

        Returns:
            A rendered instance of the child.

        """
        if index is None:
            index = self.selected_index
        child = self.children[index]
        child_hash = hash(child)
        if child_hash not in self.child_render_infos:
            child_render_info = ChildRenderInfo(self, child)
            self.child_render_infos[child_hash] = child_render_info
        else:
            child_render_info = self.child_render_infos[child_hash]
        return child_render_info

    def scroll(self, n: "int") -> "None":
        """Scrolls up or down a number of rows.

        Args:
            n: The number of rows to scroll, negative for up, positive for down

        """
        self.refresh_children = True
        if n > 0:
            if min(self.visible_indicies) == 0 and self.index_positions[0] + n > 0:
                return
        elif n < 0:
            bottom_index = len(self.children) - 1
            if bottom_index in self.visible_indicies:
                bottom_child = self.get_child_render_info(bottom_index)
                if (
                    self.index_positions[bottom_index] + bottom_child.height + n
                    < self.last_write_position.height
                ):
                    return

        self.selected_child_position += n

    def mouse_scroll_handler(self, mouse_event: "MouseEvent") -> "None":
        """A mouse handler to scroll the pane."""
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.scroll(-1)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.scroll(1)

    # @abstractmethod
    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: str,
        erase_bg: bool,
        z_index: Optional[int],
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

        # Record children which are currently visible
        visible_indicies = set()

        # Force the selected child to refresh
        selected_index = self.selected_index

        self._selected_child_render_info = self.get_child_render_info(selected_index)
        self._selected_child_render_info.refresh = True

        # Refresh all children if the width has changed
        if (
            self.last_write_position is not None
            and self.last_write_position.width != write_position.width
        ):
            for child_render_info in self.child_render_infos.values():
                child_render_info.refresh = True

        # Blit selected child and those below it that are on screen
        line = self.selected_child_position
        for i in range(selected_index, len(self.children)):
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
        for i in range(selected_index - 1, -1, -1):
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

        # Ensure the selected child is always in the layout
        visible_indicies.add(self._selected_index)

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

        vertical_scroll = (
            sum(list(sizes.values())[: self._selected_index])
            - self.selected_child_position
        )

        # Mock up a WindowRenderInfo so we can draw a scrollbar margin
        self.render_info = WindowRenderInfo(
            window=cast("Window", self),
            ui_content=UIContent(line_count=content_height),
            horizontal_scroll=0,
            vertical_scroll=vertical_scroll,
            window_width=available_width,
            window_height=available_height,
            configured_scroll_offsets=ScrollOffsets(),
            visible_line_to_row_col={i: (i, 0) for i in range(available_height)},
            rowcol_to_yx={},
            x_offset=0,
            y_offset=0,
            wrap_lines=False,
        )

    def get_children(self) -> List["Container"]:
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
            index = self.selected_index
        return self.children[index]

    def scroll_to(self, index: "int") -> "None":
        """Scroll a child into view.

        Args:
            index: The child index to scroll into view

        """
        child_render_info = self.get_child_render_info(index)
        child_render_info.render(
            self.last_write_position.width, self.last_write_position.height
        )

        if index in self.visible_indicies:
            new_top = self.index_positions[index]
        else:
            if index < self._selected_index:
                new_top = 0
            elif index == self._selected_index:
                new_top = self.selected_child_position
            elif index > self._selected_index:
                last_index = max(self.index_positions)
                new_top = max(
                    min(
                        self.last_write_position.height,
                        self.index_positions[last_index]
                        + self.get_child_render_info(last_index).height,
                    ),
                    0,
                )

        if new_top < 0:
            self.selected_child_position = 0
        elif new_top > self.last_write_position.height - child_render_info.height:
            self.selected_child_position = max(
                0,
                self.last_write_position.height - child_render_info.height,
            )
        else:
            self.selected_child_position = new_top

    @property
    def known_sizes(self) -> "dict[int, int]":
        """A dictionary mapping child indicies to height values."""
        sizes = {}
        for i, child in enumerate(self.children):
            child_hash = hash(child)
            if child_render_info := self.child_render_infos.get(child_hash):
                sizes[i] = child_render_info.height
        return sizes

    def _scroll_up(self) -> "None":
        """Scroll up one line: for compatibility with :py:class:`Window`."""
        self.scroll(1)

    def _scroll_down(self) -> "None":
        """Scroll down one line: for compatibility with :py:class:`Window`."""
        self.scroll(-1)


class ScrollbarControl(UIControl):
    """A control which displays a :py:class:`ScrollbarMargin` for another container."""

    def __init__(self, target: "ScrollingContainer") -> "None":
        """Create a varical scrollbar for a :py:class:`ScrollingContainer` instance."""
        self.target = target
        self.margin = ScrollbarMargin()
        self.lines: "list[StyleAndTextTuples]" = []

    def preferred_width(self, max_available_width: "int") -> "int":
        """Return the preferred width of this scrollbar."""
        return 1

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[Callable[[int, int], AnyFormattedText]]",
    ) -> "Optional[int]":
        """Get the preferred height of the scrollbar: all of the height available."""
        return max_available_height

    def create_content(self, width: "int", height: "int") -> "UIContent":
        """Generates the scrollbar's content."""
        self.lines = list(
            split_lines(
                self.margin.create_margin(
                    window_render_info=self.target.render_info,
                    width=width,
                    height=height,
                )
            )
        )
        return UIContent(
            self.lines.__getitem__,
            line_count=len(self.lines),
            show_cursor=False,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> "NotImplementedOrNone":
        """Handle mouse events."""
        if self.lines:
            fragments = self.lines[max(0, min(len(self.lines), mouse_event.position.y))]
            # Find position in the fragment list.
            xpos = mouse_event.position.x
            # Find mouse handler for this character.
            count = 0
            for item in fragments:
                count += len(item[1])
                if count > xpos:
                    if len(item) >= 3:
                        # Call the handler and return its result
                        handler = item[2]  # type: ignore
                        return handler(mouse_event)
                    else:
                        break
        # Otherwise, don't handle here.
        return NotImplemented
