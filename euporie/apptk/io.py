"""Define custom inputs and outputs, and related methods."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app

if TYPE_CHECKING:
    from typing import IO, Any, TextIO


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

    from euporie.apptk.application.run_in_terminal import run_in_terminal

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
