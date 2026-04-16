import asyncio
import threading
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_T = TypeVar("_T")
T = TypeVar("T")
_LOOPS: dict[str, asyncio.AbstractEventLoop] = {}
_THREADS: dict[str, threading.Thread] = {}

__all__ = [
    "call_soon_threadsafe",
    "get_or_create_loop",
    "get_traceback_from_context",
    "run_coro_async",
    "run_coro_sync",
    "run_in_executor_with_context",
]

def run_in_executor_with_context(
    func: Callable[..., _T],
    *args: Any,
    loop: asyncio.AbstractEventLoop | None = None,
) -> Awaitable[_T]: ...
def call_soon_threadsafe(
    func: Callable[[], None],
    max_postpone_time: float | None = None,
    loop: asyncio.AbstractEventLoop | None = None,
) -> None: ...
def get_traceback_from_context(context: dict[str, Any]) -> TracebackType | None: ...
def get_or_create_loop(name: str) -> asyncio.AbstractEventLoop: ...
def run_coro_sync(
    coro: Coroutine[Any, Any, T],
    loop: asyncio.AbstractEventLoop | None = None,
) -> T: ...
def run_coro_async(
    coro: Coroutine[Any, Any, T],
    loop: asyncio.AbstractEventLoop,
    *,
    cancel_previous: bool = False,
    previous_tasks: dict[str, asyncio.Future] | None = None,
    callback: Callable[[T], None] | None = None,
) -> asyncio.Future[T]: ...
