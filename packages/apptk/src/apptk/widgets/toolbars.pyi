import logging
from typing import TYPE_CHECKING, Any

from apptk.buffer import Buffer
from apptk.cache import FastDictCache
from apptk.completion.base import Completer, Completion
from apptk.filters import (
    FilterOrBool,
)
from apptk.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
)
from apptk.key_binding.key_bindings import (
    KeyBindingsBase,
)
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.layout.containers import (
    ConditionalContainer,
    Container,
    Window,
)
from apptk.layout.controls import (
    BufferControl,
    FormattedTextControl,
    SearchBufferControl,
    UIContent,
    UIControl,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Unpack

    from apptk.buffer import CompletionState
    from apptk.completion.base import CompleteEvent
    from apptk.document import Document
    from apptk.history import History
    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from apptk.layout.containers import AnyContainer
    from apptk.layout.controls import GetLinePrefixCallable
    from apptk.mouse_events import MouseEvent

E = KeyPressEvent
StatusBarFields = tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]
log = logging.getLogger(__name__)

__all__ = [
    "ArgToolbar",
    "CommandBar",
    "CommandCompleter",
    "CompletionsToolbar",
    "FormattedTextToolbar",
    "HorizontalCompletionsMenu",
    "SearchToolbar",
    "SystemToolbar",
    "ValidationToolbar",
]

class FormattedTextToolbar(Window):
    def __init__(self, text: AnyFormattedText, style: str = "", **kw: Any) -> None: ...

class SystemToolbar:
    prompt: AnyFormattedText
    enable_global_bindings: FilterOrBool
    system_buffer: Buffer
    _bindings = self._build_key_bindings()
    buffer_control: BufferControl
    window: Window
    container: ConditionalContainer
    def __init__(
        self,
        prompt: AnyFormattedText = "Shell command: ",
        enable_global_bindings: FilterOrBool = True,
    ) -> None: ...
    def _get_display_before_text(self) -> StyleAndTextTuples: ...
    def _build_key_bindings(self) -> KeyBindingsBase: ...
    def __pt_container__(self) -> Container: ...

class ArgToolbar:
    window: Window
    container: ConditionalContainer
    def __init__(self) -> None: ...
    def __pt_container__(self) -> Container: ...

class SearchToolbar:
    search_buffer: Buffer | None
    control: SearchBufferControl
    container: ConditionalContainer
    commands: tuple[str, ...] = ("accept-search", "stop-search")
    def __init__(
        self,
        search_buffer: Buffer | None = None,
        vi_mode: bool = False,
        text_if_not_searching: AnyFormattedText = "",
        forward_search_prompt: AnyFormattedText = "I-search: ",
        backward_search_prompt: AnyFormattedText = "I-search backward: ",
        ignore_case: FilterOrBool = False,
        auto_ignore_case: bool = True,
        key_bindings: KeyBindingsBase | None = None,
        history: History | None = None,
    ) -> None: ...
    def __pt_container__(self) -> Container: ...

class _CompletionsToolbarControl(UIControl):
    def create_content(self, width: int, height: int) -> UIContent: ...

class CompletionsToolbar:
    container: ConditionalContainer
    def __init__(self) -> None: ...
    def __pt_container__(self) -> Container: ...

class ValidationToolbar:
    control: FormattedTextControl
    container: ConditionalContainer
    def __init__(self, show_position: bool = False) -> None: ...
    def __pt_container__(self) -> Container: ...

class CommandCompleter(Completer):
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...

class CommandBar:
    _commands_registered: bool = False
    prompt: AnyFormattedText
    style: str
    buffer: Buffer
    control: BufferControl
    window: Window
    container: ConditionalContainer
    def __init__(
        self,
        prompt: AnyFormattedText = ":",
        style: str = "class:command-toolbar",
        history: History | None = None,
    ) -> None: ...
    def _validate(self, text: str) -> bool: ...
    def _accept(self, buffer: Buffer) -> bool: ...
    def __pt_container__(self) -> Container: ...
    def _activate_command_bar(event: KeyPressEvent) -> None: ...
    def _activate_command_bar_shell(event: KeyPressEvent) -> None: ...
    def _deactivate_command_bar(event: KeyPressEvent) -> None: ...
    @staticmethod
    async def _run_shell_command(
        event: KeyPressEvent,
        *cmd_arg: Unpack[tuple[str]],
    ) -> None: ...

class StatusBar:
    default: StatusBarFields
    left_style: str
    right_style: str
    left_separator: tuple[str, str]
    right_separator: tuple[str, str]
    _status_cache: FastDictCache[tuple[int], list[StyleAndTextTuples]]
    container: ConditionalContainer
    def __init__(
        self,
        filter: FilterOrBool = True,
        default: StatusBarFields | None = None,
        left_style: str = "class:status",
        right_style: str = "class:status.right",
        left_separator: tuple[str, str] = ("", ""),
        right_separator: tuple[str, str] = ("", ""),
    ) -> None: ...
    def _status(self, render_counter: int = 0) -> list[StyleAndTextTuples]: ...
    def __pt_container__(self) -> AnyContainer: ...

class _HorizontalCompletionMenuControl(UIControl):
    max_item_width: int
    min_item_width: int
    def __init__(self, min_item_width: int = 5, max_item_width: int = 30) -> None: ...
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def _get_col_width(
        self,
        complete_state: CompletionState,
        width: int,
        height: int,
    ) -> int: ...
    def create_content(self, width: int, height: int) -> UIContent: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    def move_cursor_down(self) -> None: ...
    def move_cursor_up(self) -> None: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...

class _CompletionMetaControl(UIControl):
    def preferred_width(self, max_available_width: int) -> int | None: ...
    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None: ...
    def create_content(self, width: int, height: int) -> UIContent: ...

class HorizontalCompletionsMenu(ConditionalContainer):
    def __init__(
        self,
        filter: FilterOrBool = True,
        min_item_width: int = 5,
        max_item_width: int = 30,
        max_height: int = 8,
        show_meta: bool = True,
        style: str = "class:completion-toolbar",
    ) -> None: ...
