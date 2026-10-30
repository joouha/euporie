"""Tests for decorative layout containers and window fast paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from apptk.application import Application
from apptk.application.current import set_app
from apptk.border import ThinLine
from apptk.input.defaults import create_pipe_input
from apptk.layout import Layout
from apptk.layout.containers import Window, to_container
from apptk.layout.controls import DummyControl
from apptk.layout.decor import Border, Fill
from apptk.layout.dimension import Dimension
from apptk.layout.mouse_handlers import MouseHandlers
from apptk.layout.screen import Screen, WritePosition
from apptk.output import DummyOutput
from apptk.widgets.base import Frame

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def app() -> Iterator[Application]:
    """Provide a running application context for rendering containers."""
    with create_pipe_input() as pipe_input:
        application = Application(
            layout=Layout(Window()),
            output=DummyOutput(),
            input=pipe_input,
        )
        with set_app(application):
            yield application


def render(container: object, width: int, height: int) -> tuple[list[str], Screen]:
    """Render a container and return its text lines and screen."""
    screen = Screen()
    to_container(container).write_to_screen(
        screen,
        MouseHandlers(),
        WritePosition(0, 0, width, height),
        "",
        False,
        None,
    )
    lines = [
        "".join(screen.data_buffer[y][x].char for x in range(width))
        for y in range(height)
    ]
    return lines, screen


def _dims(dimension: Dimension) -> tuple[int, int, int, int]:
    """Return the comparable fields of a dimension."""
    return (dimension.min, dimension.max, dimension.preferred, dimension.weight)


@pytest.mark.parametrize(
    "dimension",
    [None, 0, 3, Dimension(min=1), Dimension(preferred=2, max=4)],
)
def test_fill_dimensions_match_dummy_window(
    app: Application, dimension: Dimension | int | None
) -> None:
    """A fill reports the same dimensions as an equivalent dummy window."""
    fill = Fill(width=dimension, height=dimension)
    window = Window(DummyControl(), width=dimension, height=dimension)

    assert _dims(fill.preferred_width(80)) == _dims(window.preferred_width(80))
    assert _dims(fill.preferred_height(80, 24)) == _dims(
        window.preferred_height(80, 24)
    )


def test_fill_renders_character(app: Application) -> None:
    """A fill paints its character over its whole area."""
    lines, _screen = render(Fill(char=".", width=3, height=2), 5, 3)
    assert lines == [".....", ".....", "....."]


def test_fill_applies_style(app: Application) -> None:
    """A fill applies its style to the filled area."""
    _lines, screen = render(Fill(char=" ", width=2, height=1, style="class:test"), 2, 1)
    assert "class:test" in screen.data_buffer[0][0].style


def test_border_renders_all_edges(app: Application) -> None:
    """A border draws all four edges and corners around its body."""
    body = Window(DummyControl(), char=" ")
    lines, _screen = render(Border(body, grid=lambda: ThinLine.grid), 6, 4)
    assert lines == [
        "┌────┐",
        "│    │",
        "│    │",
        "└────┘",
    ]


def test_border_supports_disabled_edges(app: Application) -> None:
    """Disabled edges are not drawn and free up space for the body."""
    body = Window(DummyControl(), char=" ")
    lines, _screen = render(
        Border(body, grid=lambda: ThinLine.grid, top=False, left=False), 5, 3
    )
    assert lines == [
        "    │",
        "    │",
        "────┘",
    ]


def test_border_preferred_dimensions(app: Application) -> None:
    """Border dimensions include the enabled edges."""
    body = Window(DummyControl(), width=4, height=2)

    border = Border(body, grid=lambda: ThinLine.grid)
    assert border.preferred_width(80).preferred == 6
    assert border.preferred_height(80, 24).preferred == 4

    partial = Border(body, grid=lambda: ThinLine.grid, top=False, left=False)
    assert partial.preferred_width(80).preferred == 5
    assert partial.preferred_height(80, 24).preferred == 3


def test_border_draws_focusable_corner(app: Application) -> None:
    """A corner container is drawn over the top-left border character."""
    from apptk.layout.controls import FormattedTextControl

    body = Window(DummyControl(), char=" ")
    corner = Window(FormattedTextControl("C"))
    lines, _screen = render(
        Border(body, grid=lambda: ThinLine.grid, corner=corner), 6, 3
    )
    assert lines == [
        "C────┐",
        "│    │",
        "└────┘",
    ]


def test_dummy_window_fast_path(app: Application) -> None:
    """Dummy windows are painted without creating render info."""
    window = Window(DummyControl(), char="x", style="class:fill")
    screen = Screen()
    handlers = MouseHandlers()

    window.write_to_screen(
        screen,
        handlers,
        WritePosition(0, 0, 3, 2),
        "",
        False,
        None,
    )

    assert [
        "".join(screen.data_buffer[y][x].char for x in range(3)) for y in range(2)
    ] == ["xxx", "xxx"]
    assert "class:fill" in screen.data_buffer[0][0].style
    assert window.render_info is None
    assert window in screen.visible_windows_to_write_positions
    # A mouse handler is still installed for the window area.
    assert handlers.mouse_handlers[0][0] == window._dummy_mouse_handler


def test_dummy_window_mouse_handler_returns_not_implemented(
    app: Application,
) -> None:
    """Mouse events on dummy windows bubble up to the parent."""
    from apptk.data_structures import Point
    from apptk.mouse_events import MouseButton, MouseEvent, MouseEventType

    window = Window(DummyControl())
    event = MouseEvent(
        position=Point(x=0, y=0),
        event_type=MouseEventType.MOUSE_DOWN,
        button=MouseButton.LEFT,
        modifiers=frozenset(),
    )
    assert window._dummy_mouse_handler(event) is NotImplemented


def test_frame_renders_border_and_title(app: Application) -> None:
    """Frames draw their border and a centered title."""
    body = Window(DummyControl(), char=" ")
    lines, _screen = render(Frame(body, title="Hi"), 10, 4)
    assert lines == [
        "┌── Hi ──┐",
        "│        │",
        "│        │",
        "└────────┘",
    ]


def test_frame_honours_show_borders(app: Application) -> None:
    """Frames only draw the enabled borders."""
    body = Window(DummyControl(), char=" ")
    lines, _screen = render(Frame(body, show_borders=(False, True, True, False)), 10, 4)
    assert lines == [
        "         │",
        "         │",
        "         │",
        "─────────┘",
    ]


def test_frame_without_borders_is_transparent(app: Application) -> None:
    """A frame with all borders disabled is a transparent wrapper."""
    body = Window(DummyControl(), char=" ")
    lines, _screen = render(Frame(body, show_borders=False), 4, 2)
    assert lines == ["    ", "    "]


def test_frame_preferred_dimensions(app: Application) -> None:
    """Frame dimensions include the enabled borders."""
    body = Window(DummyControl(), width=4, height=2)

    frame = to_container(Frame(body))
    assert frame.preferred_width(80).preferred == 6
    assert frame.preferred_height(80, 24).preferred == 4

    partial = to_container(Frame(body, show_borders=(False, True, True, False)))
    assert partial.preferred_width(80).preferred == 5
    assert partial.preferred_height(80, 24).preferred == 3
