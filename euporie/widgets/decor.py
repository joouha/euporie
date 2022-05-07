"""Decorative widgets."""

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.widgets import Label

from euporie.border import Thin
from euporie.config import config

if TYPE_CHECKING:
    from typing import Optional

log = logging.getLogger(__name__)


class Line(Container):
    """Draws a horizontal or vertical line."""

    def __init__(
        self,
        char: "Optional[str]" = None,
        width: "Optional[int]" = None,
        height: "Optional[int]" = None,
        collapse: "bool" = False,
        style: "str" = "class:grid-line",
    ) -> "None":
        """Initializes a grid line.

        Args:
            char: The character to draw. If unset, the relevant character from
                :py:class:`euporie.box.grid` is used
            width: The length of the line. If specified, the line will be horizontal
            height: The height of the line. If specified, the line will be vertical
            collapse: Whether to hide the line when there is not enough space
            style: Style to apply to the line

        Raises:
            ValueError: If both width and height are specified. A line must only have a
                single dimension.

        """
        if width and height:
            raise ValueError("Only one of `width` or `height` must be set")
        self.width = width
        self.height = height
        if char is None:
            char = Thin.grid.VERTICAL if width else Thin.grid.HORIZONTAL
        self.char = Char(char, style)
        self.collapse = collapse

    def reset(self) -> "None":
        """Resets the state of the line. Does nothing."""

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Return the preferred width of the line."""
        return Dimension(min=int(not self.collapse), max=self.width)

    def preferred_height(
        self, width: "int", max_available_height: "int"
    ) -> "Dimension":
        """Return the preferred height of the line."""
        return Dimension(min=int(not self.collapse), max=self.height)

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
    ) -> "None":
        """Draws a continuous line in the ``write_position`` area.

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

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + write_position.width):
                row[x] = self.char

    def get_children(self) -> "list":
        """Return an empty list of the container's children."""
        return []


class Pattern(Container):
    """Fill an area with a repeating background pattern."""

    def __init__(self, char: "str") -> "None":
        """Initialize the :class:`Pattern`."""
        self.bg = Char(" ", "class:pattern")
        self.char = Char(char, "class:pattern")

    def reset(self) -> "None":
        """Resets the pattern. Does nothing."""
        pass

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Return an empty diemension (expand to available width)."""
        return Dimension()

    def preferred_height(
        self, width: "int", max_available_height: "int"
    ) -> "Dimension":
        """Return an empty diemension (expand to available height)."""
        return Dimension()

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
    ) -> "None":
        """Fill the whole area of write_position with a pattern.

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

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + write_position.width):
                if (
                    (config.background_pattern == 1)
                    or (config.background_pattern == 2 and (x + y) % 2 == 0)
                    or (config.background_pattern == 3 and (x + 2 * y) % 4 == 0)
                    or (config.background_pattern == 4 and (x + y) % 3 == 0)
                    or (
                        config.background_pattern == 5
                        and ((x + y % 2 * 3) % 6) % 4 == 0
                    )
                ):
                    row[x] = self.char
                else:
                    row[x] = self.bg

    def get_children(self) -> "list":
        """Return an empty list of the container's children."""
        return []


class Border:
    """Draw a border around any container."""

    def __init__(
        self,
        body: "AnyContainer",
        border: "Optional[GridStyle]" = Thin,
        style: "Union[str, Callable[[], str]]" = "class:frame.border",
        show_borders: "Tuple[FilterOrBool, FilterOrBool, FilterOrBool, FilterOrBool]" = (
            True,
            True,
            True,
            True,
        ),
    ) -> None:
        self.body = body
        self.style = style

        border_top = to_filter(show_borders[0])
        border_right = to_filter(show_borders[1])
        border_bottom = to_filter(show_borders[2])
        border_left = to_filter(show_borders[3])

        if border is not None:
            self.container = HSplit(
                [
                    VSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    height=1,
                                    char=border.TOP_LEFT,
                                    style=self.add_style("class:left,top"),
                                ),
                                filter=border_top & border_left,
                            ),
                            ConditionalContainer(
                                Window(
                                    char=border.TOP_MID,
                                    style=self.add_style("class:top"),
                                ),
                                filter=border_top,
                            ),
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    height=1,
                                    char=border.TOP_RIGHT,
                                    style=self.add_style("class:right,top"),
                                ),
                                filter=border_top & border_right,
                            ),
                        ],
                        height=1,
                    ),
                    VSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_LEFT,
                                    style=self.add_style("class:left"),
                                ),
                                filter=border_left,
                            ),
                            DynamicContainer(lambda: self.body),
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_RIGHT,
                                    style=self.add_style("class:right"),
                                ),
                                filter=border_right,
                            )
                            # Padding is required to make sure that if the content is
                            # too small, the right frame border is still aligned.
                        ],
                        padding=0,
                    ),
                    VSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    height=1,
                                    char=border.BOTTOM_LEFT,
                                    style=self.add_style("class:left,bottom"),
                                ),
                                filter=border_bottom & border_left,
                            ),
                            ConditionalContainer(
                                Window(
                                    char=border.BOTTOM_MID,
                                    style=self.add_style("class:bottom"),
                                ),
                                filter=border_bottom,
                            ),
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    height=1,
                                    char=border.BOTTOM_RIGHT,
                                    style=self.add_style("class:right,bottom"),
                                ),
                                filter=border_bottom & border_right,
                            ),
                        ],
                        # specifying height here will increase the rendering speed.
                        height=1,
                    ),
                ],
            )
        else:
            self.container = body

    def add_style(self, extra):
        def _style():
            if callable(self.style):
                return f"{self.style()} {extra}"
            else:
                return f"{self.style} {extra}"

        return _style

    def __pt_container__(self) -> Container:
        return self.container
