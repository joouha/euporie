from collections.abc import Callable, Sequence
from typing import TypeVar

from apptk.application import Application
from apptk.completion import Completer
from apptk.filters import FilterOrBool
from apptk.formatted_text import AnyFormattedText
from apptk.styles import BaseStyle
from apptk.validation import Validator

_T = TypeVar("_T")

__all__ = [
    "button_dialog",
    "checkboxlist_dialog",
    "input_dialog",
    "message_dialog",
    "progress_dialog",
    "radiolist_dialog",
    "yes_no_dialog",
]

def yes_no_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    yes_text: str = "Yes",
    no_text: str = "No",
    style: BaseStyle | None = None,
) -> Application[bool]: ...
def button_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    buttons: list[tuple[str, _T]] = [],
    style: BaseStyle | None = None,
) -> Application[_T]: ...
def input_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "OK",
    cancel_text: str = "Cancel",
    completer: Completer | None = None,
    validator: Validator | None = None,
    password: FilterOrBool = False,
    style: BaseStyle | None = None,
    default: str = "",
) -> Application[str]: ...
def message_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "Ok",
    style: BaseStyle | None = None,
) -> Application[None]: ...
def radiolist_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "Ok",
    cancel_text: str = "Cancel",
    values: Sequence[tuple[_T, AnyFormattedText]] | None = None,
    default: _T | None = None,
    style: BaseStyle | None = None,
) -> Application[_T]: ...
def checkboxlist_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "Ok",
    cancel_text: str = "Cancel",
    values: Sequence[tuple[_T, AnyFormattedText]] | None = None,
    default_values: Sequence[_T] | None = None,
    style: BaseStyle | None = None,
) -> Application[list[_T]]: ...
def progress_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    run_callback: Callable[
        [Callable[[int], None], Callable[[str], None]], None
    ] = lambda *a: None,
    style: BaseStyle | None = None,
) -> Application[None]: ...
