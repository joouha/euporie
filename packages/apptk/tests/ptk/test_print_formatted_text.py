"""Test the `print` function."""

from __future__ import annotations

import pytest
from apptk import print_formatted_text as pt_print
from apptk.formatted_text import HTML, FormattedText, to_formatted_text
from apptk.output import ColorDepth
from apptk.styles import Style
from apptk.utils import is_windows


class _Capture:
    """Emulate an stdout object."""

    def __init__(self) -> None:
        """Initialize the capture object."""
        self._data: list[str] = []

    def write(self, data: str) -> None:
        """Write data to the capture buffer."""
        self._data.append(data)

    @property
    def data(self) -> str:
        """Return the captured data."""
        return "".join(self._data)

    def flush(self) -> None:
        """Flush the buffer (no-op)."""

    def isatty(self) -> bool:
        """Return whether this is a TTY."""
        return True

    def fileno(self) -> int:
        """Return the file descriptor."""
        # File descriptor is not used for printing formatted text.
        # (It is only needed for getting the terminal size.)
        return -1


@pytest.mark.skipif(is_windows(), reason="Doesn't run on Windows yet.")
def test_print_formatted_text() -> None:
    """Test printing formatted text."""
    f = _Capture()
    pt_print([("", "hello"), ("", "world")], file=f)
    assert "hello" in f.data
    assert "world" in f.data


@pytest.mark.skipif(is_windows(), reason="Doesn't run on Windows yet.")
def test_print_formatted_text_backslash_r() -> None:
    """Test printing formatted text with backslash-r."""
    f = _Capture()
    pt_print("hello\r\n", file=f)
    assert "hello" in f.data


@pytest.mark.skipif(is_windows(), reason="Doesn't run on Windows yet.")
def test_formatted_text_with_style() -> None:
    """Test printing formatted text with style."""
    f = _Capture()
    style = Style.from_dict(
        {
            "hello": "#ff0066",
            "world": "#44ff44 italic",
        }
    )
    tokens = FormattedText(
        [
            ("class:hello", "Hello "),
            ("class:world", "world"),
        ]
    )

    # NOTE: We pass the default (8bit) color depth, so that the unit tests
    #       don't start failing when environment variables change.
    pt_print(tokens, style=style, file=f, color_depth=ColorDepth.DEFAULT)
    assert "\x1b[0;38;5;197mHello" in f.data
    assert "\x1b[0;38;5;83;3mworld" in f.data


@pytest.mark.skipif(is_windows(), reason="Doesn't run on Windows yet.")
def test_html_with_style() -> None:
    """Text `print_formatted_text` with `HTML` wrapped in `to_formatted_text`."""
    f = _Capture()

    html = HTML("<ansigreen>hello</ansigreen> <b>world</b>")
    formatted_text = to_formatted_text(html, style="class:myhtml")
    pt_print(formatted_text, file=f, color_depth=ColorDepth.DEFAULT)

    assert (
        f.data
        == "\x1b[0m\x1b[?7h\x1b[0;32mhello\x1b[0m \x1b[0;1mworld\x1b[0m\r\n\x1b[0m"
    )


@pytest.mark.skipif(is_windows(), reason="Doesn't run on Windows yet.")
def test_print_formatted_text_with_dim() -> None:
    """Test that dim formatting works correctly."""
    f = _Capture()
    style = Style.from_dict(
        {
            "dimtext": "dim",
        }
    )
    tokens = FormattedText([("class:dimtext", "dim text")])

    pt_print(tokens, style=style, file=f, color_depth=ColorDepth.DEFAULT)

    # Check that the ANSI dim escape code (ESC[2m) is in the output
    assert "\x1b[0;2m" in f.data or "\x1b[2m" in f.data
