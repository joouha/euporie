"""Define custom inputs and outputs, and related methods."""

from __future__ import annotations

import logging
import os
from base64 import b64encode
from functools import lru_cache
from typing import TYPE_CHECKING, TextIO

from prompt_toolkit.output.vt100 import (
    BG_ANSI_COLORS,
    FG_ANSI_COLORS,
    _16_bg_colors,
    _16_fg_colors,
    _256_colors,
)
from prompt_toolkit.output.vt100 import (
    Vt100_Output as PtkVt100_Output,
)
from prompt_toolkit.output.vt100 import (
    _EscapeCodeCache as _PtkEscapeCodeCache,
)

from euporie.apptk.filters.environment import in_screen, in_tmux
from euporie.apptk.filters.utils import to_filter
from euporie.apptk.output.color_depth import ColorDepth
from euporie.apptk.styles.base import DEFAULT_ATTRS
from euporie.apptk.utils import is_dumb_terminal

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from prompt_toolkit.styles.base import Attrs

    from euporie.apptk.data_structures import Size
    from euporie.apptk.filters.base import FilterOrBool

log = logging.getLogger(__name__)

TERMINAL_COLORS_TO_RGB = {
    "fg": (255, 255, 255),
    "bg": (0, 0, 0),
}


@lru_cache
def _have_termios_tty_fcntl() -> bool:
    try:
        import fcntl  # noqa F401
        import termios  # noqa F401
        import tty  # noqa F401
    except ModuleNotFoundError:
        return False
    else:
        return True


# TODO - move to output
def _tiocgwinsz() -> tuple[int, int, int, int]:
    """Get the size and pixel dimensions of the terminal with `termios`."""
    import array

    output = array.array("H", [0, 0, 0, 0])
    if _have_termios_tty_fcntl():
        import fcntl
        import termios

        try:
            fcntl.ioctl(1, termios.TIOCGWINSZ, output)
        except OSError:
            pass
    rows, cols, xpixels, ypixels = output
    return rows, cols, xpixels, ypixels


class _EscapeCodeCache(_PtkEscapeCodeCache):
    """Cache for VT100 escape codes.

    It maps (fgcolor, bgcolor, bold, dim, underline, doubleunderline, curvyunderline,
    strike, italic, blink, blinkfast, reverse, hidden and overline) tuples to VT100
    escape sequences.

    Args:
        true_color: When True, use 24bit colors instead of 256 colors.
    """

    def __init__(self, color_depth: ColorDepth) -> None:
        self.color_depth = color_depth

    def __missing__(self, attrs: Attrs) -> str:
        attr_args = DEFAULT_ATTRS._asdict() | attrs._asdict()
        fgcolor = attr_args["color"]
        bgcolor = attr_args["bgcolor"]
        bold = attr_args["bold"]
        dim = attr_args["dim"]
        underline = attr_args["underline"]
        strike = attr_args["strike"]
        italic = attr_args["italic"]
        blink = attr_args["blink"]
        reverse = attr_args["reverse"]
        hidden = attr_args["hidden"]
        blinkfast = attr_args["blinkfast"]
        ulcolor = attr_args["ulcolor"]
        doubleunderline = attr_args["doubleunderline"]
        curvyunderline = attr_args["curvyunderline"]
        dottedunderline = attr_args["dottedunderline"]
        dashedunderline = attr_args["dashedunderline"]
        overline = attr_args["overline"]

        parts: list[str] = []

        parts.extend(self._colors_to_code(fgcolor or "", bgcolor or "", ulcolor or ""))

        if bold:
            parts.append("1")
        if dim:
            parts.append("2")
        if italic:
            parts.append("3")
        if blink:
            parts.append("5")
        if underline:
            parts.append("4")
        if doubleunderline:
            parts.append("4:2")
        if curvyunderline:
            parts.append("4:3")
        if dottedunderline:
            parts.append("4:4")
        if dashedunderline:
            parts.append("4:5")
        if blink:
            parts.append("5")
        if blinkfast:
            parts.append("6")
        if reverse:
            parts.append("7")
        if hidden:
            parts.append("8")
        if strike:
            parts.append("9")
        if overline:
            parts.append("53")

        if parts:
            result = "\x1b[0;" + ";".join(parts) + "m"
        else:
            result = "\x1b[0m"

        self[attrs] = result
        return result

    def _colors_to_code(
        self, fg_color: str, bg_color: str, ul_color: str = ""
    ) -> Iterable[str]:
        """Return a tuple with the vt100 values that represent this color."""
        result: list[int] = []
        fg_ansi = ""

        if self.color_depth == ColorDepth.DEPTH_1_BIT:
            return result

        # Process foreground color
        if fg_color:
            if fg_color in FG_ANSI_COLORS:
                result.append(FG_ANSI_COLORS[fg_color])
            else:
                try:
                    rgb = self._color_name_to_rgb(fg_color)
                    if self.color_depth == ColorDepth.DEPTH_4_BIT:
                        code, fg_ansi = _16_fg_colors.get_code(rgb)
                        result.append(code)
                    elif self.color_depth == ColorDepth.DEPTH_24_BIT:
                        r, g, b = rgb
                        result.extend([38, 2, r, g, b])
                    else:
                        result.extend([38, 5, _256_colors[rgb]])
                except ValueError:
                    pass

        # Process background color
        if bg_color:
            if bg_color in BG_ANSI_COLORS:
                result.append(BG_ANSI_COLORS[bg_color])
            else:
                try:
                    rgb = self._color_name_to_rgb(bg_color)
                    if self.color_depth == ColorDepth.DEPTH_4_BIT:
                        exclude = [fg_ansi] if fg_color != bg_color else []
                        code, _ = _16_bg_colors.get_code(rgb, exclude=exclude)
                        result.append(code)
                    elif self.color_depth == ColorDepth.DEPTH_24_BIT:
                        r, g, b = rgb
                        result.extend([48, 2, r, g, b])
                    else:
                        result.extend([48, 5, _256_colors[rgb]])
                except ValueError:
                    pass

        # Process underline color (SGR 58 for setting underline color)
        if ul_color:
            if ul_color in FG_ANSI_COLORS:
                # Use SGR 58:5:n for 256-color mode with ANSI color index
                result.extend([58, 5, FG_ANSI_COLORS[ul_color]])
            else:
                try:
                    rgb = self._color_name_to_rgb(ul_color)
                    if self.color_depth == ColorDepth.DEPTH_4_BIT:
                        code, _ = _16_fg_colors.get_code(rgb)
                        result.extend([58, 5, code])
                    elif self.color_depth == ColorDepth.DEPTH_24_BIT:
                        r, g, b = rgb
                        result.extend([58, 2, r, g, b])
                    else:
                        result.extend([58, 5, _256_colors[rgb]])
                except ValueError:
                    pass

        return map(str, result)


class Vt100_Output(PtkVt100_Output):
    """A Vt100 output which enables SGR pixel mouse positioning."""

    _pixel_size: tuple[int, int]

    def __init__(
        self,
        stdout: TextIO,
        get_size: Callable[[], Size],
        term: str | None = None,
        default_color_depth: ColorDepth | None = None,
        enable_bell: bool = True,
        enable_cpr: bool = True,
        enable_passthrough: FilterOrBool = False,
    ) -> None:
        """Initialize the Vt100 output.

        Args:
            stdout: The stdout stream to write to.
            get_size: Callable that returns the terminal size.
            term: The terminal type string.
            default_color_depth: The default color depth to use.
            enable_bell: Whether to enable the terminal bell.
            enable_cpr: Whether to enable cursor position reporting.
            enable_passthrough: Whether to enable terminal multiplexer passthrough.
        """
        super().__init__(
            stdout, get_size, term, default_color_depth, enable_bell, enable_cpr
        )
        self.enable_passthrough = to_filter(enable_passthrough)

    def begin_synced_output(self) -> None:
        """Begin updating the output."""
        self.write_raw("\x1b[?2026h")
        self.flush()

    def end_synced_output(self) -> None:
        """End updating the terminal output."""
        self.write_raw("\x1b[?2026l")

    def mplex_passthrough(self, cmd: str) -> str:
        """Wrap an escape sequence for terminal passthrough."""
        if self.enable_passthrough():
            if in_tmux():
                cmd = cmd.replace("\x1b", "\x1b\x1b")
                cmd = f"\x1bPtmux;{cmd}\x1b\\"
            elif in_screen():
                # Screen limits escape sequences to 768 bytes, so we have to chunk it
                cmd = "".join(
                    f"\x1bP{cmd[i : i + 764]}\x1b\\" for i in range(0, len(cmd), 764)
                )
        return cmd

    def get_pixel_size(self) -> tuple[int, int]:
        """Dimensions of the terminal in pixels."""
        try:
            return self._pixel_size
        except AttributeError:
            from euporie.apptk.io import _tiocgwinsz

            _rows, _cols, px, py = _tiocgwinsz()
            self._pixel_size = (px, py)
        return self._pixel_size

    def set_pixel_size(self, px: int, py: int) -> None:
        """Set terminal pixel dimensions."""
        self._pixel_size = (px, py)

    def write_raw(self, data: str) -> None:
        """Write raw data to output."""
        self._buffer.append(data)

    def clear_graphics_kitty(self) -> None:
        """Delete all kitty terminal graphic placements."""
        self.write_raw("\x1b_Ga=d,d=a,q=1\x1b\\")

    def enable_sgr_pixel(self) -> None:
        """Enable SGR-pixel mouse positioning."""
        self.write_raw("\x1b[?1016h")

    def disable_sgr_pixel(self) -> None:
        """Disable SGR-pixel mouse positioning."""
        self.write_raw("\x1b[?1016l")

    def enable_palette_dsr(self) -> None:
        """Enable device status reports for color palette updates."""
        self.write_raw("\x1b[?2031h")

    def disable_palette_dsr(self) -> None:
        """Disable device status reports for color palette updates."""
        self.write_raw("\x1b[?2031l")

    def enable_extended_keys(self) -> None:
        """Request extended keys."""
        # xterm
        self.write_raw("\x1b[>4;1m")
        # kitty
        self.write_raw("\x1b[>1u")

    def disable_extended_keys(self) -> None:
        """Disable extended keys."""
        # xterm
        self.write_raw("\x1b[>4;0m")
        # kitty
        self.write_raw("\x1b[<1u")

    def set_clipboard(self, text: str) -> None:
        """Set clipboard data using OSC-52."""
        b64data = b64encode(text.encode()).decode()
        self.write_raw(f"\x1b]52;c;{b64data}\x1b\\")
        self.flush()

    def ask_for_clipboard(self) -> None:
        """Get clipboard contents using OSC-52."""
        self.write_raw("\x1b]52;c;?\x1b\\")
        self.flush()

    def ask_for_colors(self) -> None:
        """Query terminal colors."""
        self.write_raw(
            self.mplex_passthrough(
                ("\x1b]10;?\x1b\\\x1b]11;?\x1b\\")
                + "".join(f"\x1b]4;{i};?\x1b\\" for i in range(16))
            )
        )
        self.flush()

    def ask_for_pixel_size(self) -> None:
        """Check the terminal's dimensions in pixels."""
        self.write_raw("\x1b[14t")
        self.flush()

    def ask_for_kitty_graphics_status(self) -> None:
        """Query terminal to check for kitty graphics support."""
        self.write_raw(
            "\x1b[s"
            + self.mplex_passthrough(
                "\x1b_Gi=4294967295,s=1,v=1,a=q,t=d,f=24;aaaa\x1b\\"
            )
            + "\x1b[u\x1b[2K"
        )
        self.flush()

    def ask_for_device_attributes(self) -> None:
        """Query terminal for device attributes."""
        self.write_raw(self.mplex_passthrough("\x1b[c"))
        self.flush()

    def ask_for_iterm_graphics_status(self) -> None:
        """Query terminal for iTerm graphics support."""
        self.write_raw(self.mplex_passthrough("\x1b[>q"))
        self.flush()

    def ask_for_sgr_pixel_status(self) -> None:
        """Query terminal to check for Pixel SGR support."""
        # Enable, check, disable
        self.write_raw("\x1b[?1016h\x1b[?1016$p\x1b[?1016l")
        self.flush()

    def ask_for_csiu_status(self) -> None:
        """Query terminal to check for CSI-u support."""
        self.write_raw("\x1b[?u")
        self.flush()

    def get_default_color_depth(self) -> ColorDepth:
        """Return the default color depth for a vt100 terminal, according to the our term value.

        We prefer 256 colors almost always, because this is what most terminals
        support these days, and is a good default.

        This override adds support for the NO_COLOR and COLORTERM environment variables.
        """
        if self.default_color_depth is not None:
            return self.default_color_depth

        colorterm = os.environ.get("COLORTERM", "")
        if "truecolor" in colorterm or "24bit" in colorterm:
            return ColorDepth.DEPTH_24_BIT

        term = self.term

        if term is None:
            return ColorDepth.DEFAULT

        if is_dumb_terminal(term) or os.environ.get("NO_COLOR", ""):
            return ColorDepth.DEPTH_1_BIT

        if term in ("linux", "eterm-color"):
            return ColorDepth.DEPTH_4_BIT

        if "256" in term:
            return ColorDepth.DEPTH_8_BIT

        return ColorDepth.DEFAULT
