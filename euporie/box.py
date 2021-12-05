# -*- coding: utf-8 -*-
"""Define box border constants."""
from prompt_toolkit.layout.containers import Container
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.screen import Char

from euporie.config import config


class Border:
    """Box drawing characters, includeing characters for splits."""

    HORIZONTAL = "─"
    VERTICAL = "│"
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    SPLIT_BOTTOM = "┴"
    SPLIT_TOP = "┬"
    SPLIT_LEFT = "├"
    SPLIT_RIGHT = "┤"
    CROSS = "┼"


class BorderLine(Container):
    """
    Generate the background of dots, which becomes visible when several clients
    are attached and not all of them have the same size.
    (This is implemented as a Container, rather than a UIControl wrapped in a
    Window, because it can be done very effecient this way.)
    """

    def __init__(self, char=None, width=None, height=None, collapse=False, style=""):
        if width and height:
            raise ValueError("Only one of `width` or `height` must be set")
        self.width = width
        self.height = height
        if char is None:
            char = Border.VERTICAL if width else Border.HORIZONTAL
        self.char = Char(char, style)
        self.collapse = collapse

    def reset(self):
        pass

    def preferred_width(self, max_available_width):
        return Dimension(min=int(not self.collapse), max=self.width)

    def preferred_height(self, width, max_available_height):
        return Dimension(min=int(not self.collapse), max=self.height)

    def write_to_screen(
        self, screen, mouse_handlers, write_position, parent_style, erase_bg, z_index
    ):
        """Fill the whole area of write_position with dots."""

        ypos = write_position.ypos
        xpos = write_position.xpos

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + write_position.width):
                row[x] = self.char

    def get_children(self):
        return []


class Pattern(Container):
    """
    Generate the background of dots, which becomes visible when several clients
    are attached and not all of them have the same size.
    (This is implemented as a Container, rather than a UIControl wrapped in a
    Window, because it can be done very effecient this way.)
    """

    def __init__(self):
        self.bg = Char(" ", "class:background-pattern")

    def reset(self):
        pass

    def preferred_width(self, max_available_width):
        return Dimension()

    def preferred_height(self, width, max_available_height):
        return Dimension()

    def write_to_screen(
        self, screen, mouse_handlers, write_position, parent_style, erase_bg, z_index
    ):
        """Fill the whole area of write_position with dots."""

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
                    row[x] = Char(
                        config.background_character, "class:background-pattern"
                    )
                else:
                    row[x] = self.bg

    def get_children(self):
        return []
