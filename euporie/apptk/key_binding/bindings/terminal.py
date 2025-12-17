"""Contains key handlers for terminal queries."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.key_binding.key_bindings import KeyBindings

from euporie.apptk.key_binding.key_processor import KeyPressEvent

if TYPE_CHECKING:
    from euporie.apptk.key_binding.key_bindings import NotImplementedOrNone

    from euporie.apptk.key_binding import KeyBindingsBase, KeyPressEvent

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
    "4;7": "ansiwhite",
    "4;8": "ansirbightblack",
    "4;9": "ansirbightred",
    "4;10": "ansirbightgreen",
    "4;11": "ansirbightyellow",
    "4;12": "ansirbightblue",
    "4;13": "ansirbightpurple",
    "4;14": "ansirbightcyan",
    "4;15": "ansirbightwhite",
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


def load_terminal_bindings() -> KeyBindingsBase:
    """Load key-bindings for terminal query responses."""
    key_bindings = KeyBindings()

    @key_bindings.add("<palette-dsr-response>", is_global=True)
    def _set_terminal_palette(event: KeyPressEvent) -> NotImplementedOrNone:
        event.app.output.ask_for_colors()
        return NotImplemented

    @key_bindings.add("<colors-response>", is_global=True)
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
            app = event.app
            app.renderer.colors[_COLOR_NAMES.get(c, c)] = f"#{r[:2]}{g[:2]}{b[:2]}"
            app.update_style()
            return None
        return NotImplemented

    @key_bindings.add("<pixel-size-response>", is_global=True)
    def _set_terminal_pixel_size(event: KeyPressEvent) -> NotImplementedOrNone:
        """Run when the terminal receives a pixel dimension query response."""
        if (
            (values := _get_match(event))
            and (x := values.get("x"))
            and (y := values.get("y"))
        ):
            event.app.output.set_pixel_size(int(x), int(y))
        return NotImplemented

    @key_bindings.add("<kitty-graphics-status-response>", is_global=True)
    def _set_terminal_graphics_kitty(event: KeyPressEvent) -> NotImplementedOrNone:
        """Run when the terminal receives a kitty graphics support query response."""
        if (values := _get_match(event)) and values.get("status") == "OK":
            event.app.renderer.graphics_kitty = True
        return NotImplemented

    @key_bindings.add("<device-attributes-response>", is_global=True)
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

    @key_bindings.add("<iterm-graphics-status-response>", is_global=True)
    def _set_terminal_graphics_iterm(event: KeyPressEvent) -> NotImplementedOrNone:
        """Run when the terminal receives a iterm graphics support query response."""
        if (
            (values := _get_match(event))
            and (term := values.get("term"))
            and term.startswith(("WezTerm", "Konsole", "mlterm"))
        ):
            event.app.renderer.graphics_iterm = True
        return NotImplemented

    @key_bindings.add("<sgr-pixel-status-response>", is_global=True)
    def _set_terminal_sgr_pixel(event: KeyPressEvent) -> NotImplementedOrNone:
        """Run when the terminal receives a SGR-pixel mode support query response."""
        if (values := _get_match(event)) and (values.get("Pm") in {"1", "3"}):
            event.app.renderer.sgr_pixel = True
        return NotImplemented

    @key_bindings.add("<clipboard-data-response>", is_global=True)
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

    return key_bindings
