"""Unit tests for euporie.apptk.eventloop.utils module."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import pytest

from euporie.apptk.eventloop import utils as async_utils

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def reset_loops_threads() -> Generator[None, None, None]:
    """Clean up internal state between tests.

    Yields:
        None

    """
    async_utils._LOOPS.clear()
    async_utils._THREADS.clear()
    yield
    async_utils._LOOPS.clear()
    async_utils._THREADS.clear()


async def sample_coro(value: int) -> int:
    """Define a simple coroutine for testing.

    Args:
        value: The value to return after a short delay

    Returns:
        The input value

    """
    await asyncio.sleep(0.01)
    return value


def test_get_or_create_loop_returns_same_loop() -> None:
    """Test that get_or_create_loop returns the same loop for the same name."""
    loop1 = async_utils.get_or_create_loop("test")
    loop2 = async_utils.get_or_create_loop("test")
    assert loop1 is loop2
    assert "test" in async_utils._LOOPS
    assert "test" in async_utils._THREADS


def test_get_or_create_loop_creates_new_thread_for_new_name() -> None:
    """Test that get_or_create_loop creates separate loops for different names."""
    loop1 = async_utils.get_or_create_loop("one")
    loop2 = async_utils.get_or_create_loop("two")
    assert loop1 is not loop2
    assert set(async_utils._THREADS.keys()) == {"one", "two"}


def test_get_or_create_loop_thread_names() -> None:
    """Test that background threads have correct names."""
    async_utils.get_or_create_loop("kernel")
    async_utils.get_or_create_loop("lsp")

    thread_names = {t.name for t in async_utils._THREADS.values()}
    assert "EuporieKernelLoop" in thread_names
    assert "EuporieLspLoop" in thread_names


def test_get_or_create_loop_pyodide(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_or_create_loop returns main loop in Pyodide."""
    monkeypatch.setattr(sys, "platform", "emscripten")

    # Ensure a loop is set for Python 3.12+
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)

    loop = asyncio.get_event_loop()
    result = async_utils.get_or_create_loop("anything")
    assert result is loop
    # Should not spawn threads in Pyodide
    assert "anything" not in async_utils._THREADS


def test_run_coro_sync_with_given_loop() -> None:
    """Test run_coro_sync executes coroutine synchronously with provided loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = async_utils.run_coro_sync(sample_coro(5), loop)
        assert result == 5
    finally:
        loop.close()


def test_run_coro_sync_raises_if_no_loop() -> None:
    """Test run_coro_sync raises RuntimeError when no loop is available."""
    # Ensure no event loop is running
    try:
        asyncio.get_running_loop()
        pytest.skip("Cannot test without loop when loop is already running")
    except RuntimeError:
        pass

    coro = sample_coro(5)
    try:
        with pytest.raises(
            RuntimeError, match="run_coro_sync requires a loop argument"
        ):
            async_utils.run_coro_sync(coro)
    finally:
        coro.close()  # Ensure coroutine is closed to prevent warnings


def test_run_coro_sync_pyodide(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_coro_sync works correctly in Pyodide environment."""
    monkeypatch.setattr(sys, "platform", "emscripten")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = async_utils.run_coro_sync(sample_coro(7), loop)
        assert result == 7
    finally:
        loop.close()


def test_run_coro_async_normal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_coro_async schedules coroutines correctly in normal Python."""
    monkeypatch.setattr(sys, "platform", "linux")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    results: list[int] = []

    def callback(val: int) -> None:
        results.append(val)

    try:
        fut = async_utils.run_coro_async(sample_coro(42), loop, callback=callback)
        loop.run_until_complete(fut)
        assert fut.result() == 42
        assert results == [42]
    finally:
        loop.close()


def test_run_coro_async_cancel_previous(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_coro_async cancels previous tasks when requested."""
    monkeypatch.setattr(sys, "platform", "linux")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    prev_tasks: dict[str, asyncio.Future] = {}

    try:
        fut1 = async_utils.run_coro_async(
            sample_coro(1), loop, previous_tasks=prev_tasks
        )
        # Schedule new task with cancel_previous=True
        fut2 = async_utils.run_coro_async(
            sample_coro(2),
            loop,
            cancel_previous=True,
            previous_tasks=prev_tasks,
        )

        # First future should be cancelled
        assert fut1.cancelled() or fut1.done()

        loop.run_until_complete(fut2)
        assert fut2.result() == 2
    finally:
        loop.close()


def test_run_coro_async_previous_tasks_tracking() -> None:
    """Test that previous_tasks dict correctly tracks scheduled tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    prev_tasks: dict[str, asyncio.Future] = {}

    try:
        fut = async_utils.run_coro_async(
            sample_coro(10), loop, previous_tasks=prev_tasks
        )
        assert "sample_coro" in prev_tasks
        assert prev_tasks["sample_coro"] is fut

        loop.run_until_complete(fut)
    finally:
        loop.close()


def test_run_coro_async_pyodide(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_coro_async works correctly in Pyodide environment."""
    monkeypatch.setattr(sys, "platform", "emscripten")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    results: list[int] = []

    try:
        fut = async_utils.run_coro_async(
            sample_coro(123), loop, callback=lambda x: results.append(x)
        )
        loop.run_until_complete(fut)
        assert fut.result() == 123
        assert results == [123]
    finally:
        loop.close()


def test_run_coro_async_without_callback() -> None:
    """Test run_coro_async works without a callback."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        fut = async_utils.run_coro_async(sample_coro(99), loop)
        loop.run_until_complete(fut)
        assert fut.result() == 99
    finally:
        loop.close()
