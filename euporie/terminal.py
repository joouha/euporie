"""Contains classes related to querying terminal feautres."""

from __future__ import annotations

import array
import logging
import os
import re
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from aenum import extend_enum  # type: ignore
from prompt_toolkit.input import vt100_parser
from prompt_toolkit.keys import Keys
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.utils import Event

from euporie.commands.registry import add
from euporie.config import config
from euporie.filters import in_tmux

if TYPE_CHECKING:
    from typing import Any, Optional, Type, Union

    from prompt_toolkit.input import Input
    from prompt_toolkit.input.vt100 import Vt100Input
    from prompt_toolkit.key_binding import KeyPressEvent
    from prompt_toolkit.output import Output

log = logging.getLogger(__name__)

_response_prefix_re = re.compile(
    r"""^\x1b(
        \][^\\\x07]*  # Operating System Commands
        |
        _[^\\]*  # Application Program Command
        |
        \[\?[\d;]*  # Primary device attribute responses
    )\Z""",
    re.VERBOSE,
)


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


class _IsPrefixOfLongerMatchCache(vt100_parser._IsPrefixOfLongerMatchCache):
    def __missing__(self, prefix: "str") -> "bool":
        """Check if the response might match an OSC or APC code, or DA response."""
        result = super().__missing__(prefix)
        if not result:
            if _response_prefix_re.match(prefix):
                result = True
                self[prefix] = result
        return result


# Monkey patch the prefix cache
vt100_parser._IS_PREFIX_OF_LONGER_MATCH_CACHE = _IsPrefixOfLongerMatchCache()


class Vt100Parser(vt100_parser.Vt100Parser):
    """A Vt100Parser which checks input against additional key patterns."""

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Create a new VT100 parser."""
        super().__init__(*args, **kwargs)
        self.queries: "dict[Keys, re.Pattern]" = {}

    def _get_match(self, prefix: "str") -> "Union[None, Keys, tuple[Keys, ...]]":
        """Checks for additional key matches first."""
        for key, pattern in self.queries.items():
            if pattern.match(prefix):
                return key

        return super()._get_match(prefix)


def tmuxify(cmd: "str") -> "str":
    """Wraps an escape sequence for tmux passthrough."""
    if in_tmux() and config.tmux_graphics:
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

    def __init__(self, output: "Output") -> "None":
        """Create a new instance of the terminal query."""
        self.output = output
        self.waiting = False
        self._value: "Optional[Any]" = None
        self.event = Event(self)
        if self.output.stdout and not self.output.stdout.isatty():
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

    def send(self) -> "None":
        """Sends the terminal query command to the output."""
        if self.cmd and not self.waiting:
            log.debug("Sending query %s", self.cmd.__repr__())
            self.output.write_raw(self.cmd)
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


class ForegroundColor(ColorQueryMixin, TerminalQuery):
    """A terminal query to check the terminal's foreground colour."""

    default = "#FFFFFF"
    cache = True
    cmd = "\x1b]11;?\x1b\\"
    pattern = re.compile(
        r"^\x1b\]10;rgb:"
        "(?P<r>[0-9A-Fa-f]{2,4})/"
        "(?P<g>[0-9A-Fa-f]{2,4})/"
        "(?P<b>[0-9A-Fa-f]{2,4})"
        r"\x1b\\\Z"
    )


class BackgroundColor(ColorQueryMixin, TerminalQuery):
    """A terminal query to check the terminal's background colour."""

    default = "#000000"
    cache = True
    cmd = "\x1b]10;?\x1b\\"
    pattern = re.compile(
        r"^\x1b\]11;rgb:"
        "(?P<r>[0-9A-Fa-f]{2,4})/"
        "(?P<g>[0-9A-Fa-f]{2,4})/"
        "(?P<b>[0-9A-Fa-f]{2,4})"
        r"\x1b\\\Z"
    )


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
    cmd = tmuxify(
        "\x1b_Gi=4294967295,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\"  # + "\x1b[1K" + "\x1b[1G"
    )
    pattern = re.compile(r"^\x1b_Gi=4294967295;(?P<status>OK)\x1b\\\Z")

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
    cmd = tmuxify("\x1b[c")
    pattern = re.compile(r"^\x1b\[\?(?:\d+;)*(?P<sixel>4)(?:;\d+)*c\Z")

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

    def __init__(self, output: "Output") -> "None":
        """Detect the iTerm graphics support based on environment variables."""
        self._value = None
        if (
            os.environ.get("TERM_PROGRAM", "") in {"WezTerm", "iTerm.app"}
            or os.environ.get("MLTERM") is not None
        ):
            self._value = True


class DepthOfColor(TerminalQuery):
    """Determines the suspected color depth of the terminal."""

    # TODO - detect 24bit color support with escape sequence
    # "\x1b[48:2:1:2:3m\eP$qm\x1b\\"

    default = ColorDepth.DEPTH_24_BIT

    def __init__(self, output: "Output") -> "None":
        """Detect the terminal's colour support based on environment variables."""
        self._value: "Optional[ColorDepth]" = None
        if os.environ.get("NO_COLOR", ""):
            self._value = ColorDepth.DEPTH_1_BIT
            return
        colorterm = os.environ.get("COLORTERM", "")
        if "truecolor" in colorterm or "24bit" in colorterm:
            self._value = ColorDepth.DEPTH_24_BIT
            return
        if "256" in os.environ.get("TERM", ""):
            self._value = ColorDepth.DEPTH_8_BIT
            return


class TerminalInfo:
    """A class to gather and hold information about the terminal."""

    input: "Input"
    output: "Output"

    def __init__(self, input_: "Input", output: "Output") -> "None":
        """Instantiates the terminal information class."""
        self.input = input_
        self.output = output
        self._queries: "list[TerminalQuery]" = []

        self.foreground_color = self.register(ForegroundColor)
        self.background_color = self.register(BackgroundColor)
        self.pixel_dimensions = self.register(PixelDimensions)
        self.sixel_graphics_status = self.register(SixelGraphicsStatus)
        self.kitty_graphics_status = self.register(KittyGraphicsStatus)
        self.iterm_graphics_status = self.register(ItermGraphicsStatus)
        self.depth_of_color = self.register(DepthOfColor)

    def register(self, query: "Type[TerminalQuery]") -> "TerminalQuery":
        """Instantiates and registers a query's response with the input parser."""
        # Create an instance of this query
        query_inst = query(self.output)
        self._queries.append(query_inst)

        # If the query expects a response from the terminal, we need to add a
        # key-binding for it and register it with the input parser
        if query.pattern:
            name = re.sub(r"(?<!^)(?=[A-Z])", "-", query.__name__).lower()
            title = name.replace("-", " ")

            # Add a "key" definition for this query
            key_name = f"{query.__name__}Response"
            key_code = f"<{name}-response>"
            extend_enum(Keys, key_name, key_code)
            key = getattr(Keys, key_name)

            # Register this key with the parser
            if hasattr(self.input, "vt100_parser"):
                # Ensure mypy knows the current types
                self.input = cast("Vt100Input", self.input)
                self.input.vt100_parser = cast("Vt100Parser", self.input.vt100_parser)
                # Register the key
                self.input.vt100_parser.queries[key] = query.pattern

            # Add a command for the query's key-binding
            add(
                name=name,
                title=f"Set terminal {title}",
                hidden=True,
                description=f"Sets the terminal's {title} value.",
                group="terminal",
                keys=[key],
            )(query_inst._handle_response)

        return query_inst

    def send_all(self) -> "None":
        """Sends the command for all queries."""
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
        _rows, _cols, px, py = self._tiocgwnsz()
        # If unsuccessful, try requesting info with escape code method
        if px == 0:
            px, py = self.pixel_dimensions.value
        return px, py

    @property
    def cell_size_px(self) -> "tuple[int, int]":
        """Get the pixel size of a single terminal cell."""
        px, py = self.terminal_size_px
        rows, cols = self.output.get_size()
        # If we can't get the pixel size, just guess wildly
        return px // cols or 10, py // rows or 20
