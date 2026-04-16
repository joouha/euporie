import logging
from abc import abstractmethod
from collections.abc import Callable, Hashable, Iterable
from typing import TYPE_CHECKING, NamedTuple

from apptk.buffer import Buffer
from apptk.cache import SimpleCache
from apptk.data_structures import Point
from apptk.document import Document
from apptk.filters import FilterOrBool
from apptk.formatted_text import AnyFormattedText, StyleAndTextTuples
from apptk.lexers import Lexer
from apptk.mouse_events import MouseEvent
from apptk.search import SearchState

from .processors import (
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightSearchProcessor,
    HighlightSelectionProcessor,
    Processor,
)

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindingsBase, NotImplementedOrNone
    from apptk.utils import Event

GetLinePrefixCallable = Callable[[int, int], AnyFormattedText]
log = logging.getLogger(__name__)

__all__ = [
    "BufferControl",
    "DummyControl",
    "FocusableDummyControl",
    "FormattedTextControl",
    "GetLinePrefixCallable",
    "SearchBufferControl",
    "UIContent",
    "UIControl",
]

class UIContent:
    get_line: Callable[[int], StyleAndTextTuples]
    line_count: int
    cursor_position: Point | None
    menu_position: Point | None
    show_cursor: bool
    _line_heights_cache: dict[Hashable, int]
    def __init__(
        self,
        get_line: Callable[[int], StyleAndTextTuples] = lambda i: [],
        line_count: int = 0,
        cursor_position: Point | None = None,
        menu_position: Point | None = None,
        show_cursor: bool = True,
    ) -> None: ...
    def get_height_for_line(
        self,
        lineno: int,
        width: int,
        get_line_prefix: GetLinePrefixCallable | None,
        slice_stop: int | None = None,
    ) -> int: ...
    def graphic_positions(self) -> dict[str, Point]: ...
    def __getitem__(self, lineno: int) -> StyleAndTextTuples: ...

class UIControl:
    def reset(self) -> None: ...
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def is_focusable(self) -> bool: ...
    @abstractmethod
    def create_content(self, width: int, height: int) -> UIContent: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    def move_cursor_down(self) -> None: ...
    def move_cursor_up(self) -> None: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_invalidate_events(self) -> Iterable[Event[object]]: ...

class FormattedTextControl(UIControl):
    text: AnyFormattedText
    style: str
    focusable: FilterOrBool
    key_bindings: KeyBindingsBase | None
    show_cursor: bool
    modal: bool
    get_cursor_position: Callable[[], Point | None] | None
    _content_cache: SimpleCache[Hashable, UIContent]
    _fragment_cache: SimpleCache[int, StyleAndTextTuples]
    _fragments: StyleAndTextTuples | None
    def __init__(
        self,
        text: AnyFormattedText = "",
        style: str = "",
        focusable: FilterOrBool = False,
        key_bindings: KeyBindingsBase | None = None,
        show_cursor: bool = True,
        modal: bool = False,
        get_cursor_position: Callable[[], Point | None] | None = None,
    ) -> None: ...
    def reset(self) -> None: ...
    def is_focusable(self) -> bool: ...
    def _get_formatted_text_cached(self) -> StyleAndTextTuples: ...
    def preferred_width(self, max_available_width: int) -> int: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def create_content(self, width: int, height: int | None) -> UIContent: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def __repr__(self) -> str: ...

class DummyControl(UIControl):
    def create_content(self, width: int, height: int) -> UIContent: ...
    def is_focusable(self) -> bool: ...

class _ProcessedLine(NamedTuple):
    fragments: StyleAndTextTuples
    source_to_display: Callable[[int], int]
    display_to_source: Callable[[int], int]

class BufferControl:
    input_processors: list[Processor] | None
    include_default_input_processors: bool
    default_input_processors = [
        HighlightSearchProcessor(),
        HighlightIncrementalSearchProcessor(),
        HighlightSelectionProcessor(),
        DisplayMultipleCursors(),
    ]
    preview_search: FilterOrBool
    focusable: FilterOrBool
    focus_on_click: FilterOrBool
    buffer: Buffer | None
    menu_position: Callable[[], int | None] | None
    lexer: Lexer | None
    key_bindings: KeyBindingsBase | None
    _search_buffer_control: (
        None | SearchBufferControl | Callable[[], SearchBufferControl]
    )
    _fragment_cache: SimpleCache[Hashable, Callable[[int], StyleAndTextTuples]]
    _last_click_timestamp: float | None
    _last_get_processed_line: Callable[[int], _ProcessedLine] | None
    def __init__(
        self,
        buffer: Buffer | None = None,
        input_processors: list[Processor] | None = None,
        include_default_input_processors: bool = True,
        lexer: Lexer | None = None,
        preview_search: FilterOrBool = False,
        focusable: FilterOrBool = True,
        search_buffer_control: None
        | SearchBufferControl
        | Callable[[], SearchBufferControl] = None,
        menu_position: Callable[[], int | None] | None = None,
        focus_on_click: FilterOrBool = False,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None: ...
    @property
    def search_buffer_control(self) -> SearchBufferControl | None: ...
    @property
    def search_buffer(self) -> Buffer | None: ...
    @property
    def search_state(self) -> SearchState: ...
    def is_focusable(self) -> bool: ...
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def _get_formatted_text_for_line_func(
        self,
        document: Document,
    ) -> Callable[[int], StyleAndTextTuples]: ...
    def _create_get_processed_line_func(
        self,
        document: Document,
        width: int,
        height: int,
    ) -> Callable[[int], _ProcessedLine]: ...
    def create_content(
        self,
        width: int,
        height: int,
        preview_search: bool = False,
    ) -> UIContent: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    def move_cursor_down(self) -> None: ...
    def move_cursor_up(self) -> None: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_invalidate_events(self) -> Iterable[Event[object]]: ...
    @property
    def language(self) -> str | None: ...
    def __repr__(self) -> str: ...

class SearchBufferControl(BufferControl):
    searcher_search_state: SearchState
    def __init__(
        self,
        buffer: Buffer | None = None,
        input_processors: list[Processor] | None = None,
        lexer: Lexer | None = None,
        focus_on_click: FilterOrBool = False,
        key_bindings: KeyBindingsBase | None = None,
        ignore_case: FilterOrBool = False,
    ) -> None: ...

class FocusableDummyControl(DummyControl):
    def is_focusable(self) -> bool: ...
