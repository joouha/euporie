from typing import TYPE_CHECKING, Any, TextIO

from apptk.output import ColorDepth, Output
from apptk.styles import (
    BaseStyle,
    StyleTransformation,
)

if TYPE_CHECKING:
    from apptk.layout.containers import AnyContainer

__all__ = [
    "clear",
    "clear_title",
    "print_container",
    "print_formatted_text",
    "set_title",
]

def print_formatted_text(
    *values: Any,
    sep: str = " ",
    end: str = "\n",
    file: TextIO | None = None,
    flush: bool = False,
    style: BaseStyle | None = None,
    output: Output | None = None,
    color_depth: ColorDepth | None = None,
    style_transformation: StyleTransformation | None = None,
    include_default_pygments_style: bool = True,
) -> None: ...
def print_container(
    container: AnyContainer,
    file: TextIO | None = None,
    style: BaseStyle | None = None,
    include_default_pygments_style: bool = True,
) -> None: ...
def clear() -> None: ...
def set_title(text: str) -> None: ...
def clear_title() -> None: ...
