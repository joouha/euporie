# -*- coding: utf-8 -*-
"""Contains classes related to querying terminal feautres."""
from __future__ import annotations

import array
import re
import sys
from functools import lru_cache
from typing import IO, Callable, Optional, cast

from prompt_toolkit.output import Output

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

    device = "\x1b[>0c"
    pixel_dimensions = "\x1b[14t"
    background_color = "\x1b]11;?\x1b\\"
    sixel = "\033[?1;1;0S"
    # For some reason, konsole prints APC codes to the screen, so we clear the current
    # line and move the curor to the start after sending a kitty graphics query code,
    # which prevents breaking the display
    kitty = "\x1b_Gi=1,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\" + "\x1b[1K" + "\x1b[1G"


class QueryResponsePatterns:
    """Container for terminal query response patterns."""

    device = re.compile(r"\x1b\[\>(\d;?)+c")
    background_color = re.compile(
        "11;rgb:(?P<r>[0-9A-Fa-f]{2,4})/(?P<g>[0-9A-Fa-f]{2,4})/(?P<b>[0-9A-Fa-f]{2,4})"
    )
    pixel_dimensions = re.compile(r"4;(?P<y>\d+);(?P<x>\d+)")
    sixel = re.compile(r"\d+")
    kitty = "\x1b[_Gi=1;OK\x1b[\\"


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


def _query_term(
    query_code: "str", stdin: "IO[str]" = None, stdout: "IO[str]" = None
) -> "Optional[dict[str,str]]":
    """Query the terminal and parse the response.

    A Secondary Device Attribute request is used as the deliminator to locate the
    query response string.

    Args:
        query_code: The ANSI escape sequence to send to the terminal.
        stdin: IO to use as stdin
        stdout: IO to use as stdout

    Returns:
        A parsed escape code response.

    """
    if stdin is None:
        stdin = sys.stdin
    if stdout is None:
        stdout = sys.stdout

    # Check for tty in stdout
    if hasattr(stdout, "isatty"):
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

        tattr = termios.tcgetattr(stdin)

        output = ""

        try:
            tty.setcbreak(stdin, termios.TCSANOW)
            stdout_write(QueryCodes.device)
            stdout.flush()

            output_started = False
            query_sent = False

            while True:
                output += stdin.read(1)
                # Send query after first character of first deliminator recieved
                if not query_sent:
                    stdout_write(query_code)
                    stdout.flush()
                    query_sent = True
                if re.search(QueryResponsePatterns.device, output):
                    if not output_started:
                        output_started = True
                        # Discard the first deliminator
                        output = ""
                        # Send the second deliminator
                        stdout_write(QueryCodes.device)
                        stdout.flush()
                        continue
                    break
        finally:
            termios.tcsetattr(stdin, termios.TCSANOW, tattr)
        # Remove deliminator
        output = re.sub(QueryResponsePatterns.device, "", output, 1)
        # Parse result
        if match := CONTROL_RE.search(output):
            return match.groupdict()
    return None


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


class TermMixin:
    """Mixin for `euporie.app.App` which provides terminal feature properties."""

    output: "Output"

    @property
    def bg_color(self) -> "Optional[str]":
        """Get the background colour of the terminal as a hex colour code."""
        if result := _query_term(
            QueryCodes.background_color, stdout=self.output.stdout
        ):
            if oscs := result.get("osc_string"):
                if match := QueryResponsePatterns.background_color.match(oscs):
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
    def term_size_px(self) -> "tuple[int, int]":
        """Get the pixel dimensions of the terminal."""
        *_, px, py = _tiocgwnsz()
        # If unsuccessful, try requesting info with escape code method
        if px == 0:
            if result := _query_term(
                QueryCodes.pixel_dimensions, stdout=self.output.stdout
            ):
                params = result.get("csi_params", "")
                if match := QueryResponsePatterns.pixel_dimensions.match(params):
                    if values := match.groupdict():
                        if (x := values.get("x") is not None) and (
                            y := values.get("y") is not None
                        ):
                            px, py = int(x), int(y)
        return px, py

    @property
    def char_size_px(self) -> "tuple[int, int]":
        """Get the pixel size of a single terminal character block."""
        px, py = self.term_size_px
        rows, cols = self.output.get_size()
        # If we can't get the pixel size, just guess wildly
        return px // cols or 10, py // rows or 22

    @property  # type: ignore
    @lru_cache
    def has_sixel_graphics(self) -> "bool":
        """Determine if the terminal supports sixel graphics."""
        if result := _query_term(QueryCodes.sixel, stdout=self.output.stdout):
            param_str = result.get("csi_params", "")
            matches = QueryResponsePatterns.sixel.findall(param_str)
            params = [int(x) for x in matches]
            if len(params) >= 3:
                Pi, Ps, Pv = params[:3]
                if Ps == 0:
                    return True
        return False

    @property  # type: ignore
    @lru_cache
    def has_kitty_graphics(self) -> "bool":
        """Determine if the terminal supports the kitty graphics protocal."""
        if result := _query_term(QueryCodes.kitty, stdout=self.output.stdout):
            apc_string = result.get("apc_string", "")
            if apc_string.startswith("G"):
                if len(response := apc_string.lstrip("G").split(";")) >= 2:
                    if response[1] == "OK":
                        return True
        return False
