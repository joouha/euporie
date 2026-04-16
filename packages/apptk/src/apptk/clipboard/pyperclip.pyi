import logging
from typing import TYPE_CHECKING

from .base import ClipboardData

if TYPE_CHECKING:
    from apptk.clipboard.base import ClipboardData

log = logging.getLogger(__name__)

__all__ = [
    "PyperclipClipboard",
]

class PyperclipClipboard:
    _data: ClipboardData
    def __init__(self) -> None: ...
    def set_data(self, data: ClipboardData) -> None: ...
    def get_data(self) -> ClipboardData: ...
