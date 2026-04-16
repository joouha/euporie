from collections.abc import Sequence
from typing import Generic, TypeVar

from apptk.application import Application
from apptk.filters import (
    FilterOrBool,
)
from apptk.formatted_text import AnyFormattedText
from apptk.key_binding.key_bindings import (
    KeyBindingsBase,
)
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.styles import BaseStyle

_T = TypeVar("_T")
E = KeyPressEvent

__all__ = [
    "ChoiceInput",
    "choice",
]

def create_default_choice_input_style() -> BaseStyle: ...
def choice(
    message: AnyFormattedText,
    *,
    options: Sequence[tuple[_T, AnyFormattedText]],
    default: _T | None = None,
    mouse_support: bool = False,
    style: BaseStyle | None = None,
    symbol: str = ">",
    bottom_toolbar: AnyFormattedText = None,
    show_frame: bool = False,
    enable_suspend: FilterOrBool = False,
    enable_interrupt: FilterOrBool = True,
    interrupt_exception: type[BaseException] = KeyboardInterrupt,
    key_bindings: KeyBindingsBase | None = None,
) -> _T: ...

class ChoiceInput(Generic[_T]):
    message: AnyFormattedText
    default: _T | None
    options: Sequence[tuple[_T, AnyFormattedText]]
    mouse_support: bool
    style: BaseStyle | None
    symbol: str
    show_frame: FilterOrBool
    enable_suspend: FilterOrBool
    interrupt_exception: type[BaseException]
    enable_interrupt: FilterOrBool
    bottom_toolbar: AnyFormattedText
    key_bindings: KeyBindingsBase | None
    def __init__(
        self,
        *,
        message: AnyFormattedText,
        options: Sequence[tuple[_T, AnyFormattedText]],
        default: _T | None = None,
        mouse_support: bool = False,
        style: BaseStyle | None = None,
        symbol: str = ">",
        bottom_toolbar: AnyFormattedText = None,
        show_frame: FilterOrBool = False,
        enable_suspend: FilterOrBool = False,
        enable_interrupt: FilterOrBool = True,
        interrupt_exception: type[BaseException] = KeyboardInterrupt,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None: ...
    def _create_application(self) -> Application[_T]: ...
    def prompt(self) -> _T: ...
    async def prompt_async(self) -> _T: ...
