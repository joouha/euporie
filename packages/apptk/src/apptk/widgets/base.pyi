import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Generic, TypeVar

from apptk.auto_suggest import AutoSuggest
from apptk.border import ThinGrid, ThinLine
from apptk.buffer import Buffer, BufferAcceptHandler
from apptk.completion import Completer
from apptk.document import Document
from apptk.filters import (
    FilterOrBool,
)
from apptk.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
)
from apptk.history import History
from apptk.key_binding.key_bindings import KeyBindings
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.layout.containers import (
    AnyContainer,
    Container,
    DynamicContainer,
    FloatContainer,
    HSplit,
    Window,
    WindowAlign,
)
from apptk.layout.controls import (
    BufferControl,
    FormattedTextControl,
    GetLinePrefixCallable,
)
from apptk.layout.dimension import AnyDimension
from apptk.layout.processors import (
    Processor,
)
from apptk.lexers import Lexer
from apptk.mouse_events import MouseEvent
from apptk.validation import Validator

from .toolbars import SearchToolbar

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.border import GridStyle
    from apptk.filters.core import FilterOrBool

E = KeyPressEvent
_T = TypeVar("_T")
MouseHandler = Callable[[MouseEvent], object]
log = logging.getLogger(__name__)
Border = ThinGrid

__all__ = [
    "Box",
    "Button",
    "Checkbox",
    "CheckboxList",
    "Frame",
    "HorizontalLine",
    "Label",
    "ProgressBar",
    "RadioList",
    "Shadow",
    "TextArea",
    "VerticalLine",
]

class Border:
    HORIZONTAL = "\u2500"
    VERTICAL = "\u2502"
    TOP_LEFT = "\u250c"
    TOP_RIGHT = "\u2510"
    BOTTOM_LEFT = "\u2514"
    BOTTOM_RIGHT = "\u2518"

class TextArea:
    completer: Completer | None
    complete_while_typing: FilterOrBool
    lexer: Lexer | None
    auto_suggest: AutoSuggest | None
    read_only: FilterOrBool
    wrap_lines: FilterOrBool
    validator: Validator | None
    buffer: Buffer
    control: BufferControl
    window: Window
    def __init__(
        self,
        text: str = "",
        multiline: FilterOrBool = True,
        password: FilterOrBool = False,
        lexer: Lexer | None = None,
        auto_suggest: AutoSuggest | None = None,
        completer: Completer | None = None,
        complete_while_typing: FilterOrBool = True,
        validator: Validator | None = None,
        accept_handler: BufferAcceptHandler | None = None,
        history: History | None = None,
        focusable: FilterOrBool = True,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = True,
        read_only: FilterOrBool = False,
        width: AnyDimension = None,
        height: AnyDimension = None,
        dont_extend_height: FilterOrBool = False,
        dont_extend_width: FilterOrBool = False,
        line_numbers: bool = False,
        get_line_prefix: GetLinePrefixCallable | None = None,
        scrollbar: bool = False,
        style: str = "",
        search_field: SearchToolbar | None = None,
        preview_search: FilterOrBool = True,
        prompt: AnyFormattedText = "",
        input_processors: list[Processor] | None = None,
        name: str = "",
    ) -> None: ...
    @property
    def text(self) -> str: ...
    @text.setter
    def text(self, value: str) -> None: ...
    @property
    def document(self) -> Document: ...
    @document.setter
    def document(self, value: Document) -> None: ...
    @property
    def accept_handler(self) -> BufferAcceptHandler | None: ...
    @accept_handler.setter
    def accept_handler(self, value: BufferAcceptHandler) -> None: ...
    def __pt_container__(self) -> Container: ...

class Label:
    text: AnyFormattedText
    formatted_text_control: FormattedTextControl
    window: Window
    def __init__(
        self,
        text: AnyFormattedText,
        style: str = "",
        width: AnyDimension = None,
        dont_extend_height: bool = True,
        dont_extend_width: bool = False,
        align: WindowAlign | Callable[[], WindowAlign] = WindowAlign.LEFT,
        wrap_lines: FilterOrBool = True,
    ) -> None: ...
    def __pt_container__(self) -> Container: ...

class Button:
    text: str
    left_symbol: str
    right_symbol: str
    handler: Callable[[], None] | None
    width: int
    control: FormattedTextControl
    window: Window
    def __init__(
        self,
        text: str,
        handler: Callable[[], None] | None = None,
        width: int = 12,
        left_symbol: str = "<",
        right_symbol: str = ">",
    ) -> None: ...
    def _get_text_fragments(self) -> StyleAndTextTuples: ...
    def _get_key_bindings(self) -> KeyBindings: ...
    def __pt_container__(self) -> Container: ...

class Frame:
    title: AnyFormattedText
    body: AnyContainer
    container: AnyContainer
    style: str | Callable[[], str]
    def __init__(
        self,
        body: AnyContainer,
        title: AnyFormattedText = "",
        style: str | Callable[[], str] = "class:frame",
        width: AnyDimension = None,
        height: AnyDimension = None,
        key_bindings: KeyBindings | None = None,
        modal: bool = False,
        border: GridStyle | None = ThinLine.grid,
        border_style: str
        | Callable[[], str]
        | tuple[
            str | Callable[[], str],
            str | Callable[[], str],
            str | Callable[[], str],
            str | Callable[[], str],
        ]
        | None = None,
        show_borders: FilterOrBool
        | tuple[FilterOrBool, FilterOrBool, FilterOrBool, FilterOrBool]
        | None = None,
    ) -> None: ...
    def __pt_container__(self) -> Container: ...
    def add_styles(self, *styles: str | Callable[[], str]) -> Callable[[], str]: ...

class Shadow:
    container: DynamicContainer
    def __init__(self, body: AnyContainer, filter: FilterOrBool = True) -> None: ...
    def __pt_container__(self) -> Container: ...

class Box:
    padding: AnyDimension
    padding_left: AnyDimension
    padding_right: AnyDimension
    padding_top: AnyDimension
    padding_bottom: AnyDimension
    body: AnyContainer
    container: HSplit
    def __init__(
        self,
        body: AnyContainer,
        padding: AnyDimension = None,
        padding_left: AnyDimension = None,
        padding_right: AnyDimension = None,
        padding_top: AnyDimension = None,
        padding_bottom: AnyDimension = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        style: str = "",
        char: None | str | Callable[[], str] = None,
        modal: bool = False,
        key_bindings: KeyBindings | None = None,
    ) -> None: ...
    def __pt_container__(self) -> Container: ...

class _DialogList(Generic[_T]):
    values: Sequence[tuple[_T, AnyFormattedText]]
    show_numbers: bool
    open_character: str
    select_character: str
    close_character: str
    container_style: str
    default_style: str
    number_style: str
    selected_style: str
    checked_style: str
    multiple_selection: bool
    show_scrollbar: bool
    current_values: list[_T]
    current_value: _T
    control: FormattedTextControl
    window: Window
    _selected_index = keys.index(self.current_values[0])
    def __init__(
        self,
        values: Sequence[tuple[_T, AnyFormattedText]],
        default_values: Sequence[_T] | None = None,
        select_on_focus: bool = False,
        open_character: str = "",
        select_character: str = "*",
        close_character: str = "",
        container_style: str = "",
        default_style: str = "",
        number_style: str = "",
        selected_style: str = "",
        checked_style: str = "",
        multiple_selection: bool = False,
        show_scrollbar: bool = True,
        show_cursor: bool = True,
        show_numbers: bool = False,
    ) -> None: ...
    def _handle_enter(self) -> None: ...
    def _get_text_fragments(self) -> StyleAndTextTuples: ...
    def __pt_container__(self) -> Container: ...

class RadioList(Generic[_T], _DialogList[_T]):
    def __init__(
        self,
        values: Sequence[tuple[_T, AnyFormattedText]],
        default: _T | None = None,
        show_numbers: bool = False,
        select_on_focus: bool = False,
        open_character: str = "(",
        select_character: str = "*",
        close_character: str = ")",
        container_style: str = "class:radio-list",
        default_style: str = "class:radio",
        selected_style: str = "class:radio-selected",
        checked_style: str = "class:radio-checked",
        number_style: str = "class:radio-number",
        multiple_selection: bool = False,
        show_cursor: bool = True,
        show_scrollbar: bool = True,
    ) -> None: ...

class CheckboxList(Generic[_T], _DialogList[_T]):
    def __init__(
        self,
        values: Sequence[tuple[_T, AnyFormattedText]],
        default_values: Sequence[_T] | None = None,
        open_character: str = "[",
        select_character: str = "*",
        close_character: str = "]",
        container_style: str = "class:checkbox-list",
        default_style: str = "class:checkbox",
        selected_style: str = "class:checkbox-selected",
        checked_style: str = "class:checkbox-checked",
    ) -> None: ...

class Checkbox(CheckboxList[str]):
    show_scrollbar = False
    current_values = ["value"]
    def __init__(self, text: AnyFormattedText = "", checked: bool = False) -> None: ...
    @property
    def checked(self) -> bool: ...
    @checked.setter
    def checked(self, value: bool) -> None: ...

class VerticalLine:
    window: Window
    def __init__(self) -> None: ...
    def __pt_container__(self) -> Container: ...

class HorizontalLine:
    window: Window
    def __init__(self) -> None: ...
    def __pt_container__(self) -> Container: ...

class ProgressBar:
    _percentage = 60
    label: Label
    container: FloatContainer
    def __init__(self) -> None: ...
    @property
    def percentage(self) -> int: ...
    @percentage.setter
    def percentage(self, value: int) -> None: ...
    def __pt_container__(self) -> Container: ...
