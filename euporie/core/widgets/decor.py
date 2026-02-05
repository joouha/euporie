"""Decorative widgets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.filters import to_filter
from euporie.apptk.layout.containers import (
    DummyContainer,
    DynamicContainer,
    HSplit,
    VSplit,
)
from euporie.apptk.layout.decor import DropShadow

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.filters.core import FilterOrBool

    from euporie.apptk.layout.containers import AnyContainer
    from euporie.apptk.mouse_events import MouseEvent

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class Shadow:
    """Draw a shadow underneath/behind this container.

    The container must be in a float.
    """

    def __init__(self, body: AnyContainer, filter: FilterOrBool = True) -> None:
        """Initialize a new drop-shadow container.

        Args:
            body: Another container object.
            filter: Determines if the shadow should be applied
        """
        filter = to_filter(filter)

        spacer = DummyContainer(width=1, height=1)
        shadow = VSplit(
            [
                HSplit([body, VSplit([spacer, DropShadow()])]),
                HSplit([spacer, DropShadow()]),
            ]
        )

        def get_contents() -> AnyContainer:
            if filter():
                return shadow
            else:
                return body

        self.container = DynamicContainer(get_contents)

    def __pt_container__(self) -> AnyContainer:
        """Return the container's content."""
        return self.container
