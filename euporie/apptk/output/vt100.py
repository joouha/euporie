"""Define custom inputs and outputs, and related methods."""

from __future__ import annotations

import logging
from base64 import b64encode
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    TextIO,
)

from prompt_toolkit.output.vt100 import Vt100_Output as PtkVt100_Output

from euporie.apptk.filters.env import in_screen, in_tmux
from euporie.apptk.filters.utils import to_filter

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.output.color_depth import ColorDepth

    from euporie.apptk.data_structures import Size
    from euporie.apptk.filters.base import FilterOrBool

log = logging.getLogger(__name__)


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


class Vt100_Output(PtkVt100_Output):
    """A Vt100 output which enables SGR pixel mouse positioning."""

    pixel_size: tuple[int, int]

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
        super().__init__(
            stdout, get_size, term, default_color_depth, enable_bell, enable_cpr
        )
        self.enable_passthrough = to_filter(enable_passthrough)

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

    def ask_for_clipboard(self) -> None:
        """Get clipboard contents using OSC-52."""
        self.write_raw("\x1b]52;c;?\x1b\\")

    def ask_for_colors(self) -> None:
        """Query terminal colors."""
        self.write_raw(
            self.mplex_passthrough(
                ("\x1b]10;?\x1b\\\x1b]11;?\x1b\\")
                + "".join(f"\x1b]4;{i};?\x1b\\" for i in range(16))
            )
        )

    def request_pixel_size(self) -> None:
        """Check the terminal's dimensions in pixels."""
        self.write_raw("\x1b[14t")

    def ask_for_kitty_graphics_status(self) -> None:
        """Query terminal to check for kitty graphics support."""
        self.write_raw(
            "\x1b[s"
            + self.mplex_passthrough(
                "\x1b_Gi=4294967295,s=1,v=1,a=q,t=d,f=24;aaaa\x1b\\"
            )
            + "\x1b[u\x1b[2K"
        )

    def ask_for_device_attributes(self) -> None:
        """Query terminal for device attributes."""
        self.write_raw(self.mplex_passthrough("\x1b[c"))

    def ask_for_iterm_graphics_status(self) -> None:
        """Query terminal for iTerm graphics support."""
        self.write_raw(self.mplex_passthrough("\x1b[>q"))

    def ask_for_sgr_pixel_status(self) -> None:
        """Query terminal to check for Pixel SGR support."""
        # Enable, check, disable
        self.write_raw("\x1b[?1016h\x1b[?1016$p\x1b[?1016l")

    def ask_for_csiu_status(self) -> None:
        """Query terminal to check for CSI-u support."""
        self.write_raw("\x1b[?u")
