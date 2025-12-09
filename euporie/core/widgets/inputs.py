"""Define a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from prompt_toolkit.auto_suggest import AutoSuggest, DynamicAutoSuggest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion.base import Completer, DynamicCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    Condition,
    buffer_has_focus,
    has_focus,
    has_selection,
    is_done,
    is_searching,
    is_true,
    to_filter,
)
from prompt_toolkit.key_binding.key_bindings import merge_key_bindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    ScrollOffsets,
)
from prompt_toolkit.layout.controls import (
    BufferControl,
    GetLinePrefixCallable,
)
from prompt_toolkit.layout.dimension import AnyDimension
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.processors import (  # HighlightSearchProcessor,
    BeforeInput,
    ConditionalProcessor,
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightMatchingBracketProcessor,
    HighlightSelectionProcessor,
    PasswordProcessor,
    Processor,
    TabsProcessor,
)
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, SimpleLexer
from prompt_toolkit.validation import DynamicValidator, Validator
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.widgets.toolbars import SearchToolbar
from pygments.lexers import ClassNotFound, get_lexer_by_name

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd
from euporie.core.diagnostics import Report
from euporie.core.filters import buffer_is_code, scrollable
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.layout.containers import VSplit, Window
from euporie.core.margins import (
    MarginContainer,
    NumberedMargin,
    OverflowMargin,
    ScrollbarMargin,
)
from euporie.core.processors import (
    AppendLineAutoSuggestion,
    DiagnosticProcessor,
    ShowTrailingWhiteSpaceProcessor,
)
from euporie.core.suggest import ConditionalAutoSuggestAsync

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from prompt_toolkit.buffer import BufferAcceptHandler
    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.formatted_text import (
        AnyFormattedText,
    )
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.history import History
    from prompt_toolkit.key_binding.key_bindings import KeyBindingsBase
    from prompt_toolkit.layout.containers import AnyContainer, Container
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.layout.margins import Margin
    from prompt_toolkit.lexers.base import Lexer

    from euporie.core.bars.status import StatusBarFields
    from euporie.core.format import Formatter
    from euporie.core.inspection import Inspector
    from euporie.core.tabs.kernel import KernelTab


log = logging.getLogger(__name__)


@lru_cache
def _get_lexer(highlight: bool, lexer: Lexer | None, language: str) -> Lexer:
    """Determine which lexer should be used for syntax highlighting."""
    if not highlight:
        return SimpleLexer()
    elif lexer is not None:
        return lexer
    try:
        pygments_lexer_class = get_lexer_by_name(language).__class__
    except ClassNotFound:
        return SimpleLexer()
    else:
        return PygmentsLexer(pygments_lexer_class, sync_from_start=False)


class KernelInput(TextArea):
    """Kernel input text areas.

    A customized text area for the cell input.
    """

    def __init__(
        self,
        kernel_tab: KernelTab,
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
        focus_on_click: FilterOrBool = True,
        wrap_lines: FilterOrBool = False,
        read_only: FilterOrBool = False,
        width: AnyDimension = None,
        height: AnyDimension = None,
        dont_extend_height: FilterOrBool = False,
        dont_extend_width: FilterOrBool = False,
        line_numbers: bool = False,
        get_line_prefix: GetLinePrefixCallable | None = None,
        scrollbar: FilterOrBool = True,
        style: str = "class:kernel-input",
        search_field: SearchToolbar | None = None,
        preview_search: FilterOrBool = False,
        prompt: AnyFormattedText = "",
        input_processors: list[Processor] | None = None,
        name: str = "",
        left_margins: Sequence[Margin] | None = None,
        right_margins: Sequence[Margin] | None = None,
        on_text_changed: Callable[[Buffer], None] | None = None,
        on_cursor_position_changed: Callable[[Buffer], None] | None = None,
        tempfile_suffix: str | Callable[[], str] = "",
        key_bindings: KeyBindingsBase | None = None,
        enable_history_search: FilterOrBool = False,
        autosuggest_while_typing: FilterOrBool = True,
        validate_while_typing: FilterOrBool = False,
        scroll_offsets: ScrollOffsets | None = None,
        formatters: list[Formatter] | None = None,
        language: str | Callable[[], str] | None = None,
        diagnostics: Report | Callable[[], Report] | None = None,
        inspector: Inspector | None = None,
        show_diagnostics: FilterOrBool = True,
        relative_line_numbers: FilterOrBool = False,
    ) -> None:
        """Initiate the cell input box."""
        self.kernel_tab = kernel_tab
        app = kernel_tab.app

        if history is None:
            history = kernel_tab.history

        if search_field is None:
            search_field = app.search_bar
        if isinstance(search_field, SearchToolbar):
            search_control = search_field.control
        else:
            search_control = None

        if input_processors is None:
            input_processors = []

        # Writeable attributes.
        self.completer = completer
        self.complete_while_typing = Condition(
            lambda: app.config.autocomplete
        ) & to_filter(complete_while_typing)
        self.auto_suggest = auto_suggest or ConditionalAutoSuggestAsync(
            self.kernel_tab.suggester,
            filter=to_filter(autosuggest_while_typing)
            & Condition(lambda: app.config.autosuggest),
        )
        self.read_only = read_only
        self.wrap_lines = wrap_lines
        self.validator = validator
        self._language = language
        self.lexer = lexer

        self.formatters = formatters if formatters is not None else []
        self._diagnostics = diagnostics or Report()
        self.inspector = inspector

        self.buffer = Buffer(
            document=Document(text, 0),
            multiline=multiline,
            read_only=Condition(lambda: is_true(self.read_only)),
            completer=DynamicCompleter(lambda: self.completer),
            complete_while_typing=Condition(
                lambda: is_true(self.complete_while_typing)
            ),
            validator=DynamicValidator(lambda: self.validator),
            auto_suggest=DynamicAutoSuggest(lambda: self.auto_suggest),
            accept_handler=accept_handler,
            history=history,
            name=name,
            validate_while_typing=validate_while_typing,
            on_text_changed=on_text_changed,
            on_cursor_position_changed=on_cursor_position_changed,
            tempfile_suffix=tempfile_suffix or kernel_tab.kernel_lang_file_ext,
            enable_history_search=to_filter(enable_history_search),
        )
        self.has_focus: Filter = has_focus(self.buffer)

        # Set up autoinspect
        def _on_cursor_position_changed(buf: Buffer) -> None:
            """Respond to cursor movements."""
            # Update contextual help
            if app.config.autoinspect and self.buffer.name == "code":
                app.create_background_task(self.inspect(auto=True))
            elif pager := app.pager:
                pager.hide()

        self.buffer.on_cursor_position_changed += _on_cursor_position_changed

        # Set extra key-bindings
        widgets_key_bindings = load_registered_bindings(
            "euporie.core.widgets.inputs:KernelInput",
            config=app.config,
        )
        if key_bindings:
            widgets_key_bindings = merge_key_bindings(
                [key_bindings, widgets_key_bindings]
            )

        def _get_diagnostics() -> Report:
            return self.diagnostics

        self.control = BufferControl(
            buffer=self.buffer,
            lexer=DynamicLexer(
                lambda: _get_lexer(
                    # Only lex buffers with text
                    self.buffer.text and app.config.syntax_highlighting,
                    self.lexer,
                    self.language,
                )
            ),
            input_processors=[
                ConditionalProcessor(
                    DiagnosticProcessor(_get_diagnostics),
                    filter=to_filter(show_diagnostics),
                ),
                ConditionalProcessor(  # type: ignore
                    AppendLineAutoSuggestion(),
                    has_focus(self.buffer) & ~is_done,
                ),
                ConditionalProcessor(
                    processor=PasswordProcessor(), filter=to_filter(password)
                ),
                BeforeInput(prompt, style="class:text-area.prompt"),
                ConditionalProcessor(
                    HighlightIncrementalSearchProcessor(),
                    filter=is_searching,
                ),
                # HighlightSearchProcessor(),
                HighlightSelectionProcessor(),
                DisplayMultipleCursors(),
                ConditionalProcessor(  # type: ignore
                    HighlightMatchingBracketProcessor(),
                    has_focus(self.buffer) & ~is_done,
                ),
                TabsProcessor(char1="⇥", char2="┈"),
                ShowTrailingWhiteSpaceProcessor(),
                *input_processors,
            ],
            search_buffer_control=search_control,
            preview_search=preview_search,
            focusable=focusable,
            focus_on_click=focus_on_click,
            include_default_input_processors=False,
            key_bindings=widgets_key_bindings,
        )

        left_margins = [
            ConditionalMargin(
                NumberedMargin(
                    diagnostics=_get_diagnostics,
                    show_diagnostics=to_filter(show_diagnostics),
                    relative=to_filter(relative_line_numbers),
                ),
                app.config.filters.line_numbers & self.buffer.multiline,
            ),
        ]
        right_margins = [OverflowMargin()]
        self.window = Window(
            height=lambda: height or D(min=1)
            if self.buffer.multiline()
            else D.exact(1),
            width=width,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            content=self.control,
            wrap_lines=Condition(lambda: is_true(self.wrap_lines)),
            left_margins=left_margins,
            right_margins=right_margins,
            get_line_prefix=get_line_prefix,
            style=lambda: (
                "class:text-area "
                + ("class:focused " if self.has_focus() else "")
                + style
            ),
            cursorline=has_focus(self.buffer),
            scroll_offsets=scroll_offsets
            or ScrollOffsets(top=1, right=1, bottom=1, left=1),
        )

        self.container = VSplit(
            [
                self.window,
                ConditionalContainer(
                    MarginContainer(ScrollbarMargin(), target=self.window),
                    filter=to_filter(scrollbar) & scrollable(self.window),
                ),
            ]
        )

    @property
    def language(self) -> str:
        """The current language of the text in the input box."""
        return str(
            self._language() if callable(self._language) else self._language
        ).casefold()

    @language.setter
    def language(self, value: str) -> None:
        """Set the current language of the text in the input box."""
        self._language = value

    @property
    def diagnostics(self) -> Report:
        """The current diagnostics report."""
        if callable(self._diagnostics):
            return self._diagnostics()
        return self._diagnostics

    @diagnostics.setter
    def diagnostics(self, value: Report) -> None:
        """Set the current diagnostics report."""
        self._diagnostics = value

    def reformat(self) -> None:
        """Reformat the cell's input."""
        original_text = new_text = self.buffer.text
        language = self.language
        for formatter in self.formatters:
            new_text = formatter._format(original_text, language)
        # Do not trigger a text-changed event if the reformatting results in no change
        if new_text != original_text:
            self.buffer.text = new_text

    async def inspect(self, auto: bool = False) -> None:
        """Get contextual help for the current cursor position in the current cell."""
        from euporie.core.widgets.pager import PagerState

        if self.inspector is None:
            return

        document = self.buffer.document
        pager = self.kernel_tab.app.pager
        assert pager is not None

        prev_state = pager.state
        if (
            not auto
            and pager.visible()
            and prev_state is not None
            and prev_state.code == document.text
            and prev_state.cursor_pos == document.cursor_position
        ):
            pager.focus()
            return

        data = await self.inspector.get_context(document, auto=auto)
        new_state = (
            PagerState(
                code=document.text, cursor_pos=document.cursor_position, data=data
            )
            if data
            else None
        )
        if prev_state != new_state:
            pager.state = new_state
            self.kernel_tab.app.invalidate()

    @property
    def current_diagnostic_message(self) -> StyleAndTextTuples:
        """Format the currently selected diagnostic message."""
        document = self.buffer.document
        row = document.cursor_position_row
        col = document.cursor_position_col
        line: StyleAndTextTuples = []
        # mypy bug https://github.com/python/mypy/issues/16733
        for diagnostic in self.diagnostics:  # type: ignore [attr-defined]
            lines = diagnostic.lines
            chars = diagnostic.chars
            if lines.start <= row < lines.stop and chars.start <= col < chars.stop:
                if diagnostic.code:
                    line.append(
                        (f"class:diagnostic-{diagnostic.level}", diagnostic.code)
                    )
                if diagnostic.message:
                    if line:
                        line.append(("", " - "))
                    line.append(("", diagnostic.message))
                    break
        return line

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        return ([self.current_diagnostic_message], [])

    def __pt_container__(self) -> Container:
        """Return the widget's container."""
        return self.container

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus & ~has_selection,
    )
    async def _show_contextual_help() -> None:
        """Display contextual help."""
        from euporie.core.tabs.kernel import KernelTab

        tab = get_app().tab
        if isinstance(tab, KernelTab) and (input_box := tab.current_input) is not None:
            await input_box.inspect()

    @staticmethod
    @add_cmd(filter=buffer_is_code & buffer_has_focus)
    def _history_prev() -> None:
        """Get the previous history entry."""
        from euporie.core.app.current import get_app

        get_app().current_buffer.history_backward()

    @staticmethod
    @add_cmd(filter=buffer_is_code & buffer_has_focus)
    def _history_next() -> None:
        """Get the next history entry."""
        from euporie.core.app.current import get_app

        get_app().current_buffer.history_forward()

    @staticmethod
    @add_cmd()
    def _reformat_input() -> None:
        """Format the contents of the current input field."""
        from euporie.core.app.current import get_app
        from euporie.core.tabs.kernel import KernelTab

        if (
            (tab := get_app().tab)
            and (isinstance(tab, KernelTab))
            and (current_input := tab.current_input)
        ):
            current_input.reformat()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.widgets.inputs:KernelInput": {
                "show-contextual-help": "s-tab",
                "history-prev": "c-A-up",
                "history-next": "c-A-down",
            }
        }
    )


class StdInput:
    """A widget to accept kernel input."""

    def __init__(self, kernel_tab: KernelTab) -> None:
        """Create a new kernel input box."""
        from euporie.core.widgets.forms import LabelledWidget, Text

        self.kernel_tab = kernel_tab
        self.last_focused: FocusableElement | None = None

        self.password = False
        self.prompt: str | None = None
        self.active = False
        self.visible = Condition(lambda: self.active)

        text = Text(
            multiline=False,
            accept_handler=self.accept,
            password=Condition(lambda: self.password),
            style="class:input",
        )
        self.window = text.window
        self.container = ConditionalContainer(
            LabelledWidget(
                body=text,
                label=lambda: self.prompt or ">>>",
            ),
            filter=self.visible,
        )

    def accept(self, buffer: Buffer) -> bool:
        """Send the input to the kernel and hide the input box."""
        if self.kernel_tab.kernel is not None:
            self.kernel_tab.kernel.input(buffer.text)
        # Cleanup
        self.active = False

        buffer.text = ""
        if self.last_focused:
            try:
                get_app().layout.focus(self.last_focused)
            except ValueError:
                pass
        return True

    def get_input(
        self,
        prompt: str = "Please enter a value: ",
        password: bool = False,
    ) -> None:
        """Prompt the user for input and sends the result to the kernel."""
        self.password = password
        self.prompt = prompt

        # Set this first so the height of the cell includes the input box if it gets
        # rendered when we scroll to it
        self.active = True
        # Remember what was focused before
        app = get_app()
        layout = app.layout
        self.last_focused = layout.current_control

        # Try focusing the input box - we create an asynchronous task which will
        # probably run after the next render, when the stdin_box is recognised as being
        # in the layout. This doesn't always work (depending on timing), does usually.
        try:
            layout.focus(self)
        finally:

            async def _focus_input() -> None:
                # Focus the input box
                if self.window in layout.visible_windows:
                    layout.focus(self)
                # Redraw the screen to show it as focused
                app.invalidate()

            app.create_background_task(_focus_input())

    def __pt_container__(self) -> AnyContainer:
        """Return the input's container."""
        return self.container
