from typing import TYPE_CHECKING, ContextManager, TextIO

from .base import Input, PipeInput

if TYPE_CHECKING:
    from apptk.input.base import Input

__all__ = [
    "create_input",
    "create_pipe_input",
]

def create_input(
    stdin: TextIO | None = None, always_prefer_tty: bool = False
) -> Input: ...
def create_pipe_input() -> ContextManager[PipeInput]: ...
