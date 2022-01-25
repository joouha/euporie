"""Contains the `ScrollingContainer` class, which renders children on the fly."""

from __future__ import annotations

import logging
from collections import namedtuple
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.layout.containers import Container, Window, to_container
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension, to_dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.utils import to_str

if TYPE_CHECKING:
    from typing import Callable, Dict, List, Optional, Sequence, Union

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.layout.containers import AnyContainer, MagicContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandler
    from prompt_toolkit.mouse_events import MouseEvent

log = logging.getLogger(__name__)

__all__ = ["DrawingPosition", "ScrollingContainer", "ScrollBar"]


DrawingPosition = namedtuple(
    "DrawingPosition",
    [
        "index",
        "container",
        "top",
        "height",
        "parent_height",
    ],
)


class ScrollingContainer(Container):
    """A scrollable container which renders only the currently visible children."""

    def __init__(
        self,
        children: "Union[Sequence[AnyContainer], Callable]",
        height: "AnyDimension" = None,
        width: "AnyDimension" = None,
        style: "Union[str, Callable[[], str]]" = "",
        z_index: "Optional[int]" = None,
    ):
        """Initiates the `ScrollingContainer`."""
        self._children = children
        self.height = to_dimension(height).preferred
        self.width = to_dimension(width).preferred
        self.last_write_position: "Optional[WritePosition]" = None
        self.style = style
        self.z_index = z_index
        self._remaining_space_window = Window()
        self.last_selected_index: "int" = 0
        # Position of viewing window relative to selected child
        self.selected_child_position: "int" = 0
        self.to_draw: "Sequence[DrawingPosition]" = []
        self.visible: "dict[int, Union[Container, MagicContainer]]" = {}
        self.size_cache: "dict[int, int]" = {}
        # We need to remember the height of the container
        self.content_width = 0
        self.content_height = 0

    # Container methods

    def reset(self) -> "None":
        """Reset the state of rendered children."""
        app = get_app()
        if app.render_counter > 0:
            for c in self.get_children():
                c.reset()
            self.visible = {}

    def get_children(self) -> "List[Container]":
        """Return a list of the containers of the currently rendered children."""
        if not self.visible:
            self.visible = {0: to_container(self.get_child(0))}
        return list(map(to_container, self.visible.values()))

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Do not provide a preferred width - grow to fill the avaliable space."""
        if self.width is not None:
            return Dimension(min=1, preferred=self.width, weight=1)
        return Dimension()

    def preferred_height(self, width: int, max_available_height: int) -> "Dimension":
        """Return the preferred height only if one is provided."""
        if self.height is not None:
            return Dimension(min=1, preferred=self.height)
        return Dimension()

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
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
        self.last_write_position = write_position

        self.available_width = write_position.width
        self.available_height = write_position.height

        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        self.content_width = self.available_width
        self.content_height = self.available_height

        self.to_draw = self.arrange_children(write_position)

        ypos = write_position.ypos
        xpos = write_position.xpos

        # Draw child panes.
        for drawing in self.to_draw:

            if drawing.top < 0 or drawing.top + drawing.height > self.content_height:
                # Create a virtual screen to draw partially obscured children
                temp_screen = Screen(default_char=Char(char=" ", style=parent_style))
                # Create empty mouse handler array
                temp_mouse_handlers = MouseHandlers()
                # Draw child at (0,0) on temp screen
                temp_write_position = WritePosition(
                    xpos=xpos,
                    ypos=ypos + drawing.top,
                    width=self.content_width,
                    height=drawing.height,
                )

                drawing.container.write_to_screen(
                    temp_screen,
                    temp_mouse_handlers,
                    temp_write_position,
                    style,
                    erase_bg,
                    z_index,
                )
                temp_screen.draw_all_floats()

                # Determine how many rows to copy
                copy_row_start = max(ypos, ypos + drawing.top)
                copy_row_end = max(ypos + drawing.top, ypos + self.content_height)

                # Copy screen contents
                for y in range(copy_row_start, copy_row_end):
                    for x in range(xpos, xpos + self.content_width):
                        screen.data_buffer[y][x] = temp_screen.data_buffer[y][x]
                        mouse_handlers.mouse_handlers[y][
                            x
                        ] = temp_mouse_handlers.mouse_handlers[y][x]
                        screen.zero_width_escapes[y][
                            x
                        ] = temp_screen.zero_width_escapes[y][x]

                # Copy cursors
                for window, point in temp_screen.cursor_positions.items():
                    # Check cursor is in the visibile zone on the temp screen
                    if (
                        xpos <= point.x < xpos + self.content_width
                        and ypos <= point.y < xpos + self.content_height
                    ):
                        screen.cursor_positions[window] = point
                        # Show cursors if one is within the copied region
                        if temp_screen.show_cursor:
                            screen.show_cursor = True

                # Copy write positions
                screen.visible_windows_to_write_positions.update(
                    temp_screen.visible_windows_to_write_positions
                )

            # If the child is fully visible, simply write it to the screen
            else:
                drawing.container.write_to_screen(
                    screen,
                    mouse_handlers,
                    WritePosition(
                        xpos, ypos + drawing.top, self.content_width, drawing.height
                    ),
                    style,
                    erase_bg,
                    z_index,
                )

        # Fill in the unused space
        spaces = []
        if self.to_draw:
            # top space
            spaces.append((0, self.to_draw[0].top))
            # bottom space
            spaces.append(
                (
                    self.to_draw[-1].top + self.to_draw[-1].height,
                    self.available_height
                    - (self.to_draw[-1].top + self.to_draw[-1].height),
                )
            )
        else:
            spaces.append((0, self.available_height))
        for (start, height) in spaces:
            if height > 0:
                Window(char=" ", style="class:default").write_to_screen(
                    screen,
                    mouse_handlers,
                    WritePosition(xpos, ypos + start, self.content_width, height),
                    style,
                    erase_bg,
                    z_index,
                )

        # Draw floats before wrapping mouse handlers
        screen.draw_all_floats()

        # Wrap all the mouse handlers to add mouse scrolling
        mouse_handler_wrappers: "Dict[MouseHandler, MouseHandler]" = {}

        def _wrap_mouse_handler(
            handler: "Callable",
        ) -> "Callable[[MouseEvent], object]":
            if handler not in mouse_handler_wrappers:

                def wrapped_mouse_handler(mouse_event: "MouseEvent") -> "None":
                    if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                        self.scroll(-1)
                    elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                        self.scroll(1)
                    elif handler:
                        handler(mouse_event)

                mouse_handler_wrappers[handler] = wrapped_mouse_handler
            return mouse_handler_wrappers[handler]

        for y in range(ypos, ypos + write_position.height):
            mouse_row = mouse_handlers.mouse_handlers[y]
            for x in range(
                write_position.xpos, write_position.xpos + write_position.width
            ):
                mouse_row[x] = _wrap_mouse_handler(mouse_row[x])

    # End of container methods

    @property
    def children(self) -> "Sequence[Union[Container, MagicContainer]]":
        """Return the current children of this contianer instance."""
        if callable(self._children):
            return self._children()
        else:
            return self._children

    def get_child(self, index: "Optional[int]" = None) -> "AnyContainer":
        """Return a rendered instance of the child at the given index.

        If no index is given, the currently selected child is returned.

        Args:
            index: The index of the child to return.

        Returns:
            A rendered instance of the child.

        """
        if index is None:
            index = self.last_selected_index
        return self.children[index]

    def get_child_size(self, index: "int", refresh: "bool" = False) -> "int":
        """Return the last known height of the child at the given index.

        For unrendered children, the height is retrieved from a cache unless `refresh`
        is `True`.

        Args:
            index: The index of the child for which to get the last known height.
            refresh: Whether to render an underendered child to calculate its height.

        Returns:
            The height of the child in rows.

        """
        if not refresh and (size := self.size_cache.get(index)):
            return size
        else:
            child = self.get_child(index)
            # assert isinstance(child, AnyContainer)
            container = to_container(child)
            size = container.preferred_height(
                self.content_width, self.content_height
            ).preferred
            self.size_cache[index] = size
            return size

    def arrange_children(
        self, write_position: "WritePosition"
    ) -> "List[DrawingPosition]":
        """Calculate which children should be draw and at which positions.

        Args:
            write_position: Defines the space available for drawing children.

        Returns:
            A list of `DrawingPosition`, detailing the positions at which the children
                should be drawn to the screen.

        """
        selected_index = self.selected_index

        # Create a new version of the child cache
        cache = {}

        # Get a handle on the current child
        # child = self.get_child(selected_index)
        # container = to_container(child)
        # cache[selected_index] = child
        # size = self.get_child_size(selected_index, refresh=True)

        # Empy the list of container
        self.to_draw = []

        # Display selected child and those below it that are on screen
        if self.selected_child_position <= self.content_height:
            top = self.selected_child_position
            for i in range(self.selected_index, len(self.children)):
                size = self.get_child_size(i)
                if 0 <= top + size:
                    cache[i] = self.get_child(i)
                    container = to_container(cache[i])
                    size = self.get_child_size(i, refresh=True)
                    drawing_position = DrawingPosition(
                        index=i,
                        container=container,
                        top=top,
                        height=size,
                        parent_height=self.content_height,
                    )
                    self.to_draw.append(drawing_position)
                top += size
                if top >= self.content_height:
                    break

        # Add children to fill space above the selected child if any are on screen
        if self.selected_child_position > 0:
            top = self.selected_child_position
            for i in range(selected_index - 1, -1, -1):
                size = self.get_child_size(i)
                if top >= 0:
                    cache[i] = self.get_child(i)
                    container = to_container(cache[i])
                    size = self.get_child_size(i, refresh=True)
                    drawing_position = DrawingPosition(
                        index=i,
                        container=container,
                        top=top - size,
                        height=size,
                        parent_height=self.content_height,
                    )
                    self.to_draw.append(drawing_position)
                top -= size
                if top <= 0:
                    break

        # Add additional children to cache
        if cache:
            next_child_index = min(len(self.children) - 1, max(cache.keys()) + 1)
            if next_child_index not in cache:
                cache[next_child_index] = self.get_child(next_child_index)
            prev_child_index = max(0, min(cache.keys()) - 1)
            if prev_child_index not in cache:
                cache[prev_child_index] = self.get_child(prev_child_index)
        # Ensure the selected child is in the cache
        if self.selected_index not in cache:
            cache[self.selected_index] = self.get_child(self.selected_index)
        # Replace the cache
        self.visible = cache

        # Sort drawings
        self.to_draw = sorted(self.to_draw, key=lambda x: x.index)

        return self.to_draw

    def is_child_fully_visible(self, index: "int") -> "bool":
        """Determine if a child is fully onscreen.

        Args:
            index: The index of the child of interest.

        Returns:
            False if the child is fully or partially off-screen, otherwise True.

        """
        drawing = {drawing.index: drawing for drawing in self.to_draw}.get(index)
        return True
        return (
            drawing is not None
            and 0 <= drawing.top
            and drawing.top + drawing.height <= drawing.parent_height
        )

    def select_child(self, new_index: "int") -> "None":
        """Focus a child and scroll so it is visible.

        Args:
            new_index: The index of the child to select.

        """
        # Get the height and position of the newly selected child
        # Check if the newly selected child is currently in view
        drawing = {drawing.index: drawing for drawing in self.to_draw}.get(new_index)
        # If it is displayed on the screen, we already have that information
        if drawing:
            new_child_height = drawing.height
            new_top = drawing.top
        # If it is not displayed on the screen, we can load it from the child cache or
        # render it to calculate it's size. If it's not drawn, we pretend its position
        # is off the top of the screen or below the bottom, depending on if it is above
        # or below the currently selected child.
        else:
            new_child_height = self.get_child_size(
                new_index,
            )
            # If the children do not overflow the screen, move to the position of the
            # lowest child instead of the bottom of the screen
            new_top = (
                min(
                    max([drawing.top + drawing.height for drawing in self.to_draw]),
                    self.content_height,
                )
                if new_index > self.last_selected_index
                else 0
            )

        # If the newly selected is off the top of the display, position it at the top
        if new_top < 0:
            self.selected_child_position = 0
        # If it is off the bottom of the screen, move it fully into view at the bottom
        elif new_top > self.content_height - new_child_height:
            self.selected_child_position = max(
                0, self.content_height - new_child_height
            )
        # Otherwise, it is fully on screen, so move the selection to it's position
        else:
            self.selected_child_position = new_top

        self.focus(new_index)

    def scroll(self, n: "int" = 1) -> "None":
        """Scrolls up or down a number of rows.

        Args:
            n: The number of rows to scroll, negative for up, positive for down

        """
        for drawing in self.to_draw:
            if drawing.index == 0:
                if n > 0 and drawing.top + n > 0:
                    return
                break
            elif drawing.index == len(self.children) - 1:
                if n < 0 and drawing.top + drawing.height < self.content_height // 2:
                    return
                break
        self.selected_child_position += n

    @property
    def selected_index(self) -> "int":
        """Returns in index of the currently selected child."""
        app = get_app()
        # Detect if focused child element has changed
        if app.layout.has_focus(self):
            # Find index of selected child
            index = self.last_selected_index
            for i, child in self.visible.items():
                if app.layout.has_focus(child):
                    index = i
                    break
            # This will change the position when a new child is selected
            self.selected_index = index
        return self.last_selected_index

    @selected_index.setter
    def selected_index(self, new_index: "int") -> "None":
        """Sets the currently selected child index.

        Args:
            new_index: The index of the child to select.

        """
        self._set_selected_index(new_index)

    def _set_selected_index(self, new_index: "int", force: "bool" = False) -> None:
        # Only update the selected child if it was not selected before
        if force or new_index != self.last_selected_index:
            # Ensure selected index is a valid child
            new_index = min(max(new_index, 0), len(self.children) - 1)
            self.select_child(new_index)

            # Track which child was selected
            self.last_selected_index = new_index

    def focus(self, index: "Optional[int]" = None) -> "None":
        """Focuses the child with the given index.

        Args:
            index: The index of the child to focus.
        """
        if index is None:
            index = self.last_selected_index
        child = self.get_child(index)
        app = get_app()
        if not app.layout.has_focus(child):
            app.layout.focus(child)


class ScrollBar(UIControl):
    """A verical scrollbar for :py:class:`ScrollingContainer`."""

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
        sizes = dict(self.target.size_cache)
        avg_size = sum(sizes.values()) / len(sizes)
        for i in range(n_children):
            if i not in sizes:
                sizes[i] = int(avg_size)
        # We let people scoll below the bottom by ½
        self.total_height = max(sum(sizes.values()) - height // 2, 1)
        offset = (
            sum(list(sizes.values())[: self.target.last_selected_index])
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

    def mouse_handler(self, mouse_event: MouseEvent) -> "None":
        """Handle mouse events."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            if mouse_event.position.y == 0:
                self.target.scroll(1)
            elif mouse_event.position.y == self.height - 1:
                self.target.scroll(-1)
            else:
                rel = int(
                    (
                        (self.top - mouse_event.position.y + self.size // 2)
                        / (self.height - self.size - 2)
                    )
                    * self.total_height
                )
                log.debug(rel)
                self.target.scroll(rel)
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.target.scroll(n=-1)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.target.scroll(n=1)
