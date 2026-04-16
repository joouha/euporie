from collections.abc import AsyncGenerator, Callable, Iterable
from contextlib import AbstractAsyncContextManager
from typing import Any, TypeVar

_T_Generator = TypeVar("_T_Generator", bound=AsyncGenerator[Any])
DEFAULT_BUFFER_SIZE: int = 1000
_T = TypeVar("_T")

__all__ = [
    "aclosing",
    "generator_to_async_generator",
]

async def aclosing(
    thing: _T_Generator,
) -> AbstractAsyncContextManager[_T_Generator]: ...
async def generator_to_async_generator(
    get_iterable: Callable[[], Iterable[_T]],
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> AsyncGenerator[_T]: ...

class _Done: ...
