"""Tests for history functionality."""

from __future__ import annotations

from asyncio import run
from typing import Any

from apptk.history import FileHistory, InMemoryHistory, ThreadedHistory


def _call_history_load(history: Any) -> list[str]:
    """Call the history load method and return the result as a list of strings."""
    result = []

    async def call_load() -> None:
        async for item in history.load():
            result.append(item)

    run(call_load())
    return result


def test_in_memory_history() -> None:
    """Test in-memory history functionality."""
    history = InMemoryHistory()
    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Passing history as a parameter.
    history2 = InMemoryHistory(["abc", "def"])
    assert _call_history_load(history2) == ["def", "abc"]


def test_file_history(tmpdir: Any) -> None:
    """Test file-based history functionality."""
    histfile = tmpdir.join("history")

    history = FileHistory(histfile)

    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Create another history instance pointing to the same file.
    history2 = FileHistory(histfile)
    assert _call_history_load(history2) == ["test3", "world", "hello"]


def test_threaded_file_history(tmpdir: Any) -> None:
    """Test threaded file history functionality."""
    histfile = tmpdir.join("history")

    history = ThreadedHistory(FileHistory(histfile))

    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Create another history instance pointing to the same file.
    history2 = ThreadedHistory(FileHistory(histfile))
    assert _call_history_load(history2) == ["test3", "world", "hello"]


def test_threaded_in_memory_history() -> None:
    """Test threaded in-memory history functionality."""
    # Threaded in memory history is not useful. But testing it anyway, just to
    # see whether everything plays nicely together.
    history = ThreadedHistory(InMemoryHistory())
    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Passing history as a parameter.
    history2 = ThreadedHistory(InMemoryHistory(["abc", "def"]))
    assert _call_history_load(history2) == ["def", "abc"]
