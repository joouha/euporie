"""Defines commands relating to cell outputs."""

import logging

from prompt_toolkit.data_structures import Point

from euporie.app.current import get_base_app as get_app
from euporie.commands.registry import add
from euporie.filters import cell_output_has_focus

log = logging.getLogger(__name__)


@add(keys=["up", "k"], filter=cell_output_has_focus, group="cell-output")
def scroll_up_cell_output() -> "None":
    """Scroll the output up one line."""
    get_app().layout.current_window._scroll_up()


@add(keys=["down", "j"], filter=cell_output_has_focus, group="cell-output")
def scroll_down_cell_output() -> "None":
    """Scroll the output down one line."""
    get_app().layout.current_window._scroll_down()


@add(keys="pageup", filter=cell_output_has_focus, group="cell-output")
def page_up_cell_output() -> "None":
    """Scroll the output up one page."""
    window = get_app().layout.current_window
    if window.render_info is not None:
        for _ in range(window.render_info.window_height):
            window._scroll_up()


@add(keys="pagedown", filter=cell_output_has_focus, group="cell-output")
def page_down_cell_output() -> "None":
    """Scroll the output down one page."""
    window = get_app().layout.current_window
    if window.render_info is not None:
        for _ in range(window.render_info.window_height):
            window._scroll_down()


@add(keys="home", filter=cell_output_has_focus, group="cell-output")
def go_to_start_of_cell_output() -> "None":
    """Scroll the output to the top."""
    from euporie.output.control import OutputControl

    current_control = get_app().layout.current_control
    if isinstance(current_control, OutputControl):
        current_control.cursor_position = Point(0, 0)


@add(keys="end", filter=cell_output_has_focus, group="cell-output")
def go_to_end_of_cell_output() -> "None":
    """Scroll the output down one page."""
    from euporie.output.control import OutputControl

    layout = get_app().layout
    current_control = layout.current_control
    window = layout.current_window
    if isinstance(current_control, OutputControl) and window.render_info is not None:
        current_control.cursor_position = Point(
            0, window.render_info.ui_content.line_count - 1
        )
