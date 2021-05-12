# -*- coding: utf-8 -*-
from collections import namedtuple
from typing import Callable, Dict, List, Optional, Sequence, Union

from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.layout.containers import Container, Window, to_container
from prompt_toolkit.layout.dimension import AnyDimension, Dimension, to_dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandler, MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import to_str

from euporie.box import Border
from euporie.config import config
from euporie.keys import KeyBindingsInfo

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
    def __init__(
        self,
        children,
        max_content_width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: Optional[int] = None,
        style: Union[str, Callable[[], str]] = "",
        show_border: FilterOrBool = True,
    ):
        self.children = children
        if not isinstance(max_content_width, Dimension):
            max_content_width = Dimension(preferred=config.max_notebook_width)
        self.max_content_width = max_content_width
        self.height = height
        self.z_index = z_index
        self.style = style

        self.key_bindings = self.load_key_bindings()

        self._remaining_space_window = Window()

        self.show_border = to_filter(show_border)

        self.last_selected_index: int = 0

        # Position of viewing window relative to selected child
        self.selected_child_position: int = 0
        self.child_cache = {}
        self.size_cache = {}
        self.to_draw: Sequence[DrawingPosition] = []

    # Container methods

    def reset(self) -> None:
        for c in self.get_children():
            c.reset()
        self.child_cache = {}
        self.size_cache = {}

    def preferred_width(self, max_available_width: int):
        dimension = Dimension()
        # if self.max_content_width is not None:
        # dimension.max = 120
        # dimension.preferred = 120
        return dimension

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        if self.height is not None:
            return to_dimension(self.height)
        # Do not report preferred_height height to children so they don't complain about
        # a lack of space
        # return to_dimension(max_available_height-2)
        return Dimension()

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: str,
        erase_bg: bool,
        z_index: Optional[int],
    ) -> None:
        """
        Render the prompt to a `Screen` instance.
        :param screen: The :class:`~prompt_toolkit.layout.screen.Screen` class
            to which the output has to be written.
        """

        self.available_width = write_position.width
        self.available_height = write_position.height

        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        self.content_width = min(
            self.max_content_width.preferred
            if self.max_content_width.preferred
            else self.available_width,
            write_position.width - self.show_scroll * 2,
        )
        self.content_height = self.available_height

        self.to_draw = self.arrange_children(write_position)

        ypos = write_position.ypos
        xpos = (
            write_position.xpos
            + (write_position.width - self.show_scroll * 2 - self.content_width) // 2
        )

        # Draw frame if it fits
        if (
            self.show_border()
            and self.content_width + 4 + self.show_scroll <= self.available_width
        ):
            for y in range(ypos, ypos + self.content_height + 1):
                screen.data_buffer[y][xpos - 2] = Char(Border.VERTICAL)
                screen.data_buffer[y][xpos + 1 + self.content_width] = Char(
                    Border.VERTICAL
                )

        # Draw background if there is space
        if config.background:
            dot = Char(config.background_character, "class:background")
            for y in range(ypos, ypos + self.content_height + 1):
                for xrange in (
                    (write_position.xpos, xpos - 2),
                    (xpos + self.content_width + 2, write_position.width - 1),
                ):
                    for x in range(*xrange):
                        if (
                            (config.background == 1 and (x + y) % 2 == 0)
                            or (config.background == 2 and (x + 2 * y) % 4 == 0)
                            or (config.background == 3 and (x + y) % 3 == 0)
                            or (
                                config.background == 4
                                and ((x + y % 2 * 3) % 6) % 4 == 0
                            )
                        ):
                            screen.data_buffer[y][x] = dot

        # Draw child panes.
        for drawing in self.to_draw:

            if drawing.top < 0 or drawing.top + drawing.height > self.content_height:
                # Create a virtual screen to draw partially obscured children
                temp_screen = Screen(default_char=Char(char=" ", style=parent_style))
                temp_screen.show_cursor = False
                # Create empty mouse handler array
                temp_mouse_handlers = MouseHandlers()
                # Draw child at (0,0) on temp screen
                temp_write_position = WritePosition(
                    xpos=0, ypos=0, width=self.content_width, height=drawing.height
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

                # Determin how many rows to copy
                if drawing.top < 0:
                    copy_rows = drawing.top + drawing.height
                else:  # drawing.top + drawing.height > self.content_height
                    copy_rows = self.content_height - drawing.top

                # Copy screen contents
                for i in range(0, copy_rows):

                    real_y = ypos + max(0, drawing.top) + i
                    virt_y = 0 - min(0, drawing.top) + i

                    real_row = screen.data_buffer[real_y]
                    virt_row = temp_screen.data_buffer[virt_y]

                    real_mouse_row = mouse_handlers.mouse_handlers[real_y]
                    virt_mouse_row = temp_mouse_handlers.mouse_handlers[virt_y]

                    # real_escapes = screen.zero_width_escapes[real_y]
                    # virt_escapes = temp_screen.zero_width_escapes[virt_y]

                    for x in range(self.content_width):
                        real_row[x + xpos] = virt_row[x]
                        real_mouse_row[x + xpos] = virt_mouse_row[x]
                        # real_escapes[x + xpos] = virt_escapes[x]

                # Copy cursors
                if temp_screen.show_cursor:
                    screen.show_cursor = True
                for window, point in temp_screen.cursor_positions.items():
                    # Check cursor is in the visibible zone on the temp screen
                    if (
                        0 <= point.x < self.content_width
                        and 0 - min(0, drawing.top)
                        <= point.y
                        < 0 - min(0, drawing.top) + copy_rows
                    ):
                        screen.cursor_positions[window] = Point(
                            x=point.x + xpos,
                            y=point.y + ypos + drawing.top,
                        )

            # If the cell is fully visible, simply write it to the screen
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

        # Fill empty space, and click to focus
        ###

        # Draw floats before wrapping mouse handlers
        screen.draw_all_floats()

        # Draw scroll bar
        if self.show_scroll:

            x = write_position.xpos + self.available_width - 1

            def mouse_handler_scroll_up(mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    self.scroll_up()

            def mouse_handler_scroll_down(mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    self.scroll_down()

            screen.data_buffer[ypos + 0][x] = Char("▲", "class:scrollbar.arrow")
            mouse_handlers.mouse_handlers[ypos][x] = mouse_handler_scroll_up
            screen.data_buffer[ypos + self.available_height - 1][x] = Char(
                "▼", "class:scrollbar.arrow"
            )
            mouse_handlers.mouse_handlers[ypos + self.available_height - 1][
                x
            ] = mouse_handler_scroll_down

            def scrollbar_mouse_click(index):
                def mouse_handler(mouse_event: MouseEvent):
                    if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                        self.selected_index = index

                return mouse_handler

            scroll_tab_height = max(
                1, (self.available_height - 2) // len(self.children)
            )
            scroll_tab_top = (
                (self.available_height - 2 - scroll_tab_height)
                * self.to_draw[0].index
                // (len(self.children) - 1)
                if self.to_draw
                else 0
            )

            for y in range(self.available_height - 2):
                if scroll_tab_top <= y <= scroll_tab_height + scroll_tab_top:
                    style = "class:scrollbar.button"
                else:
                    style = "class:scrollbar.background"
                    # Set mouse click action
                child_index = int(
                    y / (self.available_height - 2 - 1) * len(self.children)
                )
                mouse_handlers.mouse_handlers[ypos + y + 1][x] = scrollbar_mouse_click(
                    child_index
                )
                screen.data_buffer[ypos + y + 1][x] = Char(style=style)

        # Wrap all the mouse handlers to add mouse scrolling
        mouse_handler_wrappers: Dict[MouseHandler, MouseHandler] = {}

        def wrap_mouse_handler(handler) -> None:
            if handler not in mouse_handler_wrappers:

                def wrapped_mouse_handler(mouse_event: MouseEvent):
                    if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                        self.scroll_down()
                    elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                        self.scroll_up()
                    elif handler:
                        handler(mouse_event)

                mouse_handler_wrappers[handler] = wrapped_mouse_handler
            return mouse_handler_wrappers[handler]

        for y in range(ypos, ypos + write_position.height):
            mouse_row = mouse_handlers.mouse_handlers[y]
            for x in range(
                write_position.xpos, write_position.xpos + write_position.width
            ):
                mouse_row[x] = wrap_mouse_handler(mouse_row.get(x))

        # If we are using kitty graphics, ensure all existing images are erased
        if get_app().has_kitty_graphics:
            screen.zero_width_escapes[ypos][xpos] = "\x1b_Ga=d\x1b\\"

    @property
    def show_scroll(self):
        return len(self.children) > 1
        # return sum([drawing.height for drawing in self.to_draw]) > self.content_height

    def get_children(self) -> List[Container]:
        return map(to_container, [x[1] for x in sorted(self.child_cache.items())])

    def get_key_bindings(self):
        return self.key_bindings

    # End of container methods

    def load_key_bindings(self):
        kb = KeyBindingsInfo()

        @kb.add("[", group="Navigation", desc="Scroll up")
        @kb.add("<scroll-up>")
        def su(event):
            self.scroll_up()

        @kb.add("]", group="Navigation", desc="Scroll down")
        @kb.add("<scroll-down>")
        def sd(event):
            self.scroll_down()

        @kb.add("c-up", group="Navigation", desc="Go to first cell")
        @kb.add("home", group="Navigation", desc="Go to first cell")
        def first_child(event=None):
            self.selected_index = 0

        @kb.add("pageup", group="Navigation", desc="Go up 5 cells")
        def prev_child5(event=None):
            self.selected_index -= 5

        @kb.add("up", group="Navigation", desc="Go up one cell")
        @kb.add("k", group="Navigation", desc="Go up one cell")
        def prev_child(event=None):
            self.selected_index -= 1

        @kb.add("down", group="Navigation", desc="Go down one cell")
        @kb.add("j", group="Navigation", desc="Go down one cell")
        def next_child(event=None):
            self.selected_index += 1

        @kb.add("pagedown", group="Navigation", desc="Go down 5 cells")
        def next_child5(event=None):
            self.selected_index += 5

        @kb.add("c-down", group="Navigation", desc="Go to last cell")
        @kb.add("end", group="Navigation", desc="Go to last cell")
        def last_child(event=None):
            self.selected_index = len(self.children)

        return kb

    def get_child(self, index=None):
        if index is None:
            index = self.last_selected_index
        child = self.child_cache.get(index)
        if child is None and self.children:
            child = self.children[index]()
            self.child_cache[index] = child
        return child

    def get_child_size(self, index, refresh=False):
        if not refresh and (size := self.size_cache.get(index)):
            return size
        else:
            child = self.get_child(index)
            container = to_container(child)
            size = container.preferred_height(
                self.content_width, self.content_height
            ).preferred
            self.size_cache[index] = size
            return size

    def arrange_children(self, write_position: "WritePosition") -> Optional[List[int]]:
        """
        Return the heights for all rows.
        Or None when there is not enough space.
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
        self.to_draw: Sequence["DrawingPosition"] = []

        # Display selected child and those below it that are on screen
        if self.selected_child_position <= self.content_height:
            top = self.selected_child_position
            for i in range(self.selected_index, len(self.children)):
                size = self.get_child_size(i)
                if 0 <= top + size:
                    cache[i] = self.get_child(i)
                    container = to_container(cache[i])
                    size = self.get_child_size(i, refresh=True)
                    cache[i]._drawing_position = DrawingPosition(
                        index=i,
                        container=container,
                        top=top,
                        height=size,
                        parent_height=self.content_height,
                    )
                    self.to_draw.append(cache[i]._drawing_position)
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
                    cache[i]._drawing_position = DrawingPosition(
                        index=i,
                        container=container,
                        top=top - size,
                        height=size,
                        parent_height=self.content_height,
                    )
                    self.to_draw.append(cache[i]._drawing_position)
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
        self.child_cache = cache

        # Sort drawings
        self.to_draw = sorted(self.to_draw, key=lambda x: x.index)

        return self.to_draw

    def select_child(self, new_index=None):

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

    def scroll_up(self, event=None) -> None:
        for drawing in self.to_draw:
            if drawing.index == 0:
                if drawing.top + 1 > 0:
                    return
                break
        self.selected_child_position += 1

    def scroll_down(self, event=None) -> None:
        for drawing in self.to_draw:
            if drawing.index == len(self.children) - 1:
                if drawing.top + drawing.height < self.content_height // 2:
                    return
                break
        self.selected_child_position -= 1

    @property
    def show_scrollbar(self):
        return sum([x.height for x in self.to_draw]) >= self.content_height

    @property
    def selected_index(self):
        app = get_app()
        # Detect if focused child element has changed
        if app.layout.has_focus(self):
            # Find index of selected child
            for child in self.child_cache.values():
                if app.layout.has_focus(child):
                    break
            # This will perform change the position when the new child is selected
            self.selected_index = child.index
        return self.last_selected_index

    @selected_index.setter
    def selected_index(self, new_index):
        self._set_selected_index(new_index)

    def _set_selected_index(self, new_index, force=False):
        # Only update the selected child if it was not selected before
        if force or new_index != self.last_selected_index:
            # Ensure selected index is a valid child
            new_index = min(max(new_index, 0), len(self.children) - 1)
            self.select_child(new_index)

            # Focus new child if not already focused
            self.focus(new_index)

            # Track which child was selected
            self.last_selected_index = new_index

    def focus(self, index=None):
        if index is None:
            index = self.last_selected_index
        child = self.get_child(index)
        app = get_app()
        if not app.layout.has_focus(child):
            app.layout.focus(child)
