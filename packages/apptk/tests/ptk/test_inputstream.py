"""Tests for VT100 input stream parsing."""

from __future__ import annotations

from typing import Any

import pytest
from apptk.input.vt100_parser import Vt100Parser
from apptk.keys import Keys


class _ProcessorMock:
    """Mock processor for testing key press handling."""

    def __init__(self) -> None:
        """Initialize the mock processor."""
        self.keys: list[Any] = []

    def feed_key(self, key_press: Any) -> None:
        """Feed a key press to the processor."""
        self.keys.append(key_press)


@pytest.fixture
def processor() -> _ProcessorMock:
    """Create a processor mock fixture."""
    return _ProcessorMock()


@pytest.fixture
def stream(processor: _ProcessorMock) -> Vt100Parser:
    """Create a VT100 parser fixture."""
    return Vt100Parser(processor.feed_key)


def test_control_keys(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test control key parsing."""
    stream.feed("\x01\x02\x10")

    assert len(processor.keys) == 3
    assert processor.keys[0].key == Keys.ControlA
    assert processor.keys[1].key == Keys.ControlB
    assert processor.keys[2].key == Keys.ControlP
    assert processor.keys[0].data == "\x01"
    assert processor.keys[1].data == "\x02"
    assert processor.keys[2].data == "\x10"


def test_arrows(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test arrow key parsing."""
    stream.feed("\x1b[A\x1b[B\x1b[C\x1b[D")

    assert len(processor.keys) == 4
    assert processor.keys[0].key == Keys.Up
    assert processor.keys[1].key == Keys.Down
    assert processor.keys[2].key == Keys.Right
    assert processor.keys[3].key == Keys.Left
    assert processor.keys[0].data == "\x1b[A"
    assert processor.keys[1].data == "\x1b[B"
    assert processor.keys[2].data == "\x1b[C"
    assert processor.keys[3].data == "\x1b[D"


def test_escape(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test escape key parsing."""
    stream.feed("\x1bhello")

    # apptk recognizes \x1bh as Alt-h, so we get 5 keys not 6
    assert len(processor.keys) == len("hello")
    assert processor.keys[0].key == Keys.AltLatinsmallletterh
    assert processor.keys[1].key == "e"
    assert processor.keys[0].data == "\x1bh"
    assert processor.keys[1].data == "e"


def test_special_double_keys(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test special double key sequences."""
    stream.feed("\x1b[1;3D")  # apptk recognizes this as Alt-Left

    assert len(processor.keys) == 1
    assert processor.keys[0].key == Keys.AltLeft
    assert processor.keys[0].data == "\x1b[1;3D"


def test_flush_1(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test key parsing without flush."""
    # Send left key in two parts without flush.
    stream.feed("\x1b")
    stream.feed("[D")

    assert len(processor.keys) == 1
    assert processor.keys[0].key == Keys.Left
    assert processor.keys[0].data == "\x1b[D"


def test_flush_2(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test key parsing with flush."""
    # Send left key with a 'Flush' in between.
    # The flush should make sure that we process everything before as-is,
    # with makes the first part just an escape character instead.
    stream.feed("\x1b")
    stream.flush()
    stream.feed("[D")

    assert len(processor.keys) == 3
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == "["
    assert processor.keys[2].key == "D"

    assert processor.keys[0].data == "\x1b"
    assert processor.keys[1].data == "["
    assert processor.keys[2].data == "D"


def test_meta_arrows(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test meta arrow key parsing."""
    stream.feed("\x1b\x1b[D")

    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == Keys.Left


def test_control_square_close(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test control square close key parsing."""
    stream.feed("\x1dC")

    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.ControlSquareClose
    assert processor.keys[1].key == "C"


def test_invalid(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test invalid sequence parsing."""
    # Invalid sequence that has at two characters in common with other
    # sequences. apptk recognizes \x1b[ as Alt-[
    stream.feed("\x1b[*")

    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.AltLeftsquarebracket
    assert processor.keys[1].key == "*"


def test_cpr_response(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test cursor position report response parsing."""
    stream.feed("a\x1b[40;10Rb")
    assert len(processor.keys) == 3
    assert processor.keys[0].key == "a"
    assert processor.keys[1].key == Keys.CPRResponse
    assert processor.keys[2].key == "b"


def test_cpr_response_2(processor: _ProcessorMock, stream: Vt100Parser) -> None:
    """Test cursor position report with newline."""
    # Make sure that the newline is not included in the CPR response.
    stream.feed("\x1b[40;1R\n")
    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.CPRResponse
    assert processor.keys[1].key == Keys.ControlJ
