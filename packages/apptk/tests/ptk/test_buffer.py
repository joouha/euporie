"""Tests for Buffer functionality."""

from __future__ import annotations

import pytest
from apptk.buffer import Buffer


@pytest.fixture
def buffer() -> Buffer:
    """Create a buffer for testing."""
    buff = Buffer()
    return buff


def test_initial(buffer: Buffer) -> None:
    """Test initial buffer state."""
    assert buffer.text == ""
    assert buffer.cursor_position == 0


def test_insert_text(buffer: Buffer) -> None:
    """Test inserting text into buffer."""
    buffer.insert_text("some_text")
    assert buffer.text == "some_text"
    assert buffer.cursor_position == len("some_text")


def test_cursor_movement(buffer: Buffer) -> None:
    """Test cursor movement and insertion."""
    buffer.insert_text("some_text")
    buffer.cursor_left()
    buffer.cursor_left()
    buffer.cursor_left()
    buffer.cursor_right()
    buffer.insert_text("A")

    assert buffer.text == "some_teAxt"
    assert buffer.cursor_position == len("some_teA")


def test_backspace(buffer: Buffer) -> None:
    """Test deleting before cursor."""
    buffer.insert_text("some_text")
    buffer.cursor_left()
    buffer.cursor_left()
    buffer.delete_before_cursor()

    assert buffer.text == "some_txt"
    assert buffer.cursor_position == len("some_t")


def test_cursor_up(buffer: Buffer) -> None:
    """Test cursor up movement."""
    # Cursor up to a line that's longer.
    buffer.insert_text("long line1\nline2")
    buffer.cursor_up()

    assert buffer.document.cursor_position == 5

    # Going up when already at the top.
    buffer.cursor_up()
    assert buffer.document.cursor_position == 5

    # Going up to a line that's shorter.
    buffer.reset()
    buffer.insert_text("line1\nlong line2")

    buffer.cursor_up()
    assert buffer.document.cursor_position == 5


def test_cursor_down(buffer: Buffer) -> None:
    """Test cursor down movement."""
    buffer.insert_text("line1\nline2")
    buffer.cursor_position = 3

    # Normally going down
    buffer.cursor_down()
    assert buffer.document.cursor_position == len("line1\nlin")

    # Going down to a line that's shorter.
    buffer.reset()
    buffer.insert_text("long line1\na\nb")
    buffer.cursor_position = 3

    buffer.cursor_down()
    assert buffer.document.cursor_position == len("long line1\na")


def test_join_next_line(buffer: Buffer) -> None:
    """Test joining next line."""
    buffer.insert_text("line1\nline2\nline3")
    buffer.cursor_up()
    buffer.join_next_line()

    assert buffer.text == "line1\nline2 line3"

    # Test when there is no '\n' in the text
    buffer.reset()
    buffer.insert_text("line1")
    buffer.cursor_position = 0
    buffer.join_next_line()

    assert buffer.text == "line1"


def test_newline(buffer: Buffer) -> None:
    """Test inserting newline."""
    buffer.insert_text("hello world")
    buffer.newline()

    assert buffer.text == "hello world\n"


def test_swap_characters_before_cursor(buffer: Buffer) -> None:
    """Test swapping characters before cursor."""
    buffer.insert_text("hello world")
    buffer.cursor_left()
    buffer.cursor_left()
    buffer.swap_characters_before_cursor()

    assert buffer.text == "hello wrold"
