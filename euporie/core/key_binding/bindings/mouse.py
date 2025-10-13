"""Key bindings to deal with pixel mouse positioning."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding.bindings.mouse import (
    MOUSE_MOVE,
    UNKNOWN_BUTTON,
    UNKNOWN_MODIFIER,
    KeyBindings,
    typical_mouse_events,
    urxvt_mouse_events,
    xterm_sgr_mouse_events,
)
from prompt_toolkit.key_binding.bindings.mouse import (
    load_mouse_bindings as load_ptk_mouse_bindings,
)
from prompt_toolkit.keys import Keys
from prompt_toolkit.renderer import HeightIsUnknownError

from euporie.core.app.app import BaseApp
from euporie.core.mouse_events import MouseEvent, RelativePosition

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

log = logging.getLogger(__name__)


def _parse_mouse_data(
    data: str, sgr_pixels: bool, cell_size_xy: tuple[int, int]
) -> MouseEvent | None:
    """Convert key-press data to a mouse event."""
    rx = ry = 0.5

    # Parse incoming packet.
    if data[2] == "M":
        # Typical.
        mouse_event, x, y = map(ord, data[3:])

        # TODO: Is it possible to add modifiers here?
        mouse_button, mouse_event_type, mouse_modifiers = typical_mouse_events[
            mouse_event
        ]

        # Handle situations where `PosixStdinReader` used surrogateescapes.
        if x >= 0xDC00:
            x -= 0xDC00
        if y >= 0xDC00:
            y -= 0xDC00

        x -= 32
        y -= 32
    else:
        # Urxvt and Xterm SGR.
        # When the '<' is not present, we are not using the Xterm SGR mode,
        # but Urxvt instead.
        data = data[2:]
        if data[:1] == "<":
            sgr = True
            data = data[1:]
        else:
            sgr = False

        # Extract coordinates.
        mouse_event, x, y = map(int, data[:-1].split(";"))
        m = data[-1]

        # Parse event type.
        if sgr:
            if sgr_pixels:
                # Scale down pixel-wise mouse position to cell based, and calculate
                # relative position of mouse within the cell
                cell_x, cell_y = cell_size_xy
                px, py = x, y
                fx, fy = px / cell_x + 1, py / cell_y + 1
                x, y = int(fx), int(fy)
                rx, ry = fx - x, fy - y
            try:
                (mouse_button, mouse_event_type, mouse_modifiers) = (
                    xterm_sgr_mouse_events[mouse_event, m]
                )
            except KeyError:
                return None

        else:
            # Some other terminals, like urxvt, Hyper terminal, ...
            (mouse_button, mouse_event_type, mouse_modifiers) = urxvt_mouse_events.get(
                mouse_event, (UNKNOWN_BUTTON, MOUSE_MOVE, UNKNOWN_MODIFIER)
            )

    x -= 1
    y -= 1

    return MouseEvent(
        position=Point(x=x, y=y),
        event_type=mouse_event_type,
        button=mouse_button,
        modifiers=mouse_modifiers,
        cell_position=RelativePosition(rx, ry),
    )


_MOUSE_EVENT_CACHE: FastDictCache[
    tuple[str, bool, tuple[int, int]], MouseEvent | None
] = FastDictCache(get_value=_parse_mouse_data)


def load_mouse_bindings() -> KeyBindings:
    """Additional key-bindings to deal with SGR-pixel mouse positioning."""
    key_bindings = load_ptk_mouse_bindings()

    @key_bindings.add(Keys.Vt100MouseEvent, eager=True)
    def _(event: KeyPressEvent) -> NotImplementedOrNone:
        """Handle incoming mouse event, include SGR-pixel mode."""
        # Ensure mypy knows this would only run in a euporie appo
        app = event.app
        assert isinstance(app, BaseApp)

        if not app.renderer.height_is_known:
            return NotImplemented

        mouse_event = _MOUSE_EVENT_CACHE[
            event.data, app.term_sgr_pixel, app.cell_size_px
        ]

        if mouse_event is None:
            return NotImplemented

        # Only handle mouse events when we know the window height.
        if mouse_event.event_type is not None:
            # Take region above the layout into account. The reported
            # coordinates are absolute to the visible part of the terminal.
            x, y = mouse_event.position

            # Adjust position to take into account space above non-full screen apps
            try:
                rows_above = app.renderer.rows_above_layout
            except HeightIsUnknownError:
                return NotImplemented
            else:
                y -= rows_above

            # Save mouse position within the app
            app.mouse_position = Point(x=x, y=y)

            # Apply limits to mouse position if enabled
            if (mouse_limits := app.mouse_limits) is not None:
                x = max(
                    mouse_limits.xpos,
                    min(x, mouse_limits.xpos + (mouse_limits.width) - 1),
                )
                y = max(
                    mouse_limits.ypos,
                    min(y, mouse_limits.ypos + (mouse_limits.height) - 1),
                )

            # Do not modify the mouse event in the cache, instead create a new instance
            mouse_event = MouseEvent(
                position=Point(x=x, y=y),
                event_type=mouse_event.event_type,
                button=mouse_event.button,
                modifiers=mouse_event.modifiers,
                cell_position=mouse_event.cell_position,
            )

            # Call the mouse handler from the renderer.
            # Note: This can return `NotImplemented` if no mouse handler was
            #       found for this position, or if no repainting needs to
            #       happen. this way, we avoid excessive repaints during mouse
            #       movements.
            handler = app.renderer.mouse_handlers.mouse_handlers[y][x]

            return handler(mouse_event)

        return NotImplemented

    return key_bindings
