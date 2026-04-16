import asyncio
import logging
import re
from collections import deque
from collections.abc import Callable, Coroutine, Iterable
from enum import Enum
from typing import Any, TypeVar

from .auto_suggest import AutoSuggest, Suggestion
from .cache import FastDictCache
from .clipboard import ClipboardData
from .completion import (
    CompleteEvent,
    Completer,
    Completion,
)
from .document import Document
from .filters import FilterOrBool
from .history import History, InMemoryHistory
from .search import SearchState
from .selection import PasteMode, SelectionState, SelectionType
from .utils import Event
from .validation import ValidationError, Validator

logger = logging.getLogger(__name__)
_QUOTED_WORDS_RE = re.compile(r"""(\s+|".*?"|'.*?')""")
BufferEventHandler = Callable[["Buffer"], None]
BufferAcceptHandler = Callable[["Buffer"], bool]
_T = TypeVar("_T", bound=Callable[..., Coroutine[Any, Any, None]])

__all__ = [
    "Buffer",
    "CompletionState",
    "EditReadOnlyBuffer",
    "indent",
    "reshape_text",
    "unindent",
]

def indent(buffer: Buffer, from_row: int, to_row: int, count: int = 1) -> None: ...
def unindent(buffer: Buffer, from_row: int, to_row: int, count: int = 1) -> None: ...
def reshape_text(buffer: Buffer, from_row: int, to_row: int) -> None: ...

class EditReadOnlyBuffer(Exception): ...

class ValidationState(Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"

class CompletionState:
    original_document: Document
    completions: list[Completion] | None
    complete_index: int | None
    def __init__(
        self,
        original_document: Document,
        completions: list[Completion] | None = None,
        complete_index: int | None = None,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def go_to_index(self, index: int | None) -> None: ...
    def new_text_and_position(self) -> tuple[str, int]: ...
    @property
    def current_completion(self) -> Completion | None: ...

class YankNthArgState:
    history_position: int
    previous_inserted_word: str
    n: int
    def __init__(
        self,
        history_position: int = 0,
        n: int = -1,
        previous_inserted_word: str = "",
    ) -> None: ...
    def __repr__(self) -> str: ...

class Buffer:
    completer: Completer | None
    auto_suggest: AutoSuggest | None
    validator: Validator | None
    tempfile_suffix: str | Callable[[], str]
    tempfile: str | Callable[[], str]
    name: str
    accept_handler: BufferAcceptHandler | None
    complete_while_typing: FilterOrBool
    validate_while_typing: FilterOrBool
    enable_history_search: FilterOrBool
    read_only: FilterOrBool
    multiline: FilterOrBool
    max_number_of_completions: int
    text_width = 0
    history: InMemoryHistory
    __cursor_position = 0
    on_text_changed: Event[Buffer]
    on_text_insert: Event[Buffer]
    on_cursor_position_changed: Event[Buffer]
    on_completions_changed: Event[Buffer]
    on_suggestion_set: Event[Buffer]
    _document_cache: FastDictCache[tuple[str, int, SelectionState | None], Document]
    _async_suggester = self._create_auto_suggest_coroutine()
    _async_completer = self._create_completer_coroutine()
    _async_validator = self._create_auto_validate_coroutine()
    _load_history_task: asyncio.Future[None] | None
    validation_error: ValidationError | None
    validation_state: ValidationState | None
    selection_state: SelectionState | None
    multiple_cursor_positions: list[int]
    preferred_column: int | None
    complete_state: CompletionState | None
    yank_nth_arg_state: YankNthArgState | None
    document_before_paste: Document | None
    suggestion: Suggestion | None
    history_search_text: str | None
    _undo_stack: list[tuple[str, int]]
    _redo_stack: list[tuple[str, int]]
    _working_lines: deque[str]
    __working_index = 0
    def __init__(
        self,
        completer: Completer | None = None,
        auto_suggest: AutoSuggest | None = None,
        history: History | None = None,
        validator: Validator | None = None,
        tempfile_suffix: str | Callable[[], str] = "",
        tempfile: str | Callable[[], str] = "",
        name: str = "",
        complete_while_typing: FilterOrBool = False,
        validate_while_typing: FilterOrBool = False,
        enable_history_search: FilterOrBool = False,
        document: Document | None = None,
        accept_handler: BufferAcceptHandler | None = None,
        read_only: FilterOrBool = False,
        multiline: FilterOrBool = True,
        max_number_of_completions: int = 10000,
        on_text_changed: BufferEventHandler | None = None,
        on_text_insert: BufferEventHandler | None = None,
        on_cursor_position_changed: BufferEventHandler | None = None,
        on_completions_changed: BufferEventHandler | None = None,
        on_suggestion_set: BufferEventHandler | None = None,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def reset(
        self,
        document: Document | None = None,
        append_to_history: bool = False,
    ) -> None: ...
    def load_history_if_not_yet_loaded(self) -> None: ...
    def _set_text(self, value: str) -> bool: ...
    def _set_cursor_position(self, value: int) -> bool: ...
    @property
    def text(self) -> str: ...
    @text.setter
    def text(self, value: str) -> None: ...
    @property
    def cursor_position(self) -> int: ...
    @cursor_position.setter
    def cursor_position(self, value: int) -> None: ...
    @property
    def working_index(self) -> int: ...
    @working_index.setter
    def working_index(self, value: int) -> None: ...
    def _text_changed(self) -> None: ...
    def _cursor_position_changed(self) -> None: ...
    @property
    def document(self) -> Document: ...
    @document.setter
    def document(self, value: Document) -> None: ...
    def set_document(self, value: Document, bypass_readonly: bool = False) -> None: ...
    @property
    def is_returnable(self) -> bool: ...
    def save_to_undo_stack(self, clear_redo_stack: bool = True) -> None: ...
    def transform_lines(
        self,
        line_index_iterator: Iterable[int],
        transform_callback: Callable[[str], str],
    ) -> str: ...
    def transform_current_line(
        self, transform_callback: Callable[[str], str]
    ) -> None: ...
    def transform_region(
        self,
        from_: int,
        to: int,
        transform_callback: Callable[[str], str],
    ) -> None: ...
    def cursor_left(self, count: int = 1) -> None: ...
    def cursor_right(self, count: int = 1) -> None: ...
    def cursor_up(self, count: int = 1) -> None: ...
    def cursor_down(self, count: int = 1) -> None: ...
    def auto_up(
        self,
        count: int = 1,
        go_to_start_of_line_if_history_changes: bool = False,
    ) -> None: ...
    def auto_down(
        self,
        count: int = 1,
        go_to_start_of_line_if_history_changes: bool = False,
    ) -> None: ...
    def delete_before_cursor(self, count: int = 1) -> str: ...
    def delete(self, count: int = 1) -> str: ...
    def join_next_line(self, separator: str = " ") -> None: ...
    def join_selected_lines(self, separator: str = " ") -> None: ...
    def swap_characters_before_cursor(self) -> None: ...
    def go_to_history(self, index: int) -> None: ...
    def complete_next(
        self, count: int = 1, disable_wrap_around: bool = False
    ) -> None: ...
    def complete_previous(
        self,
        count: int = 1,
        disable_wrap_around: bool = False,
    ) -> None: ...
    def cancel_completion(self) -> None: ...
    def _set_completions(self, completions: list[Completion]) -> CompletionState: ...
    def start_history_lines_completion(self) -> None: ...
    def go_to_completion(self, index: int | None) -> None: ...
    def apply_completion(self, completion: Completion) -> None: ...
    def _set_history_search(self) -> None: ...
    def _history_matches(self, i: int) -> bool: ...
    def history_forward(self, count: int = 1) -> None: ...
    def history_backward(self, count: int = 1) -> None: ...
    def yank_nth_arg(
        self, n: int | None = None, _yank_last_arg: bool = False
    ) -> None: ...
    def yank_last_arg(self, n: int | None = None) -> None: ...
    def start_selection(
        self,
        selection_type: SelectionType = SelectionType.CHARACTERS,
    ) -> None: ...
    def copy_selection(self, _cut: bool = False) -> ClipboardData: ...
    def cut_selection(self) -> ClipboardData: ...
    def paste_clipboard_data(
        self,
        data: ClipboardData,
        paste_mode: PasteMode = PasteMode.EMACS,
        count: int = 1,
    ) -> None: ...
    def newline(self, copy_margin: bool = True) -> None: ...
    def insert_line_above(self, copy_margin: bool = True) -> None: ...
    def insert_line_below(self, copy_margin: bool = True) -> None: ...
    def insert_text(
        self,
        data: str,
        overwrite: bool = False,
        move_cursor: bool = True,
        fire_event: bool = True,
    ) -> None: ...
    def undo(self) -> None: ...
    def redo(self) -> None: ...
    def validate(self, set_cursor: bool = False) -> bool: ...
    async def _validate_async(self) -> None: ...
    def append_to_history(self) -> None: ...
    def _search(
        self,
        search_state: SearchState,
        include_current_position: bool = False,
        count: int = 1,
    ) -> tuple[int, int] | None: ...
    def document_for_search(self, search_state: SearchState) -> Document: ...
    def get_search_position(
        self,
        search_state: SearchState,
        include_current_position: bool = True,
        count: int = 1,
    ) -> int: ...
    def apply_search(
        self,
        search_state: SearchState,
        include_current_position: bool = True,
        count: int = 1,
    ) -> None: ...
    def exit_selection(self) -> None: ...
    def _editor_simple_tempfile(self) -> tuple[str, Callable[[], None]]: ...
    def _editor_complex_tempfile(self) -> tuple[str, Callable[[], None]]: ...
    def open_in_editor(
        self, validate_and_handle: bool = False
    ) -> asyncio.Task[None]: ...
    def _open_file_in_editor(self, filename: str) -> bool: ...
    def start_completion(
        self,
        select_first: bool = False,
        select_last: bool = False,
        insert_common_part: bool = False,
        complete_event: CompleteEvent | None = None,
    ) -> None: ...
    def _create_completer_coroutine(
        self,
    ) -> Callable[..., Coroutine[Any, Any, None]]: ...
    def _create_auto_suggest_coroutine(
        self,
    ) -> Callable[[], Coroutine[Any, Any, None]]: ...
    def _create_auto_validate_coroutine(
        self,
    ) -> Callable[[], Coroutine[Any, Any, None]]: ...
    def validate_and_handle(self) -> None: ...

class _Retry(Exception): ...
