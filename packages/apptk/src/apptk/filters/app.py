"""Define common filters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apptk.filters.base import Condition

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.filters.base import Filter
    from apptk.layout.containers import Window
    from apptk.layout.layout import FocusableElement

    emacs_insert_mode: Filter
    emacs_mode: Filter
    vi_insert_mode: Filter
    vi_mode: Filter
    vi_navigation_mode: Filter
    vi_replace_mode: Filter
    has_focus: Callable[[FocusableElement], Filter]


@Condition
def display_has_focus() -> bool:
    """Determine if there is a currently focused cell."""
    from apptk.application.current import get_app
    from apptk.layout.display import DisplayControl

    return isinstance(get_app().layout.current_control, DisplayControl)


def scrollable(window: Window) -> Filter:
    """Return a filter which indicates if a window is scrollable."""
    return Condition(
        lambda: (
            window.render_info is not None
            and window.render_info.content_height > window.render_info.window_height
        )
    )


@Condition
def has_toolbar() -> bool:
    """Is there an active toolbar?"""
    from apptk.application.current import get_app
    from apptk.enums import BAR_BUFFERS

    return get_app().current_buffer.name in BAR_BUFFERS
