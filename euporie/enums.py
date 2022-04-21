"""Defines enums."""

from enum import Enum


class TabMode(Enum):
    """Defines how multiple tabs are displayed."""

    STACK = "stack"
    TILE_HORIZONTAL = "tile_horizontal"
    TILE_VERTICAL = "tile_vertical"
