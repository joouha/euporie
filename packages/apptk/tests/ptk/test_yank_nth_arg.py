"""Tests for yank nth arg functionality."""

from __future__ import annotations

import pytest
from apptk.buffer import Buffer
from apptk.history import InMemoryHistory


@pytest.fixture
def history() -> InMemoryHistory:
    """Prefilled history."""
    history = InMemoryHistory()
    history.append_string("alpha beta gamma delta")
    history.append_string("one two three four")
    return history


# Test yank_last_arg.


def test_empty_history() -> None:
    """Test yank with empty history."""
    buf = Buffer()
    buf.yank_last_arg()
    assert buf.document.current_line == ""


def test_simple_search(history: InMemoryHistory) -> None:
    """Test simple yank last arg."""
    buff = Buffer(history=history)
    buff.yank_last_arg()
    assert buff.document.current_line == "four"


def test_simple_search_with_quotes(history: InMemoryHistory) -> None:
    """Test yank last arg with quoted strings."""
    history.append_string("""one two "three 'x' four"\n""")
    buff = Buffer(history=history)
    buff.yank_last_arg()
    assert buff.document.current_line == '''"three 'x' four"'''


def test_simple_search_with_arg(history: InMemoryHistory) -> None:
    """Test yank last arg with specific argument index."""
    buff = Buffer(history=history)
    buff.yank_last_arg(n=2)
    assert buff.document.current_line == "three"


def test_simple_search_with_arg_out_of_bounds(history: InMemoryHistory) -> None:
    """Test yank last arg with out of bounds index."""
    buff = Buffer(history=history)
    buff.yank_last_arg(n=8)
    assert buff.document.current_line == ""


def test_repeated_search(history: InMemoryHistory) -> None:
    """Test repeated yank last arg."""
    buff = Buffer(history=history)
    buff.yank_last_arg()
    buff.yank_last_arg()
    assert buff.document.current_line == "delta"


def test_repeated_search_with_wraparound(history: InMemoryHistory) -> None:
    """Test repeated yank last arg with wraparound."""
    buff = Buffer(history=history)
    buff.yank_last_arg()
    buff.yank_last_arg()
    buff.yank_last_arg()
    assert buff.document.current_line == "four"


# Test yank_last_arg.


def test_yank_nth_arg(history: InMemoryHistory) -> None:
    """Test yank nth arg."""
    buff = Buffer(history=history)
    buff.yank_nth_arg()
    assert buff.document.current_line == "two"


def test_repeated_yank_nth_arg(history: InMemoryHistory) -> None:
    """Test repeated yank nth arg."""
    buff = Buffer(history=history)
    buff.yank_nth_arg()
    buff.yank_nth_arg()
    assert buff.document.current_line == "beta"


def test_yank_nth_arg_with_arg(history: InMemoryHistory) -> None:
    """Test yank nth arg with specific index."""
    buff = Buffer(history=history)
    buff.yank_nth_arg(n=2)
    assert buff.document.current_line == "three"
