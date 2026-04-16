from collections.abc import Callable
from contextlib import AbstractContextManager
from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeVar, Union

from apptk.application import Application
from apptk.auto_suggest import AutoSuggest
from apptk.buffer import Buffer
from apptk.clipboard import Clipboard
from apptk.completion import Completer
from apptk.cursor_shapes import (
    AnyCursorShapeConfig,
    CursorShapeConfig,
)
from apptk.document import Document
from apptk.enums import EditingMode
from apptk.eventloop import InputHook
from apptk.filters import (
    Condition,
    FilterOrBool,
)
from apptk.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
)
from apptk.history import History
from apptk.input.base import Input
from apptk.key_binding.key_bindings import (
    KeyBindings,
    KeyBindingsBase,
)
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.layout import Window
from apptk.layout.dimension import Dimension
from apptk.layout.layout import Layout
from apptk.layout.processors import (
    Processor,
)
from apptk.lexers import Lexer
from apptk.output import ColorDepth, Output
from apptk.styles import (
    BaseStyle,
    StyleTransformation,
)
from apptk.validation import Validator

if TYPE_CHECKING:
    from apptk.formatted_text.base import MagicFormattedText

_StyleAndTextTuplesCallable = Callable[[], StyleAndTextTuples]
E = KeyPressEvent
PromptContinuationText = Union[
    str,
    "MagicFormattedText",
    StyleAndTextTuples,
    # (prompt_width, line_number, wrap_count) -> AnyFormattedText.
    Callable[[int, int, int], AnyFormattedText],
]
_T = TypeVar("_T")

__all__ = [
    "CompleteStyle",
    "PromptSession",
    "confirm",
    "create_confirm_session",
    "prompt",
]

def prompt(
    message: AnyFormattedText | None = None,
    *,
    history: History | None = None,
    editing_mode: EditingMode | None = None,
    refresh_interval: float | None = None,
    vi_mode: bool | None = None,
    lexer: Lexer | None = None,
    completer: Completer | None = None,
    complete_in_thread: bool | None = None,
    is_password: bool | None = None,
    key_bindings: KeyBindingsBase | None = None,
    bottom_toolbar: AnyFormattedText | None = None,
    style: BaseStyle | None = None,
    color_depth: ColorDepth | None = None,
    cursor: AnyCursorShapeConfig = None,
    include_default_pygments_style: FilterOrBool | None = None,
    style_transformation: StyleTransformation | None = None,
    swap_light_and_dark_colors: FilterOrBool | None = None,
    rprompt: AnyFormattedText | None = None,
    multiline: FilterOrBool | None = None,
    prompt_continuation: PromptContinuationText | None = None,
    wrap_lines: FilterOrBool | None = None,
    enable_history_search: FilterOrBool | None = None,
    search_ignore_case: FilterOrBool | None = None,
    complete_while_typing: FilterOrBool | None = None,
    validate_while_typing: FilterOrBool | None = None,
    complete_style: CompleteStyle | None = None,
    auto_suggest: AutoSuggest | None = None,
    validator: Validator | None = None,
    clipboard: Clipboard | None = None,
    mouse_support: FilterOrBool | None = None,
    input_processors: list[Processor] | None = None,
    placeholder: AnyFormattedText | None = None,
    reserve_space_for_menu: int | None = None,
    enable_system_prompt: FilterOrBool | None = None,
    enable_suspend: FilterOrBool | None = None,
    enable_open_in_editor: FilterOrBool | None = None,
    tempfile_suffix: str | Callable[[], str] | None = None,
    tempfile: str | Callable[[], str] | None = None,
    show_frame: FilterOrBool | None = None,
    default: str = "",
    accept_default: bool = False,
    pre_run: Callable[[], None] | None = None,
    set_exception_handler: bool = True,
    handle_sigint: bool = True,
    in_thread: bool = False,
    inputhook: InputHook | None = None,
) -> str: ...
def create_confirm_session(
    message: AnyFormattedText,
    suffix: str = " (y/n) ",
) -> PromptSession[bool]: ...
def confirm(
    message: AnyFormattedText = "Confirm?", suffix: str = " (y/n) "
) -> bool: ...

class _RPrompt(Window):
    def __init__(self, text: AnyFormattedText) -> None: ...

class CompleteStyle(str, Enum):
    value: str
    COLUMN = "COLUMN"
    MULTI_COLUMN = "MULTI_COLUMN"
    READLINE_LIKE = "READLINE_LIKE"

class PromptSession(Generic[_T]):
    _fields = (
        "message",
        "lexer",
        "completer",
        "complete_in_thread",
        "is_password",
        "editing_mode",
        "key_bindings",
        "is_password",
        "bottom_toolbar",
        "style",
        "style_transformation",
        "swap_light_and_dark_colors",
        "color_depth",
        "cursor",
        "include_default_pygments_style",
        "rprompt",
        "multiline",
        "prompt_continuation",
        "wrap_lines",
        "enable_history_search",
        "search_ignore_case",
        "complete_while_typing",
        "validate_while_typing",
        "complete_style",
        "mouse_support",
        "auto_suggest",
        "clipboard",
        "validator",
        "refresh_interval",
        "input_processors",
        "placeholder",
        "enable_system_prompt",
        "enable_suspend",
        "enable_open_in_editor",
        "reserve_space_for_menu",
        "tempfile_suffix",
        "tempfile",
        "show_frame",
    )
    _input: Input | None
    _output: Output | None
    message: AnyFormattedText
    lexer: Lexer | None
    completer: Completer | None
    complete_in_thread: bool
    is_password: FilterOrBool
    key_bindings: KeyBindingsBase | None
    bottom_toolbar: AnyFormattedText
    style: BaseStyle | None
    style_transformation: StyleTransformation | None
    swap_light_and_dark_colors: FilterOrBool
    color_depth: ColorDepth | None
    cursor: AnyCursorShapeConfig
    include_default_pygments_style: FilterOrBool
    rprompt: AnyFormattedText
    multiline: FilterOrBool
    prompt_continuation: PromptContinuationText | None
    wrap_lines: FilterOrBool
    enable_history_search: FilterOrBool
    search_ignore_case: FilterOrBool
    complete_while_typing: FilterOrBool
    validate_while_typing: FilterOrBool
    complete_style: CompleteStyle
    mouse_support: FilterOrBool
    auto_suggest: AutoSuggest | None
    clipboard: Clipboard | None
    validator: Validator | None
    refresh_interval: float
    input_processors: list[Processor] | None
    placeholder: AnyFormattedText | None
    enable_system_prompt: FilterOrBool
    enable_suspend: FilterOrBool
    enable_open_in_editor: FilterOrBool
    reserve_space_for_menu: int
    tempfile_suffix: str | Callable[[], str] | None
    tempfile: str | Callable[[], str] | None
    show_frame: FilterOrBool
    interrupt_exception: type[BaseException]
    eof_exception: type[BaseException]
    history: History | None
    default_buffer = self._create_default_buffer()
    search_buffer = self._create_search_buffer()
    layout = self._create_layout()
    app: EditingMode
    def __init__(
        self,
        message: AnyFormattedText = "",
        *,
        multiline: FilterOrBool = False,
        wrap_lines: FilterOrBool = True,
        is_password: FilterOrBool = False,
        vi_mode: bool = False,
        editing_mode: EditingMode = EditingMode.EMACS,
        complete_while_typing: FilterOrBool = True,
        validate_while_typing: FilterOrBool = True,
        enable_history_search: FilterOrBool = False,
        search_ignore_case: FilterOrBool = False,
        lexer: Lexer | None = None,
        enable_system_prompt: FilterOrBool = False,
        enable_suspend: FilterOrBool = False,
        enable_open_in_editor: FilterOrBool = False,
        validator: Validator | None = None,
        completer: Completer | None = None,
        complete_in_thread: bool = False,
        reserve_space_for_menu: int = 8,
        complete_style: CompleteStyle = CompleteStyle.COLUMN,
        auto_suggest: AutoSuggest | None = None,
        style: BaseStyle | None = None,
        style_transformation: StyleTransformation | None = None,
        swap_light_and_dark_colors: FilterOrBool = False,
        color_depth: ColorDepth | None = None,
        cursor: AnyCursorShapeConfig = None,
        include_default_pygments_style: FilterOrBool = True,
        history: History | None = None,
        clipboard: Clipboard | None = None,
        prompt_continuation: PromptContinuationText | None = None,
        rprompt: AnyFormattedText = None,
        bottom_toolbar: AnyFormattedText = None,
        mouse_support: FilterOrBool = False,
        input_processors: list[Processor] | None = None,
        placeholder: AnyFormattedText | None = None,
        key_bindings: KeyBindingsBase | None = None,
        erase_when_done: bool = False,
        tempfile_suffix: str | Callable[[], str] | None = ".txt",
        tempfile: str | Callable[[], str] | None = None,
        refresh_interval: float = 0,
        show_frame: FilterOrBool = False,
        input: Input | None = None,
        output: Output | None = None,
        interrupt_exception: type[BaseException] = KeyboardInterrupt,
        eof_exception: type[BaseException] = EOFError,
    ) -> None: ...
    def _dyncond(self, attr_name: str) -> Condition: ...
    def _create_default_buffer(self) -> Buffer: ...
    def _create_search_buffer(self) -> Buffer: ...
    def _create_layout(self) -> Layout: ...
    def _create_application(
        self,
        editing_mode: EditingMode,
        erase_when_done: bool,
    ) -> Application[_T]: ...
    def _create_prompt_bindings(self) -> KeyBindings: ...
    def prompt(
        self,
        message: AnyFormattedText | None = None,
        *,
        editing_mode: EditingMode | None = None,
        refresh_interval: float | None = None,
        vi_mode: bool | None = None,
        lexer: Lexer | None = None,
        completer: Completer | None = None,
        complete_in_thread: bool | None = None,
        is_password: bool | None = None,
        key_bindings: KeyBindingsBase | None = None,
        bottom_toolbar: AnyFormattedText | None = None,
        style: BaseStyle | None = None,
        color_depth: ColorDepth | None = None,
        cursor: AnyCursorShapeConfig | None = None,
        include_default_pygments_style: FilterOrBool | None = None,
        style_transformation: StyleTransformation | None = None,
        swap_light_and_dark_colors: FilterOrBool | None = None,
        rprompt: AnyFormattedText | None = None,
        multiline: FilterOrBool | None = None,
        prompt_continuation: PromptContinuationText | None = None,
        wrap_lines: FilterOrBool | None = None,
        enable_history_search: FilterOrBool | None = None,
        search_ignore_case: FilterOrBool | None = None,
        complete_while_typing: FilterOrBool | None = None,
        validate_while_typing: FilterOrBool | None = None,
        complete_style: CompleteStyle | None = None,
        auto_suggest: AutoSuggest | None = None,
        validator: Validator | None = None,
        clipboard: Clipboard | None = None,
        mouse_support: FilterOrBool | None = None,
        input_processors: list[Processor] | None = None,
        placeholder: AnyFormattedText | None = None,
        reserve_space_for_menu: int | None = None,
        enable_system_prompt: FilterOrBool | None = None,
        enable_suspend: FilterOrBool | None = None,
        enable_open_in_editor: FilterOrBool | None = None,
        tempfile_suffix: str | Callable[[], str] | None = None,
        tempfile: str | Callable[[], str] | None = None,
        show_frame: FilterOrBool | None = None,
        default: str | Document = "",
        accept_default: bool = False,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        in_thread: bool = False,
        inputhook: InputHook | None = None,
    ) -> _T: ...
    def _dumb_prompt(
        self,
        message: AnyFormattedText = "",
    ) -> AbstractContextManager[Application[_T]]: ...
    async def prompt_async(
        self,
        message: AnyFormattedText | None = None,
        *,
        editing_mode: EditingMode | None = None,
        refresh_interval: float | None = None,
        vi_mode: bool | None = None,
        lexer: Lexer | None = None,
        completer: Completer | None = None,
        complete_in_thread: bool | None = None,
        is_password: bool | None = None,
        key_bindings: KeyBindingsBase | None = None,
        bottom_toolbar: AnyFormattedText | None = None,
        style: BaseStyle | None = None,
        color_depth: ColorDepth | None = None,
        cursor: CursorShapeConfig | None = None,
        include_default_pygments_style: FilterOrBool | None = None,
        style_transformation: StyleTransformation | None = None,
        swap_light_and_dark_colors: FilterOrBool | None = None,
        rprompt: AnyFormattedText | None = None,
        multiline: FilterOrBool | None = None,
        prompt_continuation: PromptContinuationText | None = None,
        wrap_lines: FilterOrBool | None = None,
        enable_history_search: FilterOrBool | None = None,
        search_ignore_case: FilterOrBool | None = None,
        complete_while_typing: FilterOrBool | None = None,
        validate_while_typing: FilterOrBool | None = None,
        complete_style: CompleteStyle | None = None,
        auto_suggest: AutoSuggest | None = None,
        validator: Validator | None = None,
        clipboard: Clipboard | None = None,
        mouse_support: FilterOrBool | None = None,
        input_processors: list[Processor] | None = None,
        placeholder: AnyFormattedText | None = None,
        reserve_space_for_menu: int | None = None,
        enable_system_prompt: FilterOrBool | None = None,
        enable_suspend: FilterOrBool | None = None,
        enable_open_in_editor: FilterOrBool | None = None,
        tempfile_suffix: str | Callable[[], str] | None = None,
        tempfile: str | Callable[[], str] | None = None,
        show_frame: FilterOrBool = False,
        default: str | Document = "",
        accept_default: bool = False,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
    ) -> _T: ...
    def _add_pre_run_callables(
        self,
        pre_run: Callable[[], None] | None,
        accept_default: bool,
    ) -> None: ...
    @property
    def editing_mode(self) -> EditingMode: ...
    @editing_mode.setter
    def editing_mode(self, value: EditingMode) -> None: ...
    def _get_default_buffer_control_height(self) -> Dimension: ...
    def _get_prompt(self) -> StyleAndTextTuples: ...
    def _get_continuation(
        self,
        width: int,
        line_number: int,
        wrap_count: int,
    ) -> StyleAndTextTuples: ...
    def _get_line_prefix(
        self,
        line_number: int,
        wrap_count: int,
        get_prompt_text_2: _StyleAndTextTuplesCallable,
    ) -> StyleAndTextTuples: ...
    def _get_arg_text(self) -> StyleAndTextTuples: ...
    def _inline_arg(self) -> StyleAndTextTuples: ...
    @property
    def input(self) -> Input: ...
    @property
    def output(self) -> Output: ...
