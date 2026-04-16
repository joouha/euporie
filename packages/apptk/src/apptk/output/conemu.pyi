from typing import Any, TextIO

from .color_depth import ColorDepth

__all__ = [
    "ConEmuOutput",
]

class ConEmuOutput:
    win32_output: TextIO
    vt100_output: TextIO
    def __init__(
        self,
        stdout: TextIO,
        default_color_depth: ColorDepth | None = None,
    ) -> None: ...
    @property
    def responds_to_cpr(self) -> bool: ...
    def __getattr__(self, name: str) -> Any: ...
