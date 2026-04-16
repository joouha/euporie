from ctypes.wintypes import HANDLE
from typing import Any, TextIO

from .color_depth import ColorDepth

ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

__all__ = [
    "Windows10_Output",
]

def is_win_vt100_enabled() -> bool: ...

class Windows10_Output:
    default_color_depth: ColorDepth | None
    win32_output: TextIO
    vt100_output: TextIO
    _hconsole: HANDLE
    def __init__(
        self,
        stdout: TextIO,
        default_color_depth: ColorDepth | None = None,
    ) -> None: ...
    def flush(self) -> None: ...
    @property
    def responds_to_cpr(self) -> bool: ...
    def get_default_color_depth(self) -> ColorDepth: ...
    def __getattr__(self, name: str) -> Any: ...
