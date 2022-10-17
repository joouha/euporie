"""Defines a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters import (
    Condition,
    buffer_has_focus,
    has_focus,
    has_selection,
    is_done,
    is_searching,
    to_filter,
)
from prompt_toolkit.key_binding.key_bindings import merge_key_bindings
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.processors import (  # HighlightSearchProcessor,
    ConditionalProcessor,
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightMatchingBracketProcessor,
    HighlightSelectionProcessor,
    TabsProcessor,
)
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer
from prompt_toolkit.widgets import TextArea
from pygments.lexers import get_lexer_by_name

from euporie.core.app import get_app
from euporie.core.commands import add_cmd
from euporie.core.config import add_setting
from euporie.core.filters import buffer_is_code
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.margins import NumberedDiffMargin, OverflowMargin, ScrollbarMargin
from euporie.core.processors import (
    AppendLineAutoSuggestion,
    ShowTrailingWhiteSpaceProcessor,
)
from euporie.core.suggest import ConditionalAutoSuggestAsync
from euporie.core.widgets.pager import PagerState

if TYPE_CHECKING:
    from typing import Any, Callable, Optional, Sequence, Union

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.key_binding.key_bindings import KeyBindingsBase
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.layout.margins import Margin

    from euporie.core.tabs.base import KernelTab


log = logging.getLogger(__name__)


class KernelInput(TextArea):
    """Kernel input text areas.

    A customized text area for the cell input.
    """

    def __init__(
        self,
        kernel_tab: "KernelTab",
        *args: "Any",
        left_margins: "Optional[Sequence[Margin]]" = None,
        right_margins: "Optional[Sequence[Margin]]" = None,
        on_text_changed: "Optional[Callable[[Buffer], None]]" = None,
        on_cursor_position_changed: "Optional[Callable[[Buffer], None]]" = None,
        tempfile_suffix: "Union[str, Callable[[], str]]" = "",
        key_bindings: "Optional[KeyBindingsBase]" = None,
        enable_history_search: "Optional[FilterOrBool]" = False,
        focusable: "FilterOrBool" = True,
        wrap_lines: "FilterOrBool" = False,
        complete_while_typing: "FilterOrBool" = True,
        autosuggest_while_typing: "FilterOrBool" = True,
        validate_while_typing: "Optional[FilterOrBool]" = None,
        **kwargs: "Any",
    ) -> "None":
        """Initiate the cell input box."""
        self.kernel_tab = kernel_tab
        app = kernel_tab.app

        kwargs.setdefault("wrap_lines", wrap_lines)
        kwargs.setdefault("style", "class:kernel-input")
        kwargs.setdefault("history", kernel_tab.history)
        kwargs.setdefault("search_field", app.search_bar)
        kwargs.setdefault("focus_on_click", True)
        kwargs.setdefault(
            "input_processors",
            [
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
            ],
        )
        kwargs.setdefault("completer", kernel_tab.completer)
        kwargs.setdefault(
            "lexer",
            DynamicLexer(
                lambda: PygmentsLexer(
                    get_lexer_by_name(self.kernel_tab.language).__class__,
                    sync_from_start=False,
                )
            ),
        )
        kwargs.setdefault(
            "auto_suggest",
            ConditionalAutoSuggestAsync(
                self.kernel_tab.suggester,
                filter=to_filter(autosuggest_while_typing)
                & Condition(lambda: app.config.autosuggest),
            ),
        )
        kwargs["complete_while_typing"] = Condition(
            lambda: app.config.autocomplete
        ) & to_filter(complete_while_typing)

        super().__init__(*args, **kwargs)

        if validate_while_typing:
            self.buffer.validate_while_typing = to_filter(validate_while_typing)

        self.control.include_default_input_processors = False
        if on_text_changed:
            self.buffer.on_text_changed += on_text_changed
        if on_cursor_position_changed:
            self.buffer.on_cursor_position_changed += on_cursor_position_changed
        self.buffer.tempfile_suffix = tempfile_suffix or kernel_tab.kernel_lang_file_ext

        if enable_history_search is not None:
            self.buffer.enable_history_search = to_filter(enable_history_search)

        self.has_focus = has_focus(self)

        # Replace the autosuggest processor
        # Skip type checking as PT should use "("Optional[Sequence[Processor]]"
        # instead of "Optional[list[Processor]]"
        # TODO make a PR for this
        self.control.input_processors[0] = ConditionalProcessor(  # type: ignore
            AppendLineAutoSuggestion(),
            has_focus(self.buffer) & ~is_done,
        )

        # Set style
        style = kwargs.get("style", "")
        self.window.style = lambda: (
            "class:text-area " + ("class:focused " if self.has_focus() else "") + style
        )

        # Add configurable line numbers
        self.window.left_margins = left_margins or [
            ConditionalMargin(
                NumberedDiffMargin(),
                Condition(lambda: self.kernel_tab.app.config.line_numbers),
            )
        ]
        self.window.right_margins = right_margins or [
            OverflowMargin(),
            ScrollbarMargin(),
        ]

        self.window.cursorline = self.has_focus

        # Set extra key-bindings
        widgets_key_bindings = load_registered_bindings(
            "euporie.core.widgets.inputs.KernelInput"
        )
        if key_bindings:
            widgets_key_bindings = merge_key_bindings(
                [key_bindings, widgets_key_bindings]
            )
        self.control.key_bindings = widgets_key_bindings

    def inspect(self) -> "None":
        """Get contextual help for the current cursor position in the current cell."""
        code = self.buffer.text
        cursor_pos = self.buffer.cursor_position

        pager = self.kernel_tab.app.pager
        assert pager is not None

        if pager.visible() and pager.state is not None:
            if pager.state.code == code and pager.state.cursor_pos == cursor_pos:
                pager.focus()
                return

        def _cb(response: "dict") -> "None":
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
    def _show_contextual_help() -> "None":
        """Displays contextual help."""
        from euporie.core.tabs.notebook import BaseNotebook

        nb = get_app().tab
        if isinstance(nb, BaseNotebook):
            nb.cell.input_box.inspect()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.widgets.inputs.KernelInput": {
                "show-contextual-help": "s-tab",
            }
        }
    )


class StdInput:
    """A widget to accept kernel input."""

    def __init__(self, kernel_tab: "KernelTab") -> "None":
        """Create a new kernel input box."""
        from euporie.core.widgets.forms import LabelledWidget, Text

        self.kernel_tab = kernel_tab
        self.last_focused: "Optional[FocusableElement]" = None

        self.password = False
        self.prompt: "Optional[str]" = None
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

    def accept(self, buffer: "Buffer") -> "bool":
        """Send the input to the kernel and hide the input box."""
        if self.kernel_tab.kernel.kc is not None:
            self.kernel_tab.kernel.kc.input(buffer.text)
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
        prompt: "str" = "Please enter a value: ",
        password: "bool" = False,
    ) -> "None":
        """Prompts the user for input and sends the result to the kernel."""
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

            async def _focus_input() -> "None":
                # Focus the input box
                if self.window in layout.visible_windows:
                    layout.focus(self)
                # Redraw the screen to show it as focused
                app.invalidate()

            app.create_background_task(_focus_input())

    def __pt_container__(self) -> "AnyContainer":
        """Return the input's container."""
        return self.container
