"""Defines enums."""

from enum import Enum


class TabMode(Enum):
    """Defines how multiple tabs are displayed."""

    STACK = "stack"
    TILE_HORIZONTALLY = "tile_horizontally"
    TILE_VERTICALLY = "tile_vertically"
