"""Key bindings to deal with pixel mouse positioning."""

import logging
from typing import TYPE_CHECKING, FrozenSet, NamedTuple

from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding.bindings.mouse import (
    MOUSE_MOVE,
    UNKNOWN_BUTTON,
    UNKNOWN_MODIFIER,
    KeyBindings,
)
from prompt_toolkit.key_binding.bindings.mouse import (
    load_mouse_bindings as load_ptk_mouse_bindings,
)
from prompt_toolkit.key_binding.bindings.mouse import (
    typical_mouse_events,
    urxvt_mouse_events,
    xterm_sgr_mouse_events,
)
from prompt_toolkit.keys import Keys
from prompt_toolkit.mouse_events import MouseButton
from prompt_toolkit.mouse_events import MouseEvent as PtkMouseEvent
from prompt_toolkit.mouse_events import MouseEventType, MouseModifier

from euporie.core.app import BaseApp

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

log = logging.getLogger(__name__)


class RelativePosition(NamedTuple):
    """Stores the relative position or the mouse within a terminal cell."""

    x: float
    y: float


class MouseEvent(PtkMouseEvent):
    """Mouse event, which also store relative position of the mouse event in a cell."""

    def __init__(
        self,
        position: "Point",
        event_type: "MouseEventType",
        button: "MouseButton",
        modifiers: "FrozenSet[MouseModifier]",
        cell_position: "Optional[RelativePosition]",
    ) -> "None":
        """Create new event instance."""
        super().__init__(
            position=position,
            event_type=event_type,
            button=button,
            modifiers=modifiers,
        )
        self.cell_position = cell_position or RelativePosition(0.5, 0.5)


def load_mouse_bindings() -> "KeyBindings":
    """Additional key-bindings to deal with SGR-pixel mouse positioning."""
    key_bindings = load_ptk_mouse_bindings()

    @key_bindings.add(Keys.Vt100MouseEvent)
    def _(event: "KeyPressEvent") -> "NotImplementedOrNone":
        """Handling of incoming mouse event, include SGR-pixel mode."""
        # Ensure mypy knows this would only run in a euporie app
        assert isinstance(event.app, BaseApp)

        rx = ry = 0.5

        # Parse incoming packet.
        if event.data[2] == "M":
            # Typical.
            mouse_event, x, y = map(ord, event.data[3:])

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
            data = event.data[2:]
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

                if event.app.term_info.sgr_pixel_status.value:

                    # Calculate cell position
                    cell_px, cell_py = event.app.term_info.cell_size_px
                    px, py = x, y
                    fx, fy = px / cell_px + 1, py / cell_py + 1
                    x, y = int(fx), int(fy)
                    rx, ry = fx - x, fy - y

                try:
                    (
                        mouse_button,
                        mouse_event_type,
                        mouse_modifiers,
                    ) = xterm_sgr_mouse_events[mouse_event, m]
                except KeyError:
                    return NotImplemented

            else:
                # Some other terminals, like urxvt, Hyper terminal, ...
                (
                    mouse_button,
                    mouse_event_type,
                    mouse_modifiers,
                ) = urxvt_mouse_events.get(
                    mouse_event, (UNKNOWN_BUTTON, MOUSE_MOVE, UNKNOWN_MODIFIER)
                )

        x -= 1
        y -= 1

        # Only handle mouse events when we know the window height.
        if event.app.renderer.height_is_known and mouse_event_type is not None:
            # Take region above the layout into account. The reported
            # coordinates are absolute to the visible part of the terminal.
            from prompt_toolkit.renderer import HeightIsUnknownError

            try:
                y -= event.app.renderer.rows_above_layout
            except HeightIsUnknownError:
                return NotImplemented

            # Save global mouse position
            event.app.mouse_position = Point(x=x, y=y)

            # Apply limits to mouse position if enabled
            if (mouse_limits := event.app.mouse_limits) is not None:
                x = max(
                    mouse_limits.xpos,
                    min(x, mouse_limits.xpos + mouse_limits.width),
                )
                y = max(
                    mouse_limits.ypos,
                    min(y, mouse_limits.ypos + mouse_limits.height),
                )

            # Call the mouse handler from the renderer.
            # Note: This can return `NotImplemented` if no mouse handler was
            #       found for this position, or if no repainting needs to
            #       happen. this way, we avoid excessive repaints during mouse
            #       movements.
            handler = event.app.renderer.mouse_handlers.mouse_handlers[y][x]

            return handler(
                MouseEvent(
                    position=Point(x=x, y=y),
                    event_type=mouse_event_type,
                    button=mouse_button,
                    modifiers=mouse_modifiers,
                    cell_position=RelativePosition(rx, ry),
                )
            )

        return NotImplemented

    return key_bindings
