import datetime
import signal
import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import (
    Generic,
    TextIO,
    TypeVar,
)

from apptk.application import Application
from apptk.formatted_text import AnyFormattedText
from apptk.input import Input
from apptk.key_binding import KeyBindings
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.layout.controls import UIContent, UIControl
from apptk.output import ColorDepth, Output
from apptk.styles import BaseStyle

from .formatters import Formatter

E = KeyPressEvent
_SIGWINCH = getattr(signal, "SIGWINCH", None)
_T = TypeVar("_T")
_CounterItem = TypeVar("_CounterItem", covariant=True)

__all__ = [
    "ProgressBar",
]

def create_key_bindings(cancel_callback: Callable[[], None] | None) -> KeyBindings: ...

class ProgressBar(Generic[_T]):
    title: AnyFormattedText
    formatters: Sequence[Formatter] | None
    bottom_toolbar: AnyFormattedText
    counters: list[ProgressBarCounter[object]]
    style: BaseStyle | None
    key_bindings: KeyBindings | None
    cancel_callback: Callable[[], None] | None
    color_depth: ColorDepth | None
    output: Output | None
    input: Input | None
    _thread: threading.Thread | None
    _has_sigwinch = False
    _app_started: threading.Event
    app: Application[None]
    def __init__(
        self,
        title: AnyFormattedText = None,
        formatters: Sequence[Formatter] | None = None,
        bottom_toolbar: AnyFormattedText = None,
        style: BaseStyle | None = None,
        key_bindings: KeyBindings | None = None,
        cancel_callback: Callable[[], None] | None = None,
        file: TextIO | None = None,
        color_depth: ColorDepth | None = None,
        output: Output | None = None,
        input: Input | None = None,
    ) -> None: ...
    def invalidate(self) -> None: ...
    def __call__(
        self,
        data: Iterable[_T] | None = None,
        label: AnyFormattedText = "",
        remove_when_done: bool = False,
        total: int | None = None,
    ) -> ProgressBarCounter[_T]: ...
    def __enter__(self) -> ProgressBar: ...
    def __exit__(self, *a: object) -> None: ...

class _ProgressControl(UIControl):
    progress_bar: ProgressBar
    formatter: Formatter
    _key_bindings: Callable[[], None] | None
    def __init__(
        self,
        progress_bar: ProgressBar,
        formatter: Formatter,
        cancel_callback: Callable[[], None] | None,
    ) -> None: ...
    def create_content(self, width: int, height: int) -> UIContent: ...
    def is_focusable(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindings: ...

class ProgressBarCounter(Generic[_CounterItem]):
    start_time = datetime.datetime.now()
    stop_time: datetime.datetime | None
    progress_bar: ProgressBar
    data: Iterable[_CounterItem] | None
    items_completed = 0
    label: AnyFormattedText
    remove_when_done: bool
    _done = False
    total: int | None
    def __init__(
        self,
        progress_bar: ProgressBar,
        data: Iterable[_CounterItem] | None = None,
        label: AnyFormattedText = "",
        remove_when_done: bool = False,
        total: int | None = None,
    ) -> None: ...
    def item_completed(self) -> None: ...
    @property
    def done(self) -> bool: ...
    @done.setter
    def done(self, value: bool) -> None: ...
    @property
    def stopped(self) -> bool: ...
    @stopped.setter
    def stopped(self, value: bool) -> None: ...
    @property
    def percentage(self) -> float: ...
    @property
    def time_elapsed(self) -> datetime.timedelta: ...
    @property
    def time_left(self) -> datetime.timedelta | None: ...
    def __iter__(self) -> Iterator[_CounterItem]: ...
