"""Contains classes related to querying terminal feautres."""

from __future__ import annotations

import array
import asyncio
import logging
import os
import re
import sys
import threading
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from prompt_toolkit.output import ColorDepth, Output

if TYPE_CHECKING:
    from typing import Any, Callable, Optional, TextIO, Union

    from prompt_toolkit.input import Input

__all__ = ["QueryCodes", "QueryResponsePatterns", "TerminalInfo"]

log = logging.getLogger(__name__)

CONTROL_RE = re.compile(
    r"""
\x1b
(?:
 (?P<csi>  # Control Sequence Introducer
  \[
  (?P<csi_params>[0-9:;<=>?]*)
  (?P<csi_inter>[!\"#$%&'()*+,\-./]*)
  (?P<csi_final>[A-Za-z@[\]^_`a–z{|}~])
 )
 |
 (?P<osc>  # Operating System Command
  \]
  (?P<osc_string>.*(?=\x1b\\|\x07))
  (?P<osc_term>\x1b\\|\x07) # Terminated by ST or BEL
 )
 |
 (?P<apc>  # Application Program Command
  _
  (?P<apc_string>.*(?=\x1b\\))
  (?P<apc_term>\x1b\\) # Terminated by ST or BEL
 )
 |
 (?P<fe> # Other Fe escape sequences
  [NOP[\\\]X^_]
 )
)
    """,
    re.VERBOSE,
)


class QueryCodes:
    """Container for terminal query strings."""

    os = "\x1b[5n"
    device_1 = "\x1b[0c"
    device_2 = "\x1b[>0c"
    pixel_dimensions = "\x1b[14t"
    fg_color = "\x1b]10;?\x1b\\"
    bg_color = "\x1b]11;?\x1b\\"
    sixel = "\x1b[c"
    # For some reason, konsole prints APC codes to the screen, so we clear the current
    # line and move the curor to the start after sending a kitty graphics query code,
    # which prevents breaking the display
    kitty = "\x1b_Gi=1,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\" + "\x1b[1K" + "\x1b[1G"
    cursor_position = "\x1b[6n"


class QueryResponsePatterns:
    """Container for terminal query response patterns."""

    os = re.compile(r"\x1b\[0n")
    device_1 = re.compile(r"\x1b\[\?(\d;?)+c")
    device_2 = re.compile(r"\x1b\[\>(\d;?)+c")
    bg_color = re.compile(
        "11;rgb:(?P<r>[0-9A-Fa-f]{2,4})/(?P<g>[0-9A-Fa-f]{2,4})/(?P<b>[0-9A-Fa-f]{2,4})"
    )
    fg_color = re.compile(
        "10;rgb:(?P<r>[0-9A-Fa-f]{2,4})/(?P<g>[0-9A-Fa-f]{2,4})/(?P<b>[0-9A-Fa-f]{2,4})"
    )
    pixel_dimensions = re.compile(r"4;(?P<y>\d+);(?P<x>\d+)")
    sixel = re.compile(r"\d+")
    # kitty = re.compile("\x1b[_Gi=1;OK\x1b[\\")
    cursor_position = re.compile(r"(?P<row>\d+);(?P<col>\d+)")


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


def _tiocgwnsz() -> "tuple[int, int, int, int]":
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


class TerminalInfo:
    """Provides terminal feature properties."""

    def __init__(self, input_: "Input", output: "Output") -> "None":
        """Run when initiating a new terminal query.

        Args:
            input_: The prompt toolkit input to query
            output: The prompt toolkit output to query

        """
        self.input = input_
        self.output = output

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._setup_loop)
        self.thread.daemon = True
        self.thread.start()

    def _setup_loop(self) -> "None":
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def query_terminal(
        self, *args: "Any", **kwargs: "Any"
    ) -> "Optional[dict[str, str]]":
        """Reads the terminal's response to an escape code query."""
        return asyncio.run_coroutine_threadsafe(
            self._query_terminal(*args, **kwargs),
            self.loop,
        ).result()

    async def _query_terminal(
        self,
        query_code: "str",
        stdin: "Optional[Union[Input, TextIO]]" = None,
        stdout: "Optional[Union[Output, TextIO]]" = None,
        sep: "str" = QueryCodes.os,
        sep_rsp: "re.Pattern" = QueryResponsePatterns.os,
    ) -> "Optional[dict[str, str]]":
        """Query the terminal and parse the response.

        An operating status request is used as the deliminator to locate the query
        response string. Most terminals responsd to this. If a terminal does not
        respond (or does not respond quickly), then we will time-out waiting for a
        response.

        Args:
            query_code: The ANSI escape sequence to send to the terminal.
            stdin: IO to use as stdin
            stdout: IO to use as stdout
            sep: The separator code to use
            sep_rsp: The expected response pattern from the separator code

        Returns:
            A parsed escape code response.

        """
        if stdin is None:
            stdin = self.input or sys.stdin
            # stdin = sys.stdin
        if stdout is None:
            stdout = self.output.stdout or sys.stdout

        # import ipdb; ipdb.set_trace()
        # Check for tty in stdout
        if hasattr(stdout, "isatty"):
            # assert isinstance()
            if not stdout.isatty():
                return None

        if _have_termios_tty_fcntl():
            import termios
            import tty

            stdout_write: "Callable"
            if isinstance(stdout, Output):
                stdout_write = cast("Output", stdout).write_raw
            else:
                stdout_write = stdout.write

            # tattr = termios.tcgetattr(stdin)
            # import ipdb; ipdb.set_trace()
            tattr = termios.tcgetattr(stdin)

            output = ""

            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            transport, _ = await self.loop.connect_read_pipe(lambda: protocol, stdin)

            try:
                tty.setcbreak(stdin, termios.TCSANOW)
                stdout_write(sep)
                stdout.flush()

                output_started = False
                query_sent = False

                while True:
                    try:
                        next_byte = await asyncio.wait_for(reader.read(1), 0.05)
                    except asyncio.TimeoutError:
                        log.debug(
                            "Time out querying terminal: %s", query_code.__repr__()
                        )
                        break
                    else:
                        output += next_byte.decode()
                    # Send query after first character of first deliminator recieved
                    if not query_sent:
                        stdout_write(query_code)
                        stdout.flush()
                        query_sent = True
                    if re.search(sep_rsp, output):
                        if not output_started:
                            output_started = True
                            # Discard the first deliminator
                            output = ""
                            # Send the second deliminator
                            stdout_write(sep)
                            stdout.flush()
                            continue
                        break
            finally:
                transport.close()
                termios.tcsetattr(stdin, termios.TCSANOW, tattr)
            # Remove deliminator
            output = re.sub(sep_rsp, "", output, 1)
            # Parse result
            if match := CONTROL_RE.search(output):
                return match.groupdict()
        return None

    def _color(self, query_code: "str", response_code: "re.Pattern") -> "Optional[str]":
        """Get a colour of the terminal as a hex colour code."""
        if result := self.query_terminal(query_code):
            if oscs := result.get("osc_string"):
                if match := response_code.match(oscs):
                    if colors := match.groupdict():
                        if len(colors) >= 3:
                            r, g, b = (
                                colors.get("r", "00"),
                                colors.get("g", "00"),
                                colors.get("b", "00"),
                            )
                            return f"#{r[:2]}{g[:2]}{b[:2]}"
        return None

    @property
    def background_color(self) -> "str":
        """Get the background colour of the terminal as a hex colour code."""
        result = self._color(QueryCodes.bg_color, QueryResponsePatterns.bg_color)
        return result or "#000000"

    @property
    def foreground_color(self) -> "str":
        """Get the background colour of the terminal as a hex colour code."""
        result = self._color(QueryCodes.fg_color, QueryResponsePatterns.fg_color)
        return result or "#FFFFFF"

    @property
    def term_size_px(self) -> "tuple[int, int]":
        """Get the pixel dimensions of the terminal."""
        *_, px, py = _tiocgwnsz()
        # If unsuccessful, try requesting info with escape code method
        if px == 0:
            if result := self.query_terminal(QueryCodes.pixel_dimensions):
                params = result.get("csi_params", "")
                if match := QueryResponsePatterns.pixel_dimensions.match(params):
                    if values := match.groupdict():
                        if (x := values.get("x") is not None) and (
                            y := values.get("y") is not None
                        ):
                            px, py = int(x), int(y)
        return px, py

    @property
    def cell_size_px(self) -> "tuple[int, int]":
        """Get the pixel size of a single terminal character block."""
        px, py = self.term_size_px
        rows, cols = self.output.get_size()
        # If we can't get the pixel size, just guess wildly
        return px // cols or 10, py // rows or 22

    @property  # type: ignore
    @lru_cache
    def sixel_graphics_status(self) -> "bool":
        """Determine if the terminal supports sixel graphics."""
        if result := self.query_terminal(
            QueryCodes.sixel,
            stdout=self.output.stdout,
        ):
            param_str = result.get("csi_params", "")
            matches = QueryResponsePatterns.sixel.findall(param_str)
            params = [int(x) for x in matches]
            if 4 in params:
                return True
        return False

    @property  # type: ignore
    @lru_cache
    def kitty_graphics_status(self) -> "bool":
        """Determine if the terminal supports the kitty graphics protocal."""
        if result := self.query_terminal(QueryCodes.kitty):
            apc_string = result.get("apc_string", "")
            if apc_string.startswith("G"):
                if len(response := apc_string.lstrip("G").split(";")) >= 2:
                    if response[1] == "OK":
                        return True
        return False

    @property  # type: ignore
    @lru_cache
    def cursor_position(self) -> "tuple[int, int]":
        """Determine if the terminal supports the kitty graphics protocal."""
        row = col = 0
        if result := self.query_terminal(
            QueryCodes.cursor_position, stdout=self.output.stdout
        ):
            if csi_params := result.get("csi_params"):
                if match := QueryResponsePatterns.cursor_position.match(csi_params):
                    if pos := match.groupdict():
                        row = int(pos.get("row", 0))
                        col = int(pos.get("col", 0))
        return (row, col)

    @property  # type: ignore
    @lru_cache
    def color_depth(self) -> "ColorDepth":
        """Return the suspected color depth of the terminal."""
        # TODO - detect 24bit color support
        # "\x1b[48:2:1:2:3m\eP$qm\x1b\\"
        colorterm = os.environ.get("COLORTERM", "")
        if "truecolor" in colorterm or "24bit" in colorterm:
            return ColorDepth.DEPTH_24_BIT

        if "256" in os.environ.get("TERM", ""):
            return ColorDepth.DEPTH_8_BIT

        return ColorDepth.DEPTH_24_BIT
