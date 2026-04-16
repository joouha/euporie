from collections.abc import Callable
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from apptk.buffer import CompletionState
from apptk.completion import Completion
from apptk.filters import FilterOrBool
from apptk.formatted_text import (
    StyleAndTextTuples,
)
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.mouse_events import MouseEvent

from .containers import ConditionalContainer, HSplit
from .controls import GetLinePrefixCallable, UIContent, UIControl

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindings, NotImplementedOrNone

E = KeyPressEvent

__all__ = [
    "CompletionsMenu",
    "MultiColumnCompletionsMenu",
]

class CompletionsMenuControl(UIControl):
    MIN_WIDTH = 7
    def has_focus(self) -> bool: ...
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def create_content(self, width: int, height: int) -> UIContent: ...
    def _show_meta(self, complete_state: CompletionState) -> bool: ...
    def _get_menu_width(
        self, max_width: int, complete_state: CompletionState
    ) -> int: ...
    def _get_menu_meta_width(
        self,
        max_width: int,
        complete_state: CompletionState,
    ) -> int: ...
    def _get_menu_item_meta_fragments(
        self,
        completion: Completion,
        is_current_completion: bool,
        width: int,
    ) -> StyleAndTextTuples: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...

class CompletionsMenu(ConditionalContainer):
    def __init__(
        self,
        max_height: int | None = None,
        scroll_offset: int | Callable[[], int] = 0,
        extra_filter: FilterOrBool = True,
        display_arrows: FilterOrBool = False,
        z_index: int = 10**8,
    ) -> None: ...

class MultiColumnCompletionMenuControl(Generic[_T], UIControl):
    _required_margin = 3  # One extra padding on the right + space for arrows.
    min_rows: int
    suggested_max_column_width: int
    scroll = 0
    _column_width_for_completion_state: WeakKeyDictionary[
        CompletionState, tuple[int, int]
    ]
    _rendered_rows = 0
    _rendered_columns = 0
    _total_columns = 0
    _render_pos_to_completion: dict[tuple[int, int], Completion]
    _render_left_arrow = False
    _render_right_arrow = False
    _render_width = 0
    def __init__(
        self, min_rows: int = 3, suggested_max_column_width: int = 30
    ) -> None: ...
    def reset(self) -> None: ...
    def has_focus(self) -> bool: ...
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def create_content(self, width: int, height: int) -> UIContent: ...
    def _get_column_width(self, completion_state: CompletionState) -> int: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    def get_key_bindings(self) -> KeyBindings: ...

class MultiColumnCompletionsMenu(HSplit):
    def __init__(
        self,
        min_rows: int = 3,
        suggested_max_column_width: int = 30,
        show_meta: FilterOrBool = True,
        extra_filter: FilterOrBool = True,
        z_index: int = 10**8,
    ) -> None: ...

class _SelectedCompletionMetaControl(UIControl):
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def create_content(self, width: int, height: int) -> UIContent: ...
    def _get_text_fragments(self) -> StyleAndTextTuples: ...
