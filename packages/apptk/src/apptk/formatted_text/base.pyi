from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Union

from apptk.mouse_events import MouseEvent

if TYPE_CHECKING:
    from typing import TypeGuard

    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from typing_extensions import Protocol

OneStyleAndTextTuple = Union[
    tuple[str, str], tuple[str, str, Callable[[MouseEvent], "NotImplementedOrNone"]]
]
StyleAndTextTuples = list[OneStyleAndTextTuple]
AnyFormattedText = Union[
    str,
    "MagicFormattedText",
    StyleAndTextTuples,
    # Callable[[], 'AnyFormattedText']  # Recursive definition not supported by mypy.
    Callable[[], Any],
    None,
]

__all__ = [
    "AnyFormattedText",
    "FormattedText",
    "MagicFormattedText",
    "OneStyleAndTextTuple",
    "StyleAndTextTuples",
    "Template",
    "is_formatted_text",
    "merge_formatted_text",
    "to_formatted_text",
]

class FormattedText(StyleAndTextTuples):
    def __pt_formatted_text__(self) -> StyleAndTextTuples: ...
    def __repr__(self) -> str: ...

def to_formatted_text(
    value: AnyFormattedText,
    style: str = "",
    auto_convert: bool = False,
) -> FormattedText: ...
def is_formatted_text(value: object) -> TypeGuard[AnyFormattedText]: ...
def merge_formatted_text(items: Iterable[AnyFormattedText]) -> AnyFormattedText: ...

class MagicFormattedText(Protocol):
    def __pt_formatted_text__(self) -> StyleAndTextTuples: ...

class Template:
    text: str
    def __init__(self, text: str) -> None: ...
    def format(self, *values: AnyFormattedText) -> AnyFormattedText: ...
