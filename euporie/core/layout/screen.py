"""Overrides for PTK containers which only render visible lines."""

from __future__ import annotations

from prompt_toolkit.layout.screen import WritePosition

from euporie.core.data_structures import DiInt


class BoundedWritePosition(WritePosition):
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
