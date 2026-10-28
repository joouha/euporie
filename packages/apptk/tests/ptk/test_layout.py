"""Tests for layout functionality."""

from __future__ import annotations

import pytest
from apptk.application import Application
from apptk.application.current import set_app
from apptk.input.defaults import create_pipe_input
from apptk.layout import InvalidLayoutError, Layout
from apptk.layout.containers import HSplit, VSplit, Window
from apptk.layout.controls import BufferControl, UIContent, UIControl
from apptk.layout.screen import WritePosition
from apptk.output import DummyOutput


class CountingControl(UIControl):
    """Control that counts preferred-dimension calculations."""

    def __init__(self) -> None:
        """Initialize the call counters."""
        self.width_calls = 0
        self.height_calls = 0

    def create_content(self, width: int, height: int) -> UIContent:
        """Return a single blank line."""

        def get_line(i: int) -> list[tuple[str, str]]:
            return []

        return UIContent(get_line=get_line, line_count=1)

    def preferred_width(self, max_available_width: int) -> int:
        """Return a fixed preferred width and count the call."""
        self.width_calls += 1
        return 10

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: object,
    ) -> int:
        """Return a fixed preferred height and count the call."""
        self.height_calls += 1
        return 3


def test_layout_class() -> None:
    """Test the Layout class."""
    c1 = BufferControl()
    c2 = BufferControl()
    c3 = BufferControl()
    win1 = Window(content=c1)
    win2 = Window(content=c2)
    win3 = Window(content=c3)

    layout = Layout(container=VSplit([HSplit([win1, win2]), win3]))

    # Listing of windows/controls.
    assert list(layout.find_all_windows()) == [win1, win2, win3]
    assert list(layout.find_all_controls()) == [c1, c2, c3]

    # Focusing something.
    layout.focus(c1)
    assert layout.has_focus(c1)
    assert layout.has_focus(win1)
    assert layout.current_control == c1
    assert layout.previous_control == c1

    layout.focus(c2)
    assert layout.has_focus(c2)
    assert layout.has_focus(win2)
    assert layout.current_control == c2
    assert layout.previous_control == c1

    layout.focus(win3)
    assert layout.has_focus(c3)
    assert layout.has_focus(win3)
    assert layout.current_control == c3
    assert layout.previous_control == c2

    # Pop focus. This should focus the previous control again.
    layout.focus_last()
    assert layout.has_focus(c2)
    assert layout.has_focus(win2)
    assert layout.current_control == c2
    assert layout.previous_control == c1


def test_create_invalid_layout() -> None:
    """Test creating an invalid layout raises an error."""
    with pytest.raises(InvalidLayoutError):
        Layout(HSplit([]))


def test_preferred_dimensions_cached_per_render() -> None:
    """Preferred dimensions are reused within a render and refreshed after it."""
    control = CountingControl()
    window = Window(content=control)

    with create_pipe_input() as pipe_input:
        app = Application(
            layout=Layout(Window()),
            output=DummyOutput(),
            input=pipe_input,
        )
        with set_app(app):
            assert window.preferred_width(80).preferred == 10
            assert window.preferred_height(80, 24).preferred == 3
            assert control.width_calls == 1
            assert control.height_calls == 1

            # Repeated queries in the same render are cache hits.
            assert window.preferred_width(80).preferred == 10
            assert window.preferred_height(80, 24).preferred == 3
            assert control.width_calls == 1
            assert control.height_calls == 1

            # A new render expires the previous dimensions.
            app.render_counter += 1
            assert window.preferred_width(80).preferred == 10
            assert window.preferred_height(80, 24).preferred == 3
            assert control.width_calls == 2
            assert control.height_calls == 2


def test_split_dimensions_cached_per_render() -> None:
    """Split dimension calculations are reused within a render."""
    control = CountingControl()
    window = Window(content=control)
    split = VSplit([window, Window(content=CountingControl())])
    write_position = WritePosition(xpos=0, ypos=0, width=80, height=24)

    with create_pipe_input() as pipe_input:
        app = Application(
            layout=Layout(Window()),
            output=DummyOutput(),
            input=pipe_input,
        )
        with set_app(app):
            first = split._divide_widths(80)
            assert first is not None
            assert control.width_calls == 1

            second = split._divide_widths(80)
            assert second == first
            assert control.width_calls == 1

            app.render_counter += 1
            third = split._divide_widths(80)
            assert third == first
            assert control.width_calls == 2

            hsplit = HSplit([window])
            heights = hsplit._divide_heights(write_position)
            assert heights is not None
            height_calls = control.height_calls
            assert hsplit._divide_heights(write_position) == heights
            assert control.height_calls == height_calls

            app.render_counter += 1
            assert hsplit._divide_heights(write_position) == heights
            assert control.height_calls == height_calls + 1
