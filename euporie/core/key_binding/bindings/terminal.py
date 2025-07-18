"""Contains key handlers for terminal queries."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.core.commands import add_cmd
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase, KeyPressEvent

    from euporie.core.config import Config

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


def get_match(event: KeyPressEvent) -> dict[str, str] | None:
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


@add_cmd(hidden=True, is_global=True)
def _set_terminal_palette(event: KeyPressEvent) -> object:
    from euporie.core.io import Vt100_Output

    if isinstance(output := event.app.output, Vt100_Output):
        output.get_colors()
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_color(event: KeyPressEvent) -> object:
    """Run when the terminal receives a terminal color query response.

    Args:
        event: The key press event received when the termina sends a response

    Returns:
        :py:obj:`NotImplemented`, so the application is not invalidated when a
        response from the terminal is received

    """
    from euporie.core.app.app import BaseApp

    if isinstance(app := event.app, BaseApp) and (colors := get_match(event)):
        c = colors["c"]
        r, g, b = colors.get("r", "00"), colors.get("g", "00"), colors.get("b", "00")
        app.term_colors[_COLOR_NAMES.get(c, c)] = f"#{r[:2]}{g[:2]}{b[:2]}"
        app.update_style()
        return None
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_pixel_size(event: KeyPressEvent) -> object:
    """Run when the terminal receives a pixel dimension query response."""
    from euporie.core.app.app import BaseApp

    if (
        isinstance(app := event.app, BaseApp)
        and (values := get_match(event))
        and (x := values.get("x"))
        and (y := values.get("y"))
    ):
        app.term_size_px = int(x), int(y)
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_device_attributes(event: KeyPressEvent) -> object:
    """Run when the terminal receives a device attributes query response."""
    from euporie.core.app.app import BaseApp

    if (
        isinstance(app := event.app, BaseApp)
        and (values := get_match(event))
        and (attrs_str := values.get("attrs"))
    ):
        attrs = {attr for attr in attrs_str.split(";") if attr}
        if "4" in attrs:
            app.term_graphics_sixel = True
        if "52" in attrs:
            app.term_osc52_clipboard = True
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_graphics_iterm(event: KeyPressEvent) -> object:
    """Run when the terminal receives a iterm graphics support query response."""
    from euporie.core.app.app import BaseApp

    if (
        isinstance(app := event.app, BaseApp)
        and (values := get_match(event))
        and (term := values.get("term"))
        and term.startswith(("WezTerm", "Konsole", "mlterm"))
    ):
        app.term_graphics_iterm = True
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_graphics_kitty(event: KeyPressEvent) -> object:
    """Run when the terminal receives a kitty graphics support query response."""
    from euporie.core.app.app import BaseApp

    if (
        isinstance(app := event.app, BaseApp)
        and (values := get_match(event))
        and values.get("status") == "OK"
    ):
        app.term_graphics_kitty = True
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_sgr_pixel(event: KeyPressEvent) -> object:
    """Run when the terminal receives a SGR-pixel mode support query response."""
    from euporie.core.app.app import BaseApp

    if (
        isinstance(app := event.app, BaseApp)
        and (values := get_match(event))
        and (values.get("Pm") in {"1", "3"})
    ):
        app.term_sgr_pixel = True
    return NotImplemented


@add_cmd(hidden=True, is_global=True)
def _set_terminal_clipboard_data(event: KeyPressEvent) -> object:
    """Run when the terminal receives a clipboard data query response."""
    from base64 import b64decode

    from euporie.core.app.app import BaseApp
    from euporie.core.clipboard import Osc52Clipboard

    if (
        isinstance(app := event.app, BaseApp)
        and isinstance(clipboard := app.clipboard, Osc52Clipboard)
        and (values := get_match(event))
    ):
        value = values.get("data", "")
        text = b64decode(value).decode()
        log.warning(repr(text))
        clipboard.sync(text)
    return NotImplemented


class TerminalQueries:
    """Key bindings for terminal query responses."""


register_bindings(
    {
        "euporie.core.key_binding.bindings.terminal:TerminalQueries": {
            "set-terminal-palette": "<palette-dsr-response>",
            "set-terminal-color": "<colors-response>",
            "set-terminal-pixel-size": "<pixel-size-response>",
            "set-terminal-graphics-kitty": "<kitty-graphics-status-response>",
            "set-terminal-device-attributes": "<device-attributes-response>",
            "set-terminal-graphics-iterm": "<iterm-graphics-status-response>",
            "set-terminal-sgr-pixel": "<sgr-pixel-status-response>",
            "set-terminal-clipboard-data": "<clipboard-data-response>",
        }
    }
)


def load_terminal_bindings(config: Config | None = None) -> KeyBindingsBase:
    """Load editor key-bindings in the style of the ``micro`` text editor."""
    return load_registered_bindings(
        "euporie.core.key_binding.bindings.terminal:TerminalQueries", config=config
    )
