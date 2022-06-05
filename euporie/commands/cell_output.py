"""Defines commands relating to displays."""

import logging

from prompt_toolkit.data_structures import Point

from euporie.app.current import get_base_app as get_app
from euporie.commands.registry import add
from euporie.filters import display_has_focus

log = logging.getLogger(__name__)


@add(keys=["left"], filter=display_has_focus, groups="cell-output")
def scroll_left_cell_output() -> "None":
    """Scroll the display up one line."""
    from euporie.widgets.display import DisplayWindow

    window = get_app().layout.current_window
    assert isinstance(window, DisplayWindow)
    window._scroll_left()


@add(keys=["right"], filter=display_has_focus, groups="cell-output")
def scroll_right_cell_output() -> "None":
    """Scroll the display down one line."""
    from euporie.widgets.display import DisplayWindow

    window = get_app().layout.current_window
    assert isinstance(window, DisplayWindow)
    window._scroll_right()


@add(keys=["up", "k"], filter=display_has_focus, groups="cell-output")
def scroll_up_cell_output() -> "None":
    """Scroll the display up one line."""
    get_app().layout.current_window._scroll_up()


@add(keys=["down", "j"], filter=display_has_focus, groups="cell-output")
def scroll_down_cell_output() -> "None":
    """Scroll the display down one line."""
    get_app().layout.current_window._scroll_down()


@add(keys="pageup", filter=display_has_focus, groups="cell-output")
def page_up_cell_output() -> "None":
    """Scroll the display up one page."""
    window = get_app().layout.current_window
    if window.render_info is not None:
        for _ in range(window.render_info.window_height):
            window._scroll_up()


@add(keys="pagedown", filter=display_has_focus, groups="cell-output")
def page_down_cell_output() -> "None":
    """Scroll the display down one page."""
    window = get_app().layout.current_window
    if window.render_info is not None:
        for _ in range(window.render_info.window_height):
            window._scroll_down()


@add(keys="home", filter=display_has_focus, groups="cell-output")
def go_to_start_of_cell_output() -> "None":
    """Scroll the display to the top."""
    from euporie.widgets.display import DisplayControl

    current_control = get_app().layout.current_control
    if isinstance(current_control, DisplayControl):
        current_control.cursor_position = Point(0, 0)


@add(keys="end", filter=display_has_focus, groups="cell-output")
def go_to_end_of_cell_output() -> "None":
    """Scroll the display down one page."""
    from euporie.widgets.display import DisplayControl

    layout = get_app().layout
    current_control = layout.current_control
    window = layout.current_window
    if isinstance(current_control, DisplayControl) and window.render_info is not None:
        current_control.cursor_position = Point(
            0, window.render_info.ui_content.line_count - 1
        )
