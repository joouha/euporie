import threading
from collections import deque
from collections.abc import Callable, Hashable
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_T = TypeVar("_T", bound=Hashable)
_U = TypeVar("_U")
_K = TypeVar("_K", bound=tuple[Hashable, ...])
_V = TypeVar("_V")
_F = TypeVar("_F", bound=Callable[..., object])

__all__ = [
    "FastDictCache",
    "SimpleCache",
    "memoized",
]

def memoized(maxsize: int = 1024) -> Callable[[_F], _F]: ...

class SimpleCache(Generic[_T, _U]):
    _data: dict[_T, _U]
    _keys: deque[_T]
    maxsize: int
    _lock: threading.Lock
    def __init__(self, maxsize: int = 8) -> None: ...
    def get(self, key: _T, getter_func: Callable[[], _U]) -> _U: ...
    def clear(self) -> None: ...

class FastDictCache(dict[_K, _V]):
    _keys: deque[_K]
    get_value: Callable[..., _V]
    size: int
    def __init__(self, get_value: Callable[..., _V], size: int = 1000000) -> None: ...
    def __missing__(self, key: _K) -> _V: ...
