"""Contains the `ScrollingContainer` class, which renders children on the fly."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.containers import Container, Window, to_container
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension, to_dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from typing import Callable, List, Optional, Sequence, Union

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension

    from euporie.cell import Cell

log = logging.getLogger(__name__)

__all__ = ["ChildMeta", "ScrollingContainer", "ScrollBar"]


class ChildMeta:
    """A class which holds information about a :py:class:`ScrollingContainer` child."""

    def __init__(self, parent: "ScrollingContainer", child: "Cell") -> "None":
        """Initiates the :py:class:`ChildMeta` object.

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
        self._selected_child_meta: "ChildMeta"
        self.selected_child_position: "int" = 0

        self.child_metas: "dict[int, ChildMeta]" = {}  # Holds child container wrappers
        self.visible_indicies: "set[int]" = set([self._selected_index])
        self.index_positions: "dict[int, int]" = {}

        self.last_write_position = WritePosition(0, 0, 0, 0)

        self.height = to_dimension(height).preferred
        self.width = to_dimension(width).preferred
        self.style = style

    def reset(self) -> "None":
        """Reset the state of this container and all the children."""
        for meta in self.child_metas.values():
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
            for child_hash in set(self.child_metas) - set(map(hash, self._children)):
                del self.child_metas[child_hash]
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
            self._selected_child_meta.refresh = True
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

    def get_child_meta(self, index: "Optional[int]" = None) -> "ChildMeta":
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
        if child_hash not in self.child_metas:
            child_meta = ChildMeta(self, child)
            self.child_metas[child_hash] = child_meta
        else:
            child_meta = self.child_metas[child_hash]
        return child_meta

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
                bottom_child = self.get_child_meta(bottom_index)
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
        is cached to a separate screen object stored in a :py::class:`ChildMeta`. The
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

        self._selected_child_meta = self.get_child_meta(selected_index)
        self._selected_child_meta.refresh = True

        # Refresh all children if the width has changed
        if (
            self.last_write_position is not None
            and self.last_write_position.width != write_position.width
        ):
            for child_meta in self.child_metas.values():
                child_meta.refresh = True

        # Blit selected child and those below it that are on screen
        line = self.selected_child_position
        for i in range(selected_index, len(self.children)):
            child_meta = self.get_child_meta(i)
            child_meta.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
            )
            if 0 < line + child_meta.height and line < available_height:
                self.index_positions[i] = line
                child_meta.blit(
                    screen=screen,
                    mouse_handlers=mouse_handlers,
                    left=xpos,
                    top=ypos + line,
                    cols=slice(0, available_width),
                    rows=slice(
                        max(0, 0 - line),
                        min(child_meta.height, available_height - line),
                    ),
                )
                visible_indicies.add(i)
            line += child_meta.height
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
            child_meta = self.get_child_meta(i)
            child_meta.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
            )
            line -= child_meta.height
            if 0 < line + child_meta.height and line < available_height:
                self.index_positions[i] = line
                child_meta.blit(
                    screen=screen,
                    mouse_handlers=mouse_handlers,
                    left=xpos,
                    top=ypos + line,
                    cols=slice(0, available_width),
                    rows=slice(
                        max(0, 0 - line),
                        min(child_meta.height, available_height - line),
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

    def get_children(self) -> List["Container"]:
        """Return the list of currently visible children to include in the layout."""
        return [
            self.get_child_meta(i).container
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
        child_meta = self.get_child_meta(index)
        child_meta.render(
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
                        + self.get_child_meta(last_index).height,
                    ),
                    0,
                )

        if new_top < 0:
            self.selected_child_position = 0
        elif new_top > self.last_write_position.height - child_meta.height:
            self.selected_child_position = max(
                0,
                self.last_write_position.height - child_meta.height,
            )
        else:
            self.selected_child_position = new_top

    @property
    def known_sizes(self) -> "dict[int, int]":
        """A dictionary mapping child indicies to height values."""
        sizes = {}
        for i, child in enumerate(self.children):
            child_hash = hash(child)
            if child_meta := self.child_metas.get(child_hash):
                sizes[i] = child_meta.height
        return sizes


class ScrollBar(UIControl):
    """A vertical scrollbar for :py:class:`ScrollingContainer`."""

    arrows = "▲▼"
    eighths = "█▇▆▅▄▃▂▁"

    def __init__(self, target: "ScrollingContainer") -> "None":
        """Create a varical scrollbar for a :py:class:`ScrollingContainer` instance."""
        self.target = target

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

    def get_line(self, line: "int") -> "StyleAndTextTuples":
        """Get style-and-text tuples for a particular line number.

        Args:
            line: The desired line dumber

        Returns:
            A list of style-and-text tuples

        """
        if line == 0:
            return [("class:scrollbar.arrow", self.arrows[0])]
        elif line == self.height - 1:
            return [("class:scrollbar.arrow", self.arrows[1])]
        elif int(self.top) == line:
            return [
                ("class:scrollbar.button", self.eighths[int((self.top - line) * 8)])
            ]
        elif self.top <= line and line < int(self.top + self.size):
            return [("class:scrollbar.button", self.eighths[0])]
        elif (int(self.top + self.size)) == line:
            return [
                (
                    "class:scrollbar.button reverse",
                    self.eighths[int((self.top + self.size - line) * 8)],
                )
            ]
        else:
            return [("class:scrollbar.background", " ")]

    def create_content(self, width: "int", height: "int") -> "UIContent":
        """Generate the content for this scrollbar.

        Args:
            width: The height available
            height: The width available

        Returns:
            A :class:`UIContent` instance.

        """
        self.height = height
        n_children = len(self.target.children)
        sizes = self.target.known_sizes
        avg_size = sum(sizes.values()) / len(sizes)
        for i in range(n_children):
            if i not in sizes:
                sizes[i] = int(avg_size)
        self.total_height = max(sum(sizes.values()) - height, 1)
        offset = (
            sum(list(sizes.values())[: self.target._selected_index])
            - self.target.selected_child_position
        )
        frac = min(max(offset / self.total_height, 0), 1)

        self.size = max(height / self.total_height * height, 1)
        self.size = int(self.size * 8) / 8
        self.top = (height - 2 - self.size) * frac
        self.top = 1 + int(self.top * 8) / 8

        return UIContent(
            self.get_line,
            line_count=height,
            show_cursor=False,
        )

    async def mouse_handler(self, mouse_event: MouseEvent) -> "None":
        """Handle mouse events."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            if mouse_event.position.y == 0:
                self.target.scroll(1)
            elif mouse_event.position.y == self.height - 1:
                self.target.scroll(-1)
            else:
                self.target.selected_index = int(
                    len(self.target.children)
                    * ((mouse_event.position.y - 1) / (self.height - 3))
                )
                self.target.selected_child_position = (
                    self.height - self.target.known_sizes[self.target.selected_index]
                ) // 2

        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.target.scroll(n=-1)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.target.scroll(n=1)
