from collections import deque

from .base import Clipboard, ClipboardData

__all__ = [
    "InMemoryClipboard",
]

class InMemoryClipboard(Clipboard):
    max_size: int
    _ring: deque[ClipboardData]
    def __init__(
        self, data: ClipboardData | None = None, max_size: int = 60
    ) -> None: ...
    def set_data(self, data: ClipboardData) -> None: ...
    def get_data(self) -> ClipboardData: ...
    def rotate(self) -> None: ...
