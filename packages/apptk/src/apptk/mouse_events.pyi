import logging
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

from .data_structures import Point

if TYPE_CHECKING:
    from apptk.data_structures import Point

log = logging.getLogger(__name__)

__all__ = [
    "MouseButton",
    "MouseEvent",
    "MouseEventType",
    "MouseModifier",
]

class MouseEventType(Enum):
    MOUSE_UP = "MOUSE_UP"
    MOUSE_DOWN = "MOUSE_DOWN"
    SCROLL_UP = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    MOUSE_MOVE = "MOUSE_MOVE"

class MouseButton(Enum):
    LEFT = "LEFT"
    MIDDLE = "MIDDLE"
    RIGHT = "RIGHT"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"

class MouseModifier(Enum):
    SHIFT = "SHIFT"
    ALT = "ALT"
    CONTROL = "CONTROL"

class RelativePosition(NamedTuple):
    x: float
    y: float

class MouseEvent:
    position: Point
    event_type: MouseEventType
    button: MouseButton
    modifiers: frozenset[MouseModifier]
    cell_position: RelativePosition | None
    def __init__(
        self,
        position: Point,
        event_type: MouseEventType,
        button: MouseButton,
        modifiers: frozenset[MouseModifier],
        cell_position: RelativePosition | None = None,
    ) -> None: ...
    def __repr__(self) -> str: ...
