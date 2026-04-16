from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import TypeVar

_T = TypeVar("_T")

__all__ = [
    "in_terminal",
    "run_in_terminal",
]

def run_in_terminal(
    func: Callable[[], _T],
    render_cli_done: bool = False,
    in_executor: bool = False,
) -> Awaitable[_T]: ...
async def in_terminal(
    render_cli_done: bool = False,
) -> AbstractAsyncContextManager[None]: ...
