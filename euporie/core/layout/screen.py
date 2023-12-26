"""Overrides for PTK containers which only render visible lines."""

from __future__ import annotations

import logging

from prompt_toolkit.layout import screen

from euporie.core.data_structures import DiInt

log = logging.getLogger(__name__)


class BoundedWritePosition(screen.WritePosition):
    """A write position which also hold bounding box information."""

    def __init__(
        self,
        xpos: int,
        ypos: int,
        width: int,
        height: int,
        bbox: DiInt | None = None,
    ) -> None:
        """Create a new instance of the write position."""
        super().__init__(xpos, ypos, width, height)
        self.bbox = bbox or DiInt(0, 0, 0, 0)

    def __repr__(self) -> str:
        """Return a string representation of the write position."""
        return (
            f"{self.__class__.__name__}("
            f"x={self.xpos}, y={self.ypos}, "
            f"w={self.width}, h={self.height}, "
            f"bbox={self.bbox})"
        )


class Screen(screen.Screen):
    """Screen class which uses :py:`BoundedWritePosition`s."""

    def fill_area(
        self, write_position: screen.WritePosition, style: str = "", after: bool = False
    ) -> None:
        """Fill the content of this area, using the given `style`."""
        if not style.strip():
            return

        if isinstance(write_position, BoundedWritePosition):
            bbox = write_position.bbox
        else:
            bbox = DiInt(0, 0, 0, 0)

        xmin = write_position.xpos + bbox.left
        xmax = write_position.xpos + write_position.width - bbox.right
        char_cache = screen._CHAR_CACHE
        data_buffer = self.data_buffer

        if after:
            append_style = " " + style
            prepend_style = ""
        else:
            append_style = ""
            prepend_style = style + " "

        for y in range(
            write_position.ypos + bbox.top,
            write_position.ypos + write_position.height - bbox.bottom,
        ):
            row = data_buffer[y]
            for x in range(xmin, xmax):
                cell = row[x]
                row[x] = char_cache[
                    cell.char, prepend_style + cell.style + append_style
                ]
