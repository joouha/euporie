from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from apptk.mouse_events import MouseEvent

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import NotImplementedOrNone

MouseHandler = Callable[[MouseEvent], "NotImplementedOrNone"]

__all__ = [
    "MouseHandler",
    "MouseHandlers",
]

class MouseHandlers:
    mouse_handlers: defaultdict[int, defaultdict[int, MouseHandler]]
    def __init__(self) -> None: ...
    def set_mouse_handler_for_range(
        self,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
        handler: Callable[[MouseEvent], NotImplementedOrNone],
    ) -> None: ...
