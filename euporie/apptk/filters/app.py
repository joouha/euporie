"""Define common filters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app
from euporie.apptk.filters.base import Condition

if TYPE_CHECKING:
    from euporie.apptk.filters import Filter
    from euporie.apptk.layout.containers import Window


@Condition
def display_has_focus() -> bool:
    """Determine if there is a currently focused cell."""
    from euporie.apptk.layout.display import DisplayControl

    return isinstance(get_app().layout.current_control, DisplayControl)


def scrollable(window: Window) -> Filter:
    """Return a filter which indicates if a window is scrollable."""
    return Condition(
        lambda: (
            window.render_info is not None
            and window.render_info.content_height > window.render_info.window_height
        )
    )
