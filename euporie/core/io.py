"""Define custom inputs and outputs, and related methods."""

from __future__ import annotations

import logging
import re
from base64 import b64encode
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from prompt_toolkit.input import vt100_parser
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.input.base import DummyInput, _dummy_context_manager
from prompt_toolkit.output.color_depth import ColorDepth
from prompt_toolkit.output.vt100 import Vt100_Output as PtkVt100_Output

from euporie.core.app.current import get_app
from euporie.core.filters import in_screen, in_tmux

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager
    from typing import IO, Any, TextIO

    from prompt_toolkit.keys import Keys

    from euporie.core.config import Config

log = logging.getLogger(__name__)

COLOR_DEPTHS = {
    1: ColorDepth.DEPTH_1_BIT,
    4: ColorDepth.DEPTH_4_BIT,
    8: ColorDepth.DEPTH_8_BIT,
    24: ColorDepth.DEPTH_24_BIT,
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


def passthrough(cmd: str, config: Config | None = None) -> str:
    """Wrap an escape sequence for terminal passthrough."""
    config = config or get_app().config
    if config.multiplexer_passthrough:
        if in_tmux():
            cmd = cmd.replace("\x1b", "\x1b\x1b")
            cmd = f"\x1bPtmux;{cmd}\x1b\\"
        elif in_screen():
            # Screen limits escape sequences to 768 bytes, so we have to chunk it
            cmd = "".join(
                f"\x1bP{cmd[i : i + 764]}\x1b\\" for i in range(0, len(cmd), 764)
            )
    return cmd


class _IsPrefixOfLongerMatchCache(vt100_parser._IsPrefixOfLongerMatchCache):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Pattern for any ANSI escape sequence
        self._response_prefix_re = re.compile(
            r"""^\x1b(
                \][^\\\x07]*  # Operating System Commands
                |
                _[^\\]*  # Application Program Command
                |
                \[\?[\d;]*  # Primary device attribute responses
                |
                P[ -~]*(\x1b|x1b\\)?
            )\Z""",
            re.VERBOSE,
        )
        # Generate prefix matches for all known ansi escape sequences
        # This is faster than PTK's method
        self._ansi_sequence_prefixes = {
            seq[:i] for seq in ANSI_SEQUENCES for i in range(len(seq))
        }

    def __missing__(self, prefix: str) -> bool:
        """Check if the response might match an OSC or APC code, or DA response."""
        result = bool(
            # (hard coded) If this could be a prefix of a CPR response, return True.
            vt100_parser._cpr_response_prefix_re.match(prefix)
            # True if this could be a mouse event sequence
            or vt100_parser._mouse_event_prefix_re.match(prefix)
            # True if this could be the prefix of an expected escape sequence
            or prefix in self._ansi_sequence_prefixes
            # If this could be a prefix of any other escape sequence, return True
            or self._response_prefix_re.match(prefix)
        )
        self[prefix] = result
        return result


# Monkey patch the prefix cache
vt100_parser._IS_PREFIX_OF_LONGER_MATCH_CACHE = _IsPrefixOfLongerMatchCache()


class Vt100Parser(vt100_parser.Vt100Parser):
    """A Vt100Parser which checks input against additional key patterns."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create a new VT100 parser."""
        from euporie.core.keys import MoreKeys

        super().__init__(*args, **kwargs)
        self.patterns: dict[Keys | MoreKeys, re.Pattern] = {
            MoreKeys.ColorsResponse: re.compile(
                r"^\x1b\](?P<c>(\d+;)?\d+)+;rgb:"
                r"(?P<r>[0-9A-Fa-f]{2,4})\/"
                r"(?P<g>[0-9A-Fa-f]{2,4})\/"
                r"(?P<b>[0-9A-Fa-f]{2,4})"
                # Allow BEL or ST as terminator
                r"(?:\x1b\\|\x9c|\x07)"
            ),
            MoreKeys.PaletteDsrResponse: re.compile(r"^\x1b\[\?997;(?P<mode>\d)n"),
            MoreKeys.PixelSizeResponse: re.compile(r"^\x1b\[4;(?P<y>\d+);(?P<x>\d+)t"),
            MoreKeys.KittyGraphicsStatusResponse: re.compile(
                r"^\x1b_Gi=(4294967295|0);(?P<status>OK)\x1b\\"
            ),
            MoreKeys.DeviceAttributesResponse: re.compile(
                r"^\x1b\[\?(?P<attrs>[\d;]*)c"
            ),
            MoreKeys.ItermGraphicsStatusResponse: re.compile(
                r"^\x1bP>\|(?P<term>[^\x1b]+)\x1b\\"
            ),
            MoreKeys.SgrPixelStatusResponse: re.compile(r"^\x1b\[\?1016;(?P<Pm>\d)\$"),
            MoreKeys.ClipboardDataResponse: re.compile(
                r"^\x1b\]52;(?:c|p)?;(?P<data>[A-Za-z0-9+/=]+)\x1b\\"
            ),
        }

    def _get_match(self, prefix: str) -> None | Keys | tuple[Keys, ...]:
        """Check for additional key matches first."""
        for key, pattern in self.patterns.items():
            if pattern.match(prefix):
                return cast("Keys", key)

        return super()._get_match(prefix)


class IgnoredInput(DummyInput):
    """An input which ignores input but does not immediately close the app."""

    def attach(
        self, input_ready_callback: Callable[[], None]
    ) -> AbstractContextManager[None]:
        """Do not call the callback, so the input is never closed."""
        return _dummy_context_manager()


class Vt100_Output(PtkVt100_Output):
    """A Vt100 output which enables SGR pixel mouse positioning."""

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

    def get_clipboard(self) -> None:
        """Get clipboard contents using OSC-52."""
        self.write_raw("\x1b]52;c;?\x1b\\")

    def get_colors(self) -> None:
        """Query terminal colors."""
        self.write_raw(
            passthrough(
                ("\x1b]10;?\x1b\\\x1b]11;?\x1b\\")
                + "".join(f"\x1b]4;{i};?\x1b\\" for i in range(16))
            )
        )

    def get_pixel_size(self) -> None:
        """Check the terminal's dimensions in pixels."""
        self.write_raw("\x1b[14t")

    def get_kitty_graphics_status(self) -> None:
        """Query terminal to check for kitty graphics support."""
        self.write_raw(
            "\x1b[s"
            + passthrough("\x1b_Gi=4294967295,s=1,v=1,a=q,t=d,f=24;aaaa\x1b\\")
            + "\x1b[u\x1b[2K"
        )

    def get_device_attributes(self) -> None:
        """Query terminal for device attributes."""
        self.write_raw(passthrough("\x1b[c"))

    def get_iterm_graphics_status(self) -> None:
        """Query terminal for iTerm graphics support."""
        self.write_raw(passthrough("\x1b[>q"))

    def get_sgr_pixel_status(self) -> None:
        """Query terminal to check for Pixel SGR support."""
        # Enable, check, disable
        self.write_raw("\x1b[?1016h\x1b[?1016$p\x1b[?1016l")

    def get_csiu_status(self) -> None:
        """Query terminal to check for CSI-u support."""
        self.write_raw("\x1b[?u")


class PseudoTTY:
    """Make an output stream look like a TTY."""

    fake_tty = True

    def __init__(self, underlying: IO[str] | TextIO, isatty: bool = True) -> None:
        """Wrap an underlying output stream.

        Args:
            underlying: The underlying output stream
            isatty: The value to return from :py:method:`PseudoTTY.isatty`.

        """
        self._underlying = underlying
        self._isatty = isatty

    def isatty(self) -> bool:
        """Determine if the stream is interpreted as a TTY."""
        return self._isatty

    def __getattr__(self, name: str) -> Any:
        """Return an attribute of the wrappeed stream."""
        return getattr(self._underlying, name)


def edit_in_editor(filename: str, line_number: int = 0) -> None:
    """Suspend the current app and edit a file in an external editor."""
    import os
    import shlex
    import subprocess

    from prompt_toolkit.application.run_in_terminal import run_in_terminal

    def _open_file_in_editor(filename: str) -> None:
        """Call editor executable."""
        # If the 'VISUAL' or 'EDITOR' environment variable has been set, use that.
        # Otherwise, fall back to the first available editor that we can find.
        for editor in [
            os.environ.get("VISUAL"),
            os.environ.get("EDITOR"),
            "editor",
            "micro",
            "nano",
            "pico",
            "vi",
            "emacs",
        ]:
            if editor:
                try:
                    # Use 'shlex.split()' because $VISUAL can contain spaces and quotes
                    subprocess.call([*shlex.split(editor), filename])
                    return
                except OSError:
                    # Executable does not exist, try the next one.
                    pass

    async def run() -> None:
        # Open in editor
        # (We need to use `run_in_terminal`, because not all editors go to
        # the alternate screen buffer, and some could influence the cursor
        # position)
        await run_in_terminal(lambda: _open_file_in_editor(filename), in_executor=True)

    get_app().create_background_task(run())
