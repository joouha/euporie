"""Contains key handlers for terminal queries."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.commands import add_cmd
from euporie.apptk.key_binding.key_bindings import KeyBindings
from euporie.apptk.key_binding.key_processor import KeyPressEvent
from euporie.apptk.output.vt100 import ANSI_COLORS_TO_RGB, TERMINAL_COLORS_TO_RGB

if TYPE_CHECKING:
    from euporie.apptk.key_binding import KeyBindingsBase, KeyPressEvent
    from euporie.apptk.key_binding.key_bindings import NotImplementedOrNone

__all__ = ["load_terminal_bindings"]

log = logging.getLogger(__name__)

_COLOR_NAMES: dict[str, str] = {
    "10": "fg",
    "11": "bg",
    "4;0": "ansiblack",
    "4;1": "ansired",
    "4;2": "ansigreen",
    "4;3": "ansiyellow",
    "4;4": "ansiblue",
    "4;5": "ansipurple",
    "4;6": "ansicyan",
    "4;7": "ansigray",
    "4;8": "ansibightblack",
    "4;9": "ansibightred",
    "4;10": "ansibightgreen",
    "4;11": "ansibightyellow",
    "4;12": "ansibightblue",
    "4;13": "ansibightpurple",
    "4;14": "ansibightcyan",
    "4;15": "ansiwhite",
}


def _get_match(event: KeyPressEvent) -> dict[str, str] | None:
    """Get pattern matches from a key press event."""
    if (
        (parser := getattr(event.app.input, "vt100_parser", None))
        and (patterns := getattr(parser, "patterns", None))
        and (pattern := patterns.get(event.key_sequence[-1].key))
        and (match := pattern.match(event.data))
        and (values := match.groupdict())
    ):
        return values
    return None


@add_cmd(keys=["<palette-dsr-response>"], is_global=True, hidden=True)
def _set_terminal_palette(event: KeyPressEvent) -> NotImplementedOrNone:
    event.app.output.ask_for_colors()
    return NotImplemented


@add_cmd(keys=["<colors-response>"], is_global=True, hidden=True)
def _set_terminal_color(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a terminal color query response.

    Args:
        event: The key press event received when the termina sends a response

    Returns:
        :py:obj:`NotImplemented`, so the application is not invalidated when a
        response from the terminal is received

    """
    if colors := _get_match(event):
        c = colors["c"]
        r, g, b = (
            colors.get("r", "00"),
            colors.get("g", "00"),
            colors.get("b", "00"),
        )
        name = _COLOR_NAMES.get(c, c)
        rgb = (int(r[:2], 16), int(g[:2], 16), int(b[:2], 16))
        if name in TERMINAL_COLORS_TO_RGB:
            TERMINAL_COLORS_TO_RGB[name] = rgb
            event.app.on_color_change()
            return None
        elif name in ANSI_COLORS_TO_RGB:
            ANSI_COLORS_TO_RGB[name] = rgb
            event.app.on_color_change()
            return None
    return NotImplemented


@add_cmd(keys=["<pixel-size-response>"], is_global=True, hidden=True)
def _set_terminal_pixel_size(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a pixel dimension query response."""
    if (
        (values := _get_match(event))
        and (x := values.get("x"))
        and (y := values.get("y"))
    ):
        event.app.output.set_pixel_size(int(x), int(y))
    return NotImplemented


@add_cmd(keys=["<kitty-graphics-status-response>"], is_global=True, hidden=True)
def _set_terminal_graphics_kitty(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a kitty graphics support query response."""
    if (values := _get_match(event)) and values.get("status") == "OK":
        event.app.renderer.graphics_kitty = True
    return NotImplemented


@add_cmd(keys=["<device-attributes-response>"], is_global=True, hidden=True)
def _set_terminal_device_attributes(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a device attributes query response."""
    if (values := _get_match(event)) and (attrs_str := values.get("attrs")):
        attrs = {attr for attr in attrs_str.split(";") if attr}
        app = event.app
        if "4" in attrs:
            app.renderer.graphics_sixel = True
        if "52" in attrs:
            app.renderer.osc52_clipboard = True
    return NotImplemented


@add_cmd(keys=["<iterm-graphics-status-response>"], is_global=True, hidden=True)
def _set_terminal_graphics_iterm(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a iterm graphics support query response."""
    if (
        (values := _get_match(event))
        and (term := values.get("term"))
        and term.startswith(("WezTerm", "Konsole", "mlterm"))
    ):
        event.app.renderer.graphics_iterm = True
    return NotImplemented


@add_cmd(keys=["<sgr-pixel-status-response>"], is_global=True, hidden=True)
def _set_terminal_sgr_pixel(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a SGR-pixel mode support query response."""
    if (values := _get_match(event)) and (values.get("Pm") in {"1", "3"}):
        event.app.renderer.sgr_pixel = True
    return NotImplemented


@add_cmd(keys=["<clipboard-data-response>"], is_global=True, hidden=True)
def _set_terminal_clipboard_data(event: KeyPressEvent) -> NotImplementedOrNone:
    """Run when the terminal receives a clipboard data query response."""
    from base64 import b64decode

    from euporie.apptk.clipboard.osc52 import Osc52Clipboard

    app = event.app
    if isinstance(clipboard := app.clipboard, Osc52Clipboard) and (
        values := _get_match(event)
    ):
        value = values.get("data", "")
        text = b64decode(value).decode()
        log.warning(repr(text))
        clipboard.sync(text)
    return NotImplemented


def load_terminal_bindings() -> KeyBindingsBase:
    """Load key-bindings for terminal query responses."""
    return KeyBindings.from_commands(
        (
            "set-terminal-palette",
            "set-terminal-color",
            "set-terminal-pixel-size",
            "set-terminal-graphics-kitty",
            "set-terminal-device-attributes",
            "set-terminal-graphics-iterm",
            "set-terminal-sgr-pixel",
            "set-terminal-clipboard-data",
        )
    )
