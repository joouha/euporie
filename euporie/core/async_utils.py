"""Shared asyncio event loop management for Euporie subsystems."""

from __future__ import annotations

import asyncio
import sys
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from concurrent.futures import Future as CFuture
    from typing import Any, TypeVar

    T = TypeVar("T")

_LOOPS: dict[str, asyncio.AbstractEventLoop] = {}
_THREADS: dict[str, threading.Thread] = {}


def get_or_create_loop(name: str) -> asyncio.AbstractEventLoop:
    """Get or create an event loop for a given subsystem name.

    In Pyodide, always returns the main event loop without spawning threads.
    In normal Python, creates one background thread per unique name.

    Args:
        name: The subsystem name (e.g., "kernel", "convert", "lsp")

    Returns:
        An asyncio event loop for the named subsystem

    """
    # In Pyodide, always use the main event loop
    if sys.platform == "emscripten":
        return asyncio.get_event_loop()

    # Check if we already have a loop for this name
    if name in _LOOPS:
        return _LOOPS[name]

    # Create a new event loop and thread
    loop = asyncio.new_event_loop()
    _LOOPS[name] = loop

    def _run_loop() -> None:
        """Set the loop and run it forever."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(
        target=_run_loop,
        name=f"Euporie{name.capitalize()}Loop",
        daemon=True,
    )
    thread.start()
    _THREADS[name] = thread

    return loop


def run_coro_sync(
    coro: Coroutine[Any, Any, T],
    loop: asyncio.AbstractEventLoop | None = None,
) -> T:
    """Run a coroutine synchronously from a sync context.

    In Pyodide, where the main loop is already running, this yields control
    back to the event loop repeatedly until the coroutine completes.

    In normal Python with a background loop, this uses run_coroutine_threadsafe.

    Args:
        coro: The coroutine to run
        loop: The event loop to run on (if None, uses current running loop or raises)

    Returns:
        The result of the coroutine

    Raises:
        RuntimeError: If no loop is provided and none is running

    """
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            raise RuntimeError(
                "run_coro_sync requires a loop argument when not in an async context"
            ) from exc

    # In Pyodide, the main loop is already running
    if sys.platform == "emscripten":
        # We're in sync code but the loop is running in the same thread
        # Create a task and yield control until it completes
        task = asyncio.ensure_future(coro, loop=loop)
        while not task.done():
            loop.run_until_complete(asyncio.sleep(0))
        return task.result()

    # Check if the loop is running (in another thread)
    if loop.is_running():
        # Loop is running in a background thread, use threadsafe scheduling
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        # Loop is not running, run it directly in this thread
        return loop.run_until_complete(coro)


def run_coro_async(
    coro: Coroutine[Any, Any, T],
    loop: asyncio.AbstractEventLoop,
    *,
    cancel_previous: bool = False,
    previous_tasks: dict[str, asyncio.Future] | None = None,
    callback: Callable[[T], None] | None = None,
) -> asyncio.Future[T]:
    """Schedule a coroutine on a loop from any context, returning a Future.

    Handles both normal Python (background thread loop) and Pyodide (main loop)
    scheduling transparently.

    Args:
        coro: The coroutine to schedule
        loop: The event loop to run on
        cancel_previous: If True, cancel any previous task for this coroutine
        previous_tasks: Dict to track and optionally cancel previous tasks by name
        callback: Optional callback to run when the coroutine completes

    Returns:
        A Future that will contain the result

    """
    # Cancel previous task if requested
    if cancel_previous and previous_tasks and coro.__name__ in previous_tasks:
        previous_tasks[coro.__name__].cancel()

    # In Pyodide, create a task directly on the main loop
    if sys.platform == "emscripten":
        task = loop.create_task(coro)
        if previous_tasks is not None:
            previous_tasks[coro.__name__] = task
        if callback:
            task.add_done_callback(lambda f: callback(f.result()))
        return task

    # In normal Python, use threadsafe scheduling
    cfut: CFuture[T] = asyncio.run_coroutine_threadsafe(coro, loop)
    fut: asyncio.Future[T] = asyncio.wrap_future(cfut, loop=loop)
    if previous_tasks is not None:
        previous_tasks[coro.__name__] = fut
    if callback:
        fut.add_done_callback(lambda f: callback(f.result()))
    return fut
