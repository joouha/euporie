"""Overrides for PTK containers which only render visible lines."""

from __future__ import annotations

import logging
from collections import ChainMap, defaultdict

from prompt_toolkit.layout.screen import _CHAR_CACHE, Char
from prompt_toolkit.layout.screen import Screen as PtkScreen
from prompt_toolkit.layout.screen import WritePosition as PtkWritePosition

from euporie.apptk.data_structures import DiInt

log = logging.getLogger(__name__)


class WritePosition(PtkWritePosition):
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


class ChainBuffer(dict):
    """Overlay screen buffers, storing writes in a separate buffer."""

    def __init__(
        self,
        base: defaultdict[int, defaultdict[int, str]],
    ) -> None:
        """Initialize the chain buffer with lower and upper layers.

        Args:
            lower: The lower buffer layer that receives new writes.
            upper: The upper buffer layer containing existing data.
        """
        self.layers = {0: base}

    def add_layer(self, z_index: int):
        if z_index not in self.layers:
            self.layers[z_index] = defaultdict(dict)
            self.clear()

    def __missing__(self, key: int) -> str:
        """Return a chained mapping for the given row key.

        Args:
            key: The row index to retrieve.

        Returns:
            A ChainMap combining the lower and upper buffer rows.
        """
        self[key] = ChainMap(
            *(layer[key] for _z, layer in sorted(self.layers.items(), reverse=True)),
        )
        return self[key]

    def flatten(self) -> defaultdict[int, defaultdict[int, str]]:
        """Merge the lower buffer into the upper buffer and return it.

        Returns:
            The upper buffer with all lower buffer data merged in.
        """
        base = self.layers[0]
        for _z, layer in sorted(self.layers.items())[1:]:
            for x, row in layer.items():
                base[x].update(row)
        self.layers.clear()
        return base


class Screen(PtkScreen):
    """Screen class which uses :py:`BoundedWritePosition`s."""

    def draw_all_floats(self) -> None:
        """Draw all float functions in order of z-index.

        We first draw them to a separate screen layer, then copy that over the screen.
        This allows floats to detect if there is anything underneath them (required for
        automatically hiding terminal graphics which collide with floats).
        """
        self.data_buffer = ChainBuffer(self.data_buffer)
        self.zero_width_escapes = ChainBuffer(self.zero_width_escapes)
        while self._draw_float_functions:
            # Sort the floats that we have so far by z_index.
            functions = sorted(self._draw_float_functions, key=lambda item: item[0])
            # Draw only one at a time, then sort everything again. Now floats
            # might have been added.
            self._draw_float_functions = functions[1:]

            z_index, func = functions[0]
            # Add a new layer for this float
            self.data_buffer.add_layer(z_index)
            self.zero_width_escapes.add_layer(z_index)
            # Draw the float
            func()

        self.data_buffer = self.data_buffer.flatten()
        self.zero_width_escapes = self.zero_width_escapes.flatten()

    def fill_area(
        self, write_position: WritePosition, style: str = "", after: bool = False
    ) -> None:
        """Fill the content of this area, using the given `style`.

        Args:
            write_position: The position and dimensions of the area to fill.
            style: The style string to apply to the area.
            after: If True, append the style; otherwise prepend it.
        """
        if not style.strip():
            return

        bbox = write_position.bbox

        xmin = write_position.xpos + bbox.left
        xmax = write_position.xpos + write_position.width - bbox.right
        char_cache = _CHAR_CACHE
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
