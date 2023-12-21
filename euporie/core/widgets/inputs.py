"""Define a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from prompt_toolkit.auto_suggest import AutoSuggest, DynamicAutoSuggest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, DynamicCompleter
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

from euporie.core.commands import add_cmd
from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.filters import buffer_is_code, scrollable
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.layout.containers import Window
from euporie.core.margins import NumberedDiffMargin, OverflowMargin, ScrollbarMargin
from euporie.core.processors import (
    AppendLineAutoSuggestion,
    ShowTrailingWhiteSpaceProcessor,
)
from euporie.core.suggest import ConditionalAutoSuggestAsync
from euporie.core.widgets.pager import PagerState

if TYPE_CHECKING:
    from typing import Callable, Sequence

    from prompt_toolkit.buffer import BufferAcceptHandler
    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import (
        AnyFormattedText,
    )
    from prompt_toolkit.history import History
    from prompt_toolkit.key_binding.key_bindings import KeyBindingsBase
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.layout.margins import Margin
    from prompt_toolkit.lexers.base import Lexer

    from euporie.core.tabs.base import KernelTab


log = logging.getLogger(__name__)


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
        preview_search: FilterOrBool = True,
        prompt: AnyFormattedText = "",
        input_processors: list[Processor] | None = None,
        name: str = "",
        left_margins: Sequence[Margin] | None = None,
        right_margins: Sequence[Margin] | None = None,
        on_text_changed: Callable[[Buffer], None] | None = None,
        on_cursor_position_changed: Callable[[Buffer], None] | None = None,
        tempfile_suffix: str | Callable[[], str] = "",
        key_bindings: KeyBindingsBase | None = None,
        enable_history_search: FilterOrBool | None = False,
        autosuggest_while_typing: FilterOrBool = True,
        validate_while_typing: FilterOrBool = False,
        scroll_offsets: ScrollOffsets | None = None,
    ) -> None:
        """Initiate the cell input box."""
        self.kernel_tab = kernel_tab
        app = kernel_tab.app

        if history is None:
            history = kernel_tab.history

        if search_field is None:
            search_control = app.search_bar
        if isinstance(search_field, SearchToolbar):
            search_control = search_field.control
        else:
            search_control = None

        if input_processors is None:
            input_processors = []

        def _get_lexer() -> Lexer:
            try:
                pygments_lexer_class = get_lexer_by_name(
                    self.kernel_tab.language
                ).__class__
            except ClassNotFound:
                return SimpleLexer()
            else:
                return PygmentsLexer(pygments_lexer_class, sync_from_start=False)

        # Writeable attributes.
        self.completer = completer or kernel_tab.completer
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
        self.lexer = lexer

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

        # Set extra key-bindings
        widgets_key_bindings = load_registered_bindings(
            "euporie.core.widgets.inputs.KernelInput"
        )
        if key_bindings:
            widgets_key_bindings = merge_key_bindings(
                [key_bindings, widgets_key_bindings]
            )

        self.control = BufferControl(
            buffer=self.buffer,
            lexer=DynamicLexer(lambda: self.lexer or _get_lexer()),
            input_processors=[
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
                HighlightMatchingBracketProcessor(),
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
                NumberedDiffMargin(),
                app.config.filter("line_numbers") & self.buffer.multiline,
                # & Condition(lambda: len(self.buffer.text.split("\n")) > 1),
            )
        ]
        scrollbar_margin = ConditionalMargin(
            ScrollbarMargin(), filter=to_filter(scrollbar)
        )
        right_margins = [OverflowMargin(), scrollbar_margin]
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
        scrollbar_margin.filter &= scrollable(self.window)

        self.has_focus = has_focus(self.buffer)

    def inspect(self) -> None:
        """Get contextual help for the current cursor position in the current cell."""
        code = self.buffer.text
        cursor_pos = self.buffer.cursor_position

        pager = self.kernel_tab.app.pager
        assert pager is not None

        if (
            pager.visible()
            and pager.state is not None
            and pager.state.code == code
            and pager.state.cursor_pos == cursor_pos
        ):
            pager.focus()
            return

        def _cb(response: dict) -> None:
            assert pager is not None
            prev_state = pager.state
            new_state = PagerState(
                code=code,
                cursor_pos=cursor_pos,
                response=response,
            )
            if prev_state != new_state:
                pager.state = new_state
                self.kernel_tab.app.invalidate()

        self.kernel_tab.kernel.inspect(
            code=code,
            cursor_pos=cursor_pos,
            callback=_cb,
        )

    # ################################### Settings ####################################

    add_setting(
        name="line_numbers",
        flags=["--line-numbers"],
        type_=bool,
        help_="Show or hide line numbers",
        default=True,
        description="""
            Whether line numbers are shown by default.
        """,
        hooks=[lambda x: get_app().refresh()],
    )

    add_setting(
        name="autocomplete",
        flags=["--autocomplete"],
        type_=bool,
        help_="Provide completions suggestions automatically",
        default=False,
        description="""
            Whether to automatically suggestion completions while typing in code cells.
        """,
    )

    add_setting(
        name="autosuggest",
        flags=["--autosuggest"],
        type_=bool,
        help_="Provide line completion suggestions",
        default=True,
        description="""
            Whether to automatically suggestion line content while typing in code cells.
        """,
    )

    add_setting(
        name="autoinspect",
        flags=["--autoinspect"],
        type_=bool,
        help_="Display contextual help automatically",
        default=False,
        description="""
            Whether to automatically display contextual help when navigating through code cells.
        """,
    )

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus & ~has_selection,
    )
    def _show_contextual_help() -> None:
        """Display contextual help."""
        from euporie.core.tabs.notebook import BaseNotebook

        nb = get_app().tab
        if isinstance(nb, BaseNotebook):
            nb.cell.input_box.inspect()

    @staticmethod
    @add_cmd(filter=buffer_is_code & buffer_has_focus)
    def _history_prev() -> None:
        """Get the previous history entry."""
        from euporie.console.app import get_app

        get_app().current_buffer.history_backward()

    @staticmethod
    @add_cmd(filter=buffer_is_code & buffer_has_focus)
    def _history_next() -> None:
        """Get the next history entry."""
        from euporie.console.app import get_app

        get_app().current_buffer.history_forward()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.widgets.inputs.KernelInput": {
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
        self.window = text.text_area.window
        self.container = ConditionalContainer(
            LabelledWidget(
                body=text,
                label=lambda: self.prompt or ">>>",
            ),
            filter=self.visible,
        )

    def accept(self, buffer: Buffer) -> bool:
        """Send the input to the kernel and hide the input box."""
        if self.kernel_tab.kernel.kc is not None:
            self.kernel_tab.kernel.kc.input(buffer.text)
        # Cleanup
        self.active = False

        buffer.text = ""
        if self.last_focused:
            with contextlib.suppress(ValueError):
                get_app().layout.focus(self.last_focused)
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
