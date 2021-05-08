# -*- coding: utf-8 -*-
import array
import re
import sys
from functools import lru_cache

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
    device = "\x1b[>0c"
    pixel_dimensions = "\x1b[14t"
    background_color = "\x1b]11;?\x1b\\"
    sixel = "\033[?1;1;0S"
    # For some reason, konsole prints APC codes to the screen, so we clear the current
    # line and move the curor to the start after sending a kitty graphics query code,
    # which prevents breaking the display
    kitty = "\x1b_Gi=1,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\" + "\x1b[1K" + "\x1b[1G"


class QueryResponsePatterns:
    device = re.compile(r"\x1b\[\>(\d;?)+c")
    background_color = re.compile(
        "11;rgb:(?P<r>[0-9A-Fa-f]{2,4})/(?P<g>[0-9A-Fa-f]{2,4})/(?P<b>[0-9A-Fa-f]{2,4})"
    )
    pixel_dimensions = re.compile(r"4;(?P<y>\d+);(?P<x>\d+)")
    sixel = re.compile(r"\d+")
    kitty = "\x1b[_Gi=1;OK\x1b[\\"


class TermAppMixin:
    @property
    @lru_cache
    def _have_termios_tty_fcntl(self):
        try:
            import fcntl  # noqa F401
            import termios  # noqa F401
            import tty  # noqa F401
        except ModuleNotFoundError:
            return False
        else:
            return True

    def _query_term(self, query_code):
        """
        We use a Secondary Device Attribute request as our deliminator to locate the
        query response string
        """
        if self._have_termios_tty_fcntl:
            import termios
            import tty

            stdin = sys.stdin.fileno()
            tattr = termios.tcgetattr(stdin)

            output = ""

            try:
                tty.setcbreak(stdin, termios.TCSANOW)
                self.output.write_raw(QueryCodes.device)
                self.output.flush()

                output_started = False
                query_sent = False

                while True:
                    output += sys.stdin.read(1)
                    # Send query after first character of first deliminator recieved
                    if not query_sent:
                        self.output.write_raw(query_code)
                        self.output.flush()
                        query_sent = True
                    if re.search(QueryResponsePatterns.device, output):
                        if not output_started:
                            output_started = True
                            # Discard the first deliminator
                            output = ""
                            # Send the second deliminator
                            self.output.write_raw(QueryCodes.device)
                            self.output.flush()
                            continue
                        break
            finally:
                termios.tcsetattr(stdin, termios.TCSANOW, tattr)
            # Remove deliminator
            output = re.sub(QueryResponsePatterns.device, "", output, 1)
            # Parse result
            if match := CONTROL_RE.search(output):
                return match.groupdict()

    def tiocgwnsz(self):
        output = array.array("H", [0, 0, 0, 0])
        if self._have_termios_tty_fcntl:
            import fcntl
            import termios

            fcntl.ioctl(1, termios.TIOCGWINSZ, output)
        rows, cols, xpixels, ypixels = output
        return rows, cols, xpixels, ypixels

    @property
    def bg_color(self):
        if result := self._query_term(QueryCodes.background_color):
            if oscs := result.get("osc_string"):
                if match := QueryResponsePatterns.background_color.match(oscs):
                    if colors := match.groupdict():
                        if len(colors) >= 3:
                            r, g, b = colors.get("r"), colors.get("g"), colors.get("b")
                            return f"#{r[:2]}{g[:2]}{b[:2]}"

    @property
    def term_size_px(self):
        *_, px, py = self.tiocgwnsz()
        # If unsuccessful, try requesting info with escape code method
        if px == 0:
            if result := self._query_term(QueryCodes.pixel_dimensions):
                params = result.get("csi_params", "")
                if match := QueryResponsePatterns.pixel_dimensions.match(params):
                    if values := match.groupdict():
                        px, py = int(values.get("x")), int(values.get("y"))
        return px, py

    @property
    def char_size_px(self):
        px, py = self.term_size_px
        rows, cols = self.output.get_size()
        # If we can't get the pixel size, just guess wildly
        if px == 0:
            return 10, 22
        return px // cols, py // rows

    @property
    @lru_cache
    def has_sixel_graphics(self):
        if result := self._query_term(QueryCodes.sixel):
            params = result.get("csi_params", "")
            params = QueryResponsePatterns.sixel.findall(params)
            params = [int(x) for x in params]
            if len(params) <= 3:
                Pi, Ps, Pv = params[:3]
                if Ps == 0:
                    return True
        return False

    @property
    @lru_cache
    def has_kitty_graphics(self):
        if result := self._query_term(QueryCodes.kitty):
            apc_string = result.get("apc_string", "")
            if apc_string.startswith("G"):
                if len(response := apc_string.lstrip("G").split(";")) >= 2:
                    if response[1] == "OK":
                        return True
        return False
