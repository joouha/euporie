from typing import TYPE_CHECKING, TextIO

from .base import Output

if TYPE_CHECKING:
    from apptk.patch_stdout import StdoutProxy

__all__ = [
    "create_output",
]

def create_output(
    stdout: TextIO | StdoutProxy | None = None,
    always_prefer_tty: bool = False,
) -> Output: ...
