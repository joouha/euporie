"""Updated version of the prompt_toolkit caches."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from prompt_toolkit.cache import _T, _U
from prompt_toolkit.cache import SimpleCache as PtkSimpleCache

if TYPE_CHECKING:
    from collections.abc import Callable


__all__ = [
    "SimpleCache",
]


class SimpleCache(PtkSimpleCache[_T, _U]):
    """Thread safe version of :py:`SimpleCache`."""

    def __init__(self, maxsize: int = 8) -> None:
        """Create lock at init."""
        super().__init__(maxsize)
        self._lock = threading.Lock()

    def get(self, key: _T, getter_func: Callable[[], _U]) -> _U:
        """Access cache with thread safety."""
        with self._lock:
            return super().get(key, getter_func)

    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            super().clear()
