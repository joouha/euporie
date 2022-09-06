"""Contains classes related to querying terminal feautres."""

from __future__ import annotations

import array
import logging
import os
import re
from functools import lru_cache
from typing import TYPE_CHECKING

from aenum import extend_enum
from prompt_toolkit.keys import Keys
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.utils import Event

from euporie.core.commands import add_cmd
from euporie.core.filters import in_tmux
from euporie.core.key_binding.registry import register_bindings
from euporie.core.style import DEFAULT_COLORS

if TYPE_CHECKING:
    from typing import Any, Optional, Type

    from prompt_toolkit.input import Input
    from prompt_toolkit.key_binding import KeyPressEvent
    from prompt_toolkit.output import Output

    from euporie.core.config import Config

log = logging.getLogger(__name__)


@lru_cache
def _have_termios_tty_fcntl() -> "bool":
    try:
        import fcntl  # noqa F401
        import termios  # noqa F401
        import tty  # noqa F401
    except ModuleNotFoundError:
        return False
    else:
        return True


def tmuxify(cmd: "str") -> "str":
    """Wraps an escape sequence for tmux passthrough."""
    if in_tmux():
        cmd = cmd.replace("\x1b", "\x1b\x1b")
        cmd = f"\x1bPtmux;{cmd}\033\\"
    return cmd


class TerminalQuery:
    """A class representing a terminal query.

    This allows a control sequence to sent to the terminal, the response interpreted,
    and the received value processed and stored.
    """

    default: "Optional[Any]" = None
    cache = False
    cmd = ""
    pattern: "Optional[re.Pattern]" = None

    def __init__(self, output: "Output", config: "Config") -> "None":
        """Create a new instance of the terminal query."""
        self.config = config
        self.output = output
        self.waiting = False
        self._value: "Optional[Any]" = None
        self.event = Event(self)
        self.queryable = self.output.stdout and (
            self.output.stdout.isatty()
            # Don't send escape codes if this is not a real TTY.
            # We create pseudo-ttys to get colored output, but don't want
            # any terminal queries to be sent
            and not getattr(self.output.stdout, "fake_tty", False)
        )
        if not self.queryable:
            self.cmd = ""

    def verify(self, data: "str") -> "Optional[Any]":
        """Verifies the response from the terminal."""
        return None

    async def _handle_response(self, event: "KeyPressEvent") -> "object":
        """Run when the terminal receives the response from the terminal.

        Args:
            event: The key press event received when the termina sends a response

        Returns:
            :py:obj:`NotImplemented`, so the application is not invalidated when a
            response from the terminal is received

        """
        log.debug("Got terminal response for '%s'", self.__class__.__name__)
        self.waiting = False
        new_value = self.verify(event.data)
        # Only fire the event if the value has changed
        if self._value != new_value:
            self._value = new_value
            self.event.fire()
        return NotImplemented

    def _cmd(self) -> "str":
        """Return the query's command."""
        return self.cmd

    def send(self) -> "None":
        """Sends the terminal query command to the output."""
        if self.queryable and self.cmd and not self.waiting:
            cmd = self._cmd()
            log.debug(
                "Sending query %s for %s",
                cmd.__repr__(),
                self.__class__.__name__,
            )
            self.output.write_raw(cmd)
            self.output.flush()
            self.waiting = True

    @property
    def value(self) -> "Any":
        """Returns the last known value for the query.

        Returns:
            The last value received, or the default value.

        """
        return self._value or self.default


class ColorQueryMixin:
    """A mixin for terminal queries which check a terminal colour."""

    pattern: "re.Pattern"

    def verify(self, data: "str") -> "Optional[str]":
        """Verifies the response contains a colour."""
        if match := self.pattern.match(data):
            if colors := match.groupdict():
                r, g, b = (
                    colors.get("r", "00"),
                    colors.get("g", "00"),
                    colors.get("b", "00"),
                )
                return f"#{r[:2]}{g[:2]}{b[:2]}"
        return None


class Colors(TerminalQuery):
    """A terminal query to retrieve colours as hex codes."""

    _color_names = {
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
    default = DEFAULT_COLORS
    cache = True
    cmd = ("\x1b]10;?\x1b\\" "\x1b]11;?\x1b\\") + "".join(
        f"\x1b]4;{i};?\x1b\\" for i in range(16)
    )
    pattern = re.compile(
        r"^\x1b\](?P<c>(\d+;)?\d+)+;rgb:"
        r"(?P<r>[0-9A-Fa-f]{2,4})\/"
        r"(?P<g>[0-9A-Fa-f]{2,4})\/"
        r"(?P<b>[0-9A-Fa-f]{2,4})"
        # Allow BEL or ST as terminator
        r"(\x1b\\\Z|\0x7)"
    )

    def _cmd(self) -> "str":
        return tmuxify(self.cmd)

    def verify(self, data: "str") -> "dict[str, str]":
        """Verifies the response contains a colour."""
        if match := self.pattern.match(data):
            if colors := match.groupdict():
                c = colors["c"]
                r, g, b = (
                    colors.get("r", "00"),
                    colors.get("g", "00"),
                    colors.get("b", "00"),
                )
                output = {
                    **self.value,
                    self._color_names.get(c, c): f"#{r[:2]}{g[:2]}{b[:2]}",
                }
                return output
        return self.value


class PixelDimensions(TerminalQuery):
    """A terminal query to check the terminal's dimensions in pixels."""

    default = (0, 0)
    cmd = "\x1b[14t"
    cache = True
    pattern = re.compile(r"^\x1b\[4;(?P<y>\d+);(?P<x>\d+)t\Z")

    def verify(self, data: "str") -> "Optional[tuple[int, int]]":
        """Verifies the terminal responded with pixel dimensions."""
        if match := self.pattern.match(data):
            if values := match.groupdict():
                if (x := values.get("x")) is not None and (
                    y := values.get("y")
                ) is not None:
                    return int(x), int(y)
        return None


class KittyGraphicsStatus(TerminalQuery):
    """A terminal query to check for kitty graphics support."""

    default = False
    cache = True
    cmd = "\x1b[s\x1b_Gi=4294967295,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\\x1b[u\x1b[2K"
    # Konsole responds with 'i=0' - I'll allow it
    pattern = re.compile(r"^\x1b_Gi=(4294967295|0);(?P<status>OK)\x1b\\\Z")

    def _cmd(self) -> "str":
        if self.config.tmux_graphics:
            return tmuxify(self.cmd)
        else:
            return self.cmd

    def verify(self, data: "str") -> "bool":
        """Verifies the terminal response means kitty graphics are supported."""
        if match := self.pattern.match(data):
            if values := match.groupdict():
                if values.get("status") == "OK":
                    return True
        return False


class SixelGraphicsStatus(TerminalQuery):
    """A terminal query to check for sixel graphics support."""

    default = False
    cache = True
    cmd = "\x1b[c"
    pattern = re.compile(r"^\x1b\[\?(?:\d+;)*(?P<sixel>4)(?:;\d+)*c\Z")

    def _cmd(self) -> "str":
        if self.config.tmux_graphics:
            return tmuxify(self.cmd)
        else:
            return self.cmd

    def verify(self, data: "str") -> "bool":
        """Verifies the terminal response means sixel graphics are supported."""
        if match := self.pattern.match(data):
            if values := match.groupdict():
                if values.get("sixel"):
                    return True
        return False


class ItermGraphicsStatus(TerminalQuery):
    """A terminal query to check for iTerm graphics support."""

    default = False
    cache = True

    def __init__(self, output: "Output", config: "Config") -> "None":
        """Detect the iTerm graphics support based on environment variables."""
        super().__init__(output, config)
        self._value = None
        if (
            os.environ.get("TERM_PROGRAM", "") in {"WezTerm", "iTerm.app"}
            or os.environ.get("MLTERM") is not None
            or (
                os.environ.get("KONSOLE_DBUS_WINDOW") is not None
                and int(os.environ.get("KONSOLE_VERSION", 0)) > 220370
            )
        ) and self.queryable:
            self._value = True


class DepthOfColor(TerminalQuery):
    """Determines the suspected color depth of the terminal."""

    # TODO - detect 24bit color support with escape sequence
    # "\x1b[48:2:1:2:3m\eP$qm\x1b\\"

    default = ColorDepth.DEPTH_24_BIT

    def __init__(self, output: "Output", config: "Config") -> "None":
        """Detect the terminal's colour support based on environment variables."""
        super().__init__(output, config)
        self._value: "Optional[ColorDepth]" = None
        if os.environ.get("NO_COLOR", "") or os.environ.get("TERM", "") == "dumb":
            self._value = ColorDepth.DEPTH_1_BIT
            return
        colorterm = os.environ.get("COLORTERM", "")
        if "truecolor" in colorterm or "24bit" in colorterm:
            self._value = ColorDepth.DEPTH_24_BIT
            return
        if "256" in os.environ.get("TERM", ""):
            self._value = ColorDepth.DEPTH_8_BIT
            return


class SgrPixelStatus(TerminalQuery):
    """A terminal query to check for Pixel SGR support."""

    default = False
    cache = True
    cmd = "\x1b[?1016$p"
    pattern = re.compile(r"^\x1b\[\?1016;(?P<Pm>\d)\$\Z")

    def verify(self, data: "str") -> "bool":
        """Verifies the terminal response means sixel graphics are supported."""
        if match := self.pattern.match(data):
            if values := match.groupdict():
                if values.get("Pm") != 0:
                    return True
        return False


class TerminalInfo:
    """A class to gather and hold information about the terminal."""

    input: "Input"
    output: "Output"

    def __init__(self, input_: "Input", output: "Output", config: "Config") -> "None":
        """Instantiates the terminal information class."""
        self.input = input_
        self.output = output
        self.config = config
        self._queries: "list[TerminalQuery]" = []

        self.colors = self.register(Colors)
        self.pixel_dimensions = self.register(PixelDimensions)
        self.sixel_graphics_status = self.register(SixelGraphicsStatus)
        self.kitty_graphics_status = self.register(KittyGraphicsStatus)
        self.iterm_graphics_status = self.register(ItermGraphicsStatus)
        self.depth_of_color = self.register(DepthOfColor)
        self.sgr_pixel_status = self.register(SgrPixelStatus)

    def register(self, query: "Type[TerminalQuery]") -> "TerminalQuery":
        """Instantiates and registers a query's response with the input parser."""
        # Create an instance of this query
        query_inst = query(self.output, config=self.config)
        self._queries.append(query_inst)

        # If the query expects a response from the terminal, we need to add a
        # key-binding for it and register it with the input parser
        if query.pattern:
            name = re.sub(r"(?<!^)(?=[A-Z])", "-", query.__name__).lower()
            title = name.replace("-", " ")

            # Add a "key" definition for this query
            key_name = f"{query.__name__}Response"
            key_code = f"<{name}-response>"
            # Do not register the same key multiple times
            if not hasattr(Keys, key_name):
                extend_enum(Keys, key_name, key_code)
            key = getattr(Keys, key_name)

            # Register this key with the parser if supported
            if parser := getattr(self.input, "vt100_parser", None):
                # Register the key
                parser.queries[key] = query.pattern

            # Add a command for the query's key-binding
            add_cmd(
                name=name,
                title=f"Set terminal {title}",
                hidden=True,
                description=f"Sets the terminal's {title} value.",
            )(query_inst._handle_response)
            # Add key-binding
            register_bindings({"euporie.core.app.BaseApp": {name: key}})

        return query_inst

    def send_all(self) -> "None":
        """Sends the command for all queries."""
        # Ensure line wrapping is off before sending queries
        self.output.disable_autowrap()
        for query in self._queries:
            query.send()

    def _tiocgwnsz(self) -> "tuple[int, int, int, int]":
        """Get the size and pixel dimensions of the terminal with `termios`."""
        output = array.array("H", [0, 0, 0, 0])
        if _have_termios_tty_fcntl():
            import fcntl
            import termios

            try:
                fcntl.ioctl(1, termios.TIOCGWINSZ, output)
            except Exception:  # noqa S110
                pass
        rows, cols, xpixels, ypixels = output
        return rows, cols, xpixels, ypixels

    @property
    def terminal_size_px(self) -> "tuple[int, int]":
        """Get the pixel dimensions of the terminal."""
        # Prefer using escape codes as this works over SSH
        px, py = self.pixel_dimensions.value
        if px == 0:
            # If unsuccessful, try requesting info with tiocgwnsz
            _rows, _cols, px, py = self._tiocgwnsz()
        return px, py

    @property
    def cell_size_px(self) -> "tuple[int, int]":
        """Get the pixel size of a single terminal cell."""
        px, py = self.terminal_size_px
        rows, cols = self.output.get_size()
        # If we can't get the pixel size, just guess wildly
        return px // cols or 10, py // rows or 20
