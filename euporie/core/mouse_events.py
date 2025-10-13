"""Key bindings to deal with pixel mouse positioning."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.mouse_events import MouseButton, MouseEventType, MouseModifier
from prompt_toolkit.mouse_events import MouseEvent as PtkMouseEvent

if TYPE_CHECKING:
    from prompt_toolkit.data_structures import Point

log = logging.getLogger(__name__)


class RelativePosition(NamedTuple):
    """Store the relative position or the mouse within a terminal cell."""

    x: float
    y: float


class MouseEvent(PtkMouseEvent):
    """Mouse event, which also store relative position of the mouse event in a cell."""

    def __init__(
        self,
        position: Point,
        event_type: MouseEventType,
        button: MouseButton,
        modifiers: frozenset[MouseModifier],
        cell_position: RelativePosition | None,
    ) -> None:
        """Create new event instance."""
        super().__init__(
            position=position,
            event_type=event_type,
            button=button,
            modifiers=modifiers,
        )
        self.cell_position = cell_position or RelativePosition(0.5, 0.5)
