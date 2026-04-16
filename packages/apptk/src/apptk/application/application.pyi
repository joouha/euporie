import asyncio
import contextvars
import logging
import signal
import threading
from asyncio import (
    AbstractEventLoop,
    Future,
    Task,
)
from collections.abc import Callable, Coroutine, Hashable
from contextlib import AbstractContextManager
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    overload,
)

from apptk.buffer import Buffer
from apptk.cache import SimpleCache
from apptk.clipboard import Clipboard
from apptk.cursor_shapes import AnyCursorShapeConfig
from apptk.data_structures import Point
from apptk.enums import EditingMode
from apptk.eventloop import (
    InputHook,
)
from apptk.filters import Filter, FilterOrBool
from apptk.formatted_text import AnyFormattedText
from apptk.input.base import Input
from apptk.key_binding.bindings.page_navigation import load_page_navigation_bindings
from apptk.key_binding.defaults import load_key_bindings
from apptk.key_binding.emacs_state import EmacsState
from apptk.key_binding.helix_state import HelixState
from apptk.key_binding.key_bindings import (
    Binding,
    KeyBindingsBase,
    KeysTuple,
)
from apptk.key_binding.key_processor import KeyPressEvent, KeyProcessor
from apptk.key_binding.micro_state import MicroState
from apptk.key_binding.vi_state import ViState
from apptk.layout.containers import Window
from apptk.layout.controls import UIControl
from apptk.layout.layout import Layout
from apptk.output import ColorDepth, Output
from apptk.renderer import Renderer
from apptk.search import SearchState
from apptk.styles import (
    BaseStyle,
    StyleTransformation,
)
from apptk.utils import Event

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.key_binding import KeyBindingsBase
    from apptk.layout import UIControl
    from apptk.layout.screen import WritePosition

E = KeyPressEvent
_AppResult = TypeVar("_AppResult")
ApplicationEventHandler = Callable[["Application[_AppResult]"], None]
_SIGWINCH = getattr(signal, "SIGWINCH", None)
_SIGTSTP = getattr(signal, "SIGTSTP", None)
log = logging.getLogger(__name__)

__all__ = [
    "Application",
]

def attach_winch_signal_handler(
    handler: Callable[[], None],
) -> AbstractContextManager[None]: ...

class Application(Generic[_AppResult]):
    style: BaseStyle | None
    style_transformation: StyleTransformation | None
    key_bindings: KeyBindingsBase | None
    _default_bindings = load_key_bindings()
    _page_navigation_bindings = load_page_navigation_bindings()
    layout: Layout | None
    clipboard: Clipboard | None
    full_screen: bool
    _color_depth: ColorDepth | Callable[[], ColorDepth | None] | None
    mouse_support: FilterOrBool
    paste_mode: FilterOrBool
    editing_mode: EditingMode
    erase_when_done: bool
    reverse_vi_search_direction: FilterOrBool
    enable_page_navigation_bindings: None | FilterOrBool
    min_redraw_interval: float | int | None
    max_render_postpone_time: float | int | None
    refresh_interval: float | None
    terminal_size_polling_interval: float | None
    cursor: AnyCursorShapeConfig
    on_invalidate: Event
    on_reset: Event
    before_render: Event
    after_render: Event
    output: Output | None
    input: Input | None
    pre_run_callables: list[Callable[[], None]]
    _is_running = False
    future: Future[_AppResult] | None
    loop: AbstractEventLoop | None
    _loop_thread: threading.Thread | None
    context: contextvars.Context | None
    quoted_insert = False
    vi_state: ViState
    emacs_state: EmacsState
    ttimeoutlen = 0.5
    timeoutlen = 1.0
    _merged_style: FilterOrBool
    renderer: Renderer
    render_counter = 0
    _invalidated = False
    _invalidate_events: list[Event[object]]
    _last_redraw_time = 0.0
    key_processor: KeyProcessor
    _running_in_terminal = False
    _running_in_terminal_f: Future[None] | None
    exit_style = ""
    _background_tasks: set[Task[None]]
    micro_state: MicroState
    helix_state: HelixState
    on_color_change: Event
    leave_graphics: FilterOrBool
    set_title: bool
    mouse_limits: WritePosition | None
    mouse_position: Point
    _title: str
    def __init__(
        self,
        layout: Layout | None = None,
        style: BaseStyle | None = None,
        include_default_pygments_style: FilterOrBool = True,
        style_transformation: StyleTransformation | None = None,
        key_bindings: KeyBindingsBase | None = None,
        clipboard: Clipboard | None = None,
        full_screen: bool = False,
        color_depth: ColorDepth | Callable[[], ColorDepth | None] | None = None,
        mouse_support: FilterOrBool = False,
        enable_page_navigation_bindings: None | FilterOrBool = None,
        paste_mode: FilterOrBool = False,
        editing_mode: EditingMode = EditingMode.MICRO,
        erase_when_done: bool = False,
        reverse_vi_search_direction: FilterOrBool = False,
        min_redraw_interval: float | int | None = None,
        max_render_postpone_time: float | int | None = 0.01,
        refresh_interval: float | None = None,
        terminal_size_polling_interval: float | None = 0.5,
        cursor: AnyCursorShapeConfig = None,
        on_reset: ApplicationEventHandler[_AppResult] | None = None,
        on_invalidate: ApplicationEventHandler[_AppResult] | None = None,
        before_render: ApplicationEventHandler[_AppResult] | None = None,
        after_render: ApplicationEventHandler[_AppResult] | None = None,
        on_color_change: ApplicationEventHandler[_AppResult] | None = None,
        input: Input | None = None,
        output: Output | None = None,
        title: str | None = None,
        set_title: bool = True,
        leave_graphics: FilterOrBool = True,
    ) -> None: ...
    def _create_merged_style(
        self, include_default_pygments_style: Filter
    ) -> BaseStyle: ...
    @property
    def color_depth(self) -> ColorDepth: ...
    @property
    def current_buffer(self) -> Buffer: ...
    @property
    def current_search_state(self) -> SearchState: ...
    def reset(self) -> None: ...
    def invalidate(self) -> None: ...
    @property
    def invalidated(self) -> bool: ...
    def _redraw(self, render_as_done: bool = False) -> None: ...
    def _start_auto_refresh_task(self) -> None: ...
    def _update_invalidate_events(self) -> None: ...
    def _invalidate_handler(self, sender: object) -> None: ...
    def _on_resize(self) -> None: ...
    def _pre_run(self, pre_run: Callable[[], None] | None = None) -> None: ...
    async def run_async(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        slow_callback_duration: float = 0.5,
    ) -> _AppResult: ...
    def run(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        in_thread: bool = False,
        inputhook: InputHook | None = None,
    ) -> _AppResult: ...
    def _handle_exception(
        self,
        loop: AbstractEventLoop,
        context: dict[str, Any],
    ) -> None: ...
    def _enable_breakpointhook(self) -> AbstractContextManager[None]: ...
    def _breakpointhook(self, *a: object, **kw: object) -> None: ...
    def create_background_task(
        self,
        coroutine: Coroutine[Any, Any, None],
    ) -> asyncio.Task[None]: ...
    def _on_background_task_done(self, task: asyncio.Task[None]) -> None: ...
    async def cancel_and_wait_for_background_tasks(self) -> None: ...
    async def _poll_output_size(self) -> None: ...
    def cpr_not_supported_callback(self) -> None: ...
    @overload
    def exit(self) -> None: ...
    @overload
    def exit(self, *, result: _AppResult, style: str = "") -> None: ...
    @overload
    def exit(
        self,
        *,
        exception: BaseException | type[BaseException],
        style: str = "",
    ) -> None: ...
    def exit(
        self,
        result: _AppResult | None = None,
        exception: BaseException | type[BaseException] | None = None,
        style: str = "",
    ) -> None: ...
    def _request_absolute_cursor_position(self) -> None: ...
    async def run_system_command(
        self,
        command: str,
        wait_for_enter: bool = True,
        display_before_text: AnyFormattedText = "",
        wait_text: str = "Press ENTER to continue...",
    ) -> None: ...
    def suspend_to_background(self, suspend_group: bool = True) -> None: ...
    def print_text(
        self, text: AnyFormattedText, style: BaseStyle | None = None
    ) -> None: ...
    @property
    def is_running(self) -> bool: ...
    @property
    def is_done(self) -> bool: ...
    def get_used_style_strings(self) -> list[str]: ...
    @property
    def title(self) -> str: ...
    @title.setter
    def title(self, value: str) -> None: ...
    def get_comment_prefix(self, language: str | None) -> str: ...
    def _drain_pending_input(self) -> None: ...

class _CombinedRegistry(Generic[_AppResult]):
    app: Application[_AppResult]
    _cache: SimpleCache[tuple[Window, frozenset[UIControl]], KeyBindingsBase]
    handler_keys = {}
    def __init__(self, app: Application[_AppResult]) -> None: ...
    @property
    def _version(self) -> Hashable: ...
    @property
    def bindings(self) -> list[Binding]: ...
    def _create_key_bindings(
        self,
        current_window: Window,
        other_controls: list[UIControl],
    ) -> KeyBindingsBase: ...
    @property
    def _key_bindings(self) -> KeyBindingsBase: ...
    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]: ...
    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]: ...
