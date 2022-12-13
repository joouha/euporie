"""Contains commonly used data structures."""

from typing import NamedTuple


class BoxSize(NamedTuple):
    """A tuple to hold dimensions for each side of a box."""

    top: int
    right: int
    bottom: int
    left: int
