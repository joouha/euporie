"""Define box border constants."""

from abc import ABCMeta
from typing import Optional

from prompt_toolkit.layout.containers import Container
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition

from euporie.config import config

__all__ = ["SquareBorder", "RoundBorder", "BorderLine", "Pattern"]


class Border(metaclass=ABCMeta):
    """Base border type."""

    TOP_LEFT: str
    TOP_SPLIT: str
    TOP_RIGHT: str
    HORIZONTAL: str
    INNER_VERTICAL: str
    VERTICAL: str
    LEFT_SPLIT: str
    RIGHT_SPLIT: str
    CROSS: str
    BOTTOM_LEFT: str
    BOTTOM_SPLIT: str
    BOTTOM_RIGHT: str
    NONE: str


class NoBorder(Border):
    """Invisible border."""

    TOP_LEFT = " "
    TOP_SPLIT = " "
    TOP_RIGHT = " "
    HORIZONTAL = " "
    INNER_VERTICAL = " "
    VERTICAL = " "
    LEFT_SPLIT = " "
    RIGHT_SPLIT = " "
    CROSS = " "
    BOTTOM_LEFT = " "
    BOTTOM_SPLIT = " "
    BOTTOM_RIGHT = " "


class SquareBorder(Border):
    """Square thin border."""

    TOP_LEFT = "┌"
    TOP_SPLIT = "┬"
    TOP_RIGHT = "┐"
    HORIZONTAL = "─"
    INNER_VERTICAL = "│"
    VERTICAL = "│"
    LEFT_SPLIT = "├"
    RIGHT_SPLIT = "┤"
    CROSS = "┼"
    BOTTOM_LEFT = "└"
    BOTTOM_SPLIT = "┴"
    BOTTOM_RIGHT = "┘"


class RoundBorder(SquareBorder):
    """Thin border with round corners."""

    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"


class DoubleBorder(Border):
    """Square border with double lines."""

    TOP_LEFT = "╔"
    TOP_SPLIT = "╦"
    TOP_RIGHT = "╗"
    HORIZONTAL = "═"
    VERTICAL = "║"
    LEFT_SPLIT = "╠"
    RIGHT_SPLIT = "╣"
    CROSS = "╬"
    BOTTOM_LEFT = "╚"
    BOTTOM_SPLIT = "╩"
    BOTTOM_RIGHT = "╝"


class ThickBorder(Border):
    """Square border with thick lines."""

    TOP_LEFT = "┏"
    TOP_SPLIT = "┳"
    TOP_RIGHT = "┓"
    HORIZONTAL = "━"
    VERTICAL = "┃"
    LEFT_SPLIT = "┣"
    RIGHT_SPLIT = "┫"
    CROSS = "╋"
    BOTTOM_LEFT = "┗"
    BOTTOM_SPLIT = "┻"
    BOTTOM_RIGHT = "┛"


class ThickVerticalEdgeBorder(SquareBorder):
    """Box drawing characters with thick verticals outer edges."""

    TOP_LEFT = "┎"
    TOP_RIGHT = "┒"
    VERTICAL = "┃"
    INNER_VERTICAL = "│"
    LEFT_SPLIT = "┠"
    RIGHT_SPLIT = "┨"
    BOTTOM_LEFT = "┖"
    BOTTOM_RIGHT = "┚"


class BorderLine(Container):
    """Draws a horizontal or vertical line."""

    def __init__(
        self,
        char: "Optional[str]" = None,
        width: "Optional[int]" = None,
        height: "Optional[int]" = None,
        collapse: "bool" = False,
        style: "str" = "class:border-line",
    ) -> "None":
        """Initializes a border line.

        Args:
            char: The character to draw. If unset, the relevant character from
                :py:class:`euporie.box.Border` is used
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
            char = SquareBorder.VERTICAL if width else SquareBorder.HORIZONTAL
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

    def __init__(self) -> "None":
        """Initialize the :class:`Pattern`."""
        self.bg = Char(" ", "class:pattern")
        self.char = Char(config.background_character, "class:pattern")

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
