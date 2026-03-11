"""Toolbar widgets for apptk applications.

This module provides enhanced toolbar widgets that extend prompt_toolkit's
built-in toolbars with additional functionality:

- SearchToolbar: Enhanced search with smart case sensitivity
- CommandBar: Vim-style command palette for executing registered commands
- StatusBar: Context-sensitive status display using __pt_status__ protocol
- HorizontalCompletionsMenu: Grid-based completion menu for toolbars
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from math import ceil
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.buffer import Buffer
from apptk.cache import FastDictCache
from apptk.commands import COMMANDS, add_cmd, get_cmd
from apptk.completion.base import Completer, Completion
from apptk.data_structures import Point
from apptk.enums import COMMAND_BUFFER, SEARCH_BUFFER
from apptk.filters import buffer_has_focus, has_completions, has_focus, is_done
from apptk.filters.base import Condition
from apptk.filters.modes import navigation_mode
from apptk.filters.utils import to_filter
from apptk.formatted_text import to_formatted_text
from apptk.formatted_text.utils import apply_style, pad, truncate
from apptk.key_binding.key_bindings import KeyBindings
from apptk.key_binding.vi_state import InputMode
from apptk.layout.containers import (
    _CONTAINER_STATUSES,
    ConditionalContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from apptk.layout.controls import (
    BufferControl,
    FormattedTextControl,
    UIContent,
    UIControl,
)
from apptk.layout.dimension import Dimension
from apptk.layout.processors import BeforeInput, HighlightSelectionProcessor
from apptk.lexers import SimpleLexer
from apptk.utils import get_cwidth
from apptk.validation import Validator
from prompt_toolkit.widgets import toolbars as ptk_toolbars

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Unpack

    from apptk.buffer import CompletionState
    from apptk.commands import Command
    from apptk.completion.base import CompleteEvent
    from apptk.document import Document
    from apptk.filters import FilterOrBool
    from apptk.formatted_text import AnyFormattedText, StyleAndTextTuples
    from apptk.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from apptk.key_binding.key_processor import KeyPressEvent
    from apptk.layout.containers import AnyContainer, Container
    from apptk.layout.controls import GetLinePrefixCallable
    from apptk.mouse_events import MouseEvent

    #: Type for status bar fields: (left_fields, right_fields)
    StatusBarFields = tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]

log = logging.getLogger(__name__)

__all__ = [
    # Constants
    "COMMAND_BUFFER",
    "SEARCH_BUFFER",
    # Re-exported from prompt_toolkit
    "ArgToolbar",
    # New
    "CommandBar",
    "CommandCompleter",
    "CompletionsToolbar",
    "FormattedTextToolbar",
    "HorizontalCompletionsMenu",
    # Overridden
    "SearchToolbar",
    "StatusBar",
    "SystemToolbar",
    "ValidationToolbar",
]

# Re-export prompt_toolkit toolbars
ArgToolbar = ptk_toolbars.ArgToolbar
CompletionsToolbar = ptk_toolbars.CompletionsToolbar
FormattedTextToolbar = ptk_toolbars.FormattedTextToolbar
SystemToolbar = ptk_toolbars.SystemToolbar
ValidationToolbar = ptk_toolbars.ValidationToolbar


# =============================================================================
# SearchToolbar
# =============================================================================


class SearchToolbar(ptk_toolbars.SearchToolbar):
    """Enhanced search toolbar with smart case sensitivity.

    Extends prompt_toolkit's SearchToolbar with:
    - Configurable key bindings via commands
    - Smart case sensitivity (case-insensitive when query is lowercase)
    - Customizable styling for prompts

    Args:
        search_buffer: Buffer to use for search input.
        vi_mode: Display '/' and '?' instead of I-search prompts.
        text_if_not_searching: Text to show when not searching.
        forward_search_prompt: Prompt for forward search.
        backward_search_prompt: Prompt for backward search.
        ignore_case: Base ignore case setting.
        auto_ignore_case: Enable smart case (ignore case when query is lowercase).
        key_bindings: Custom key bindings for the search control.
    """

    #: Commands to load key bindings from
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
    ) -> None:
        """Create a new search toolbar instance."""
        if search_buffer is None:
            search_buffer = Buffer(name=SEARCH_BUFFER)

        super().__init__(
            search_buffer=search_buffer,
            vi_mode=vi_mode,
            text_if_not_searching=text_if_not_searching,
            forward_search_prompt=forward_search_prompt,
            backward_search_prompt=backward_search_prompt,
            ignore_case=ignore_case,
        )

        # Set up key bindings
        if key_bindings is not None:
            self.control.key_bindings = key_bindings
        elif self.commands:
            self.control.key_bindings = KeyBindings.from_commands(self.commands)

        # Set up smart case sensitivity
        if auto_ignore_case:
            search_state = self.control.searcher_search_state
            base_ignore_case = to_filter(ignore_case)
            search_state.ignore_case = Condition(
                lambda: (
                    base_ignore_case()
                    or self.search_buffer.text.islower()
                    or search_state.text.islower()
                )
            )


# =============================================================================
# CommandBar
# =============================================================================


@lru_cache
def _parse_cmd(text: str) -> tuple[Command | None, str]:
    """Parse a command line to command and arguments.

    Command names cannot start with digits, so lines starting with digits have an
    empty command string (used for go-to-cell/go-to-line shortcuts).

    Args:
        text: The command line text to parse.

    Returns:
        Tuple of (command or None, arguments string).
    """
    if match := re.fullmatch(r"^(?P<cmd>[^\d][^\s]*|)\s*(?P<args>.*)$", text):
        cmd, args = match.groups()
    else:
        cmd, args = "", ""
    try:
        return get_cmd(cmd), args
    except KeyError:
        return None, args


class CommandCompleter(Completer):
    """Completer for registered commands.

    Provides completions from the global COMMANDS registry, filtering
    out hidden commands and avoiding duplicates. Results are sorted by
    match quality: exact matches first, then prefix, substring, and
    fuzzy matches.
    """

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Complete registered commands, sorted by match quality.

        Results are sorted by: exact match on name/alias, then prefix match,
        then substring match. Within each tier, results are sorted
        alphabetically by command name.

        Args:
            document: The current document.
            complete_event: The completion event.

        Yields:
            Completion objects for matching commands, sorted by relevance.
        """
        query = document.text
        if not query:
            return

        query_lower = query.lower()
        matches: dict[Command, int] = {}

        for alias, command in COMMANDS.items():
            if command.hidden():
                continue

            # Determine match rank: 0=exact, 1=prefix, 2=substring
            alias_lower = alias.lower()
            if query_lower == alias_lower:
                rank = 0
            elif alias_lower.startswith(query_lower):
                rank = 1
            elif query_lower in alias_lower:
                rank = 2
            else:
                continue
            if command not in matches or matches[command] > rank:
                matches[command] = rank

        for command, _rank in sorted(matches.items(), key=lambda x: (x[1], x[0].name)):
            yield Completion(
                command.name,
                start_position=-len(query),
                display=command.name,
                display_meta=command.description,
            )


class CommandBar:
    """Vim-style command bar for executing registered commands.

    A modal toolbar that allows entry of commands with completion support.
    Activated with ':' (vim style) or 'Alt-:'.

    Args:
        prompt: The prompt to display before command input.
        style: Style class for the toolbar.
    """

    #: Flag to track if commands have been registered
    _commands_registered: bool = False

    def __init__(
        self,
        prompt: AnyFormattedText = ":",
        style: str = "class:command-toolbar",
    ) -> None:
        """Create a new command bar instance."""
        self.prompt = prompt
        self.style = style

        self.buffer = Buffer(
            completer=CommandCompleter(),
            complete_while_typing=True,
            name=COMMAND_BUFFER,
            multiline=False,
            accept_handler=self._accept,
            validator=Validator.from_callable(
                validate_func=self._validate,
                error_message="Command not recognised",
                move_cursor_to_end=True,
            ),
        )
        self.control = BufferControl(
            buffer=self.buffer,
            lexer=SimpleLexer(style=f"{style}.text"),
            input_processors=[
                BeforeInput(prompt, style=f"{style}.prompt"),
                HighlightSelectionProcessor(),
            ],
            include_default_input_processors=False,
            key_bindings=KeyBindings.from_commands(("deactivate-command-bar",)),
        )
        self.window = Window(
            self.control,
            height=1,
            style=style,
        )
        self.container = ConditionalContainer(
            content=self.window,
            filter=has_focus(self.buffer),
        )

    def _validate(self, text: str) -> bool:
        """Verify that a valid command has been entered.

        Args:
            text: The command text to validate.

        Returns:
            True if the command is valid.
        """
        cmd, _args = _parse_cmd(text)
        return bool(cmd)

    def _accept(self, buffer: Buffer) -> bool:
        """Handle command acceptance.

        Args:
            buffer: The command buffer.

        Returns:
            False to clear the buffer text.
        """
        app = get_app()
        app.vi_state.input_mode = InputMode.NAVIGATION
        app.helix_state.input_mode = InputMode.NAVIGATION
        app.layout.focus_last()
        text = buffer.text.strip()
        cmd, args = _parse_cmd(text)
        if cmd:
            cmd.run(args)
        return False

    def __pt_container__(self) -> Container:
        """Return the widget's container."""
        return self.container

    @add_cmd(
        name="activate-command-bar",
        hidden=True,
        bindings=[
            {"keys": "A-:", "is_global": True},
            {
                "keys": ":",
                "filter": ~buffer_has_focus | navigation_mode,
            },
        ],
    )
    def _activate_command_bar(event: KeyPressEvent) -> None:
        """Enter command mode."""
        event.app.layout.focus(COMMAND_BUFFER)
        event.app.vi_state.input_mode = InputMode.INSERT
        event.app.helix_state.input_mode = InputMode.INSERT

    @add_cmd(
        name="activate-command-bar-shell",
        hidden=True,
        bindings=[
            {"keys": ["A-!"], "is_global": True},
            {"keys": ["!"], "filter": ~buffer_has_focus | navigation_mode},
        ],
    )
    def _activate_command_bar_shell(event: KeyPressEvent) -> None:
        """Enter command mode with shell prefix."""
        app = event.app
        layout = app.layout
        layout.focus(COMMAND_BUFFER)
        event.app.vi_state.input_mode = InputMode.INSERT
        event.app.helix_state.input_mode = InputMode.INSERT
        if isinstance(control := layout.current_control, BufferControl):
            buffer = control.buffer
            buffer.text = "shell "
            buffer.cursor_position = 6

    @add_cmd(
        name="deactivate-command-bar",
        keys=["escape", "c-c"],
        hidden=True,
    )
    def _deactivate_command_bar(event: KeyPressEvent) -> None:
        """Exit command mode."""
        app = event.app
        layout = app.layout
        layout.focus(COMMAND_BUFFER)
        if isinstance(control := layout.current_control, BufferControl):
            app.vi_state.input_mode = InputMode.NAVIGATION
            app.helix_state.input_mode = InputMode.NAVIGATION
            buffer = control.buffer
            buffer.reset()
            app.layout.focus_previous()

    @staticmethod
    @add_cmd(aliases=["shell", "!"])
    async def _run_shell_command(
        event: KeyPressEvent, *cmd_arg: Unpack[tuple[str]]
    ) -> None:
        """Run system command."""
        command = " ".join(str(x) for x in cmd_arg)
        if command:
            await event.app.run_system_command(
                command,
                display_before_text=[("bold", "$ "), ("", f"{command}\n")],
            )


# =============================================================================
# StatusBar
# =============================================================================


class StatusBar:
    """Context-sensitive status bar using __pt_status__ protocol.

    Displays status information by walking up the container hierarchy from
    the current focused window, collecting status fields from containers
    that implement the __pt_status__ protocol.

    Args:
        filter: Condition for when to show the status bar.
        default: Default status fields when none are found.
        left_style: Style for the left status section.
        right_style: Style for the right status section.
        left_separator: Separator characters for left fields (before, after).
        right_separator: Separator characters for right fields (before, after).
    """

    def __init__(
        self,
        filter: FilterOrBool = True,
        default: StatusBarFields | None = None,
        left_style: str = "class:status",
        right_style: str = "class:status.right",
        left_separator: tuple[str, str] = ("", ""),
        right_separator: tuple[str, str] = ("", ""),
    ) -> None:
        """Create a new status bar instance."""
        self.default: StatusBarFields = default or ([], [])
        self.left_style = left_style
        self.right_style = right_style
        self.left_separator = left_separator
        self.right_separator = right_separator

        self._status_cache: FastDictCache[tuple[int], list[StyleAndTextTuples]] = (
            FastDictCache(self._status, size=1)
        )

        self.container = ConditionalContainer(
            content=VSplit(
                [
                    Window(
                        FormattedTextControl(
                            lambda: self._status_cache[get_app().render_counter,][0]
                        ),
                        style=left_style,
                    ),
                    Window(
                        FormattedTextControl(
                            lambda: self._status_cache[get_app().render_counter,][1]
                        ),
                        style=right_style,
                        align=WindowAlign.RIGHT,
                    ),
                ],
                height=1,
            ),
            filter=to_filter(filter),
        )

    def _status(self, render_counter: int = 0) -> list[StyleAndTextTuples]:
        """Load and format the current status bar entries.

        Args:
            render_counter: The current render counter (for cache invalidation).

        Returns:
            List of [left_fragments, right_fragments].
        """
        layout = get_app().layout

        entries: tuple[list[AnyFormattedText], list[AnyFormattedText]] = ([], [])

        current: Container | None = layout.current_window
        while current:
            if (
                callable(
                    func := (
                        _CONTAINER_STATUSES.get(current)
                        or getattr(current, "__pt_status__", None)
                    )
                )
                and (result := func()) is not None
            ):
                # Add parent entries to start of left side
                entries[0][0:0] = result[0]
                # Add parent entries to end of right side
                entries[1].extend(result[1])

            # If current window has no parent, update child to parent map
            if current not in layout._child_to_parent:
                layout.update_parents_relations()
            current = layout._child_to_parent.get(current)

        # Format the status entries
        output: list[StyleAndTextTuples] = []
        separators = [self.left_separator, self.right_separator]
        for i, entry in enumerate(entries):
            sep_before, sep_after = separators[i]
            output.append([])
            for field in entry:
                if field:
                    output[-1] += [
                        ("class:status-sep", sep_before),
                        *to_formatted_text(field, style="class:status-field"),
                        ("class:status-sep", sep_after),
                    ]
        return output

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container


# =============================================================================
# HorizontalCompletionsMenu
# =============================================================================


class _HorizontalCompletionMenuControl(UIControl):
    """Control for displaying completions in a horizontal grid layout."""

    def __init__(self, min_item_width: int = 5, max_item_width: int = 30) -> None:
        """Initialize with item width constraints.

        Args:
            min_item_width: Minimum width for each completion item.
            max_item_width: Maximum width for each completion item.
        """
        self.max_item_width = max_item_width
        self.min_item_width = min_item_width

    def preferred_width(self, max_available_width: int) -> int | None:
        """Fill available width."""
        return max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Calculate rows needed, filling width first then overflowing."""
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return 0

        col_width = self._get_col_width(complete_state, width, max_available_height)
        height = min(
            ceil(col_width * len(complete_state.completions) / width),
            max_available_height,
        )
        return height

    def _get_col_width(
        self, complete_state: CompletionState, width: int, height: int
    ) -> int:
        """Calculate optimal width for menu items.

        Args:
            complete_state: Current completion state.
            width: Available width.
            height: Available height.

        Returns:
            Optimal column width.
        """
        completions = complete_state.completions
        item_width = max(
            min(
                max(get_cwidth(c.display_text) + 3 for c in completions),
                self.max_item_width,
            ),
            self.min_item_width,
        )
        col_count = width // item_width
        # With overflow, reduce column width to show more of truncated column
        if len(completions) > col_count * height:
            col_width = min((width - 6) // col_count, item_width)
        # With exact fit, expand columns to fill space
        elif len(completions) == col_count * height:
            col_width = max(width // col_count, item_width)
        # Otherwise use calculated item width
        else:
            col_width = item_width
        return col_width

    def create_content(self, width: int, height: int) -> UIContent:
        """Create UIContent for the completion menu.

        Args:
            width: Available width.
            height: Available height.

        Returns:
            UIContent with completion grid.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return UIContent()

        completions = complete_state.completions
        index = complete_state.complete_index  # Can be None!

        # Calculate width of completions menu
        col_width = self._get_col_width(complete_state, width, height)
        # Calculate offset to ensure active completion is visible
        cur_col = (index or 0) // height
        visible_cols = width // col_width
        offset = max(0, cur_col - visible_cols + 1) * height

        # Pad and style visible items
        items: list[StyleAndTextTuples] = []
        item: StyleAndTextTuples
        for i in range(offset, offset + ((visible_cols + 1) * height)):
            if i < len(completions):
                item = completions[i].display
                item = truncate(item, col_width - 3)
                item = pad(item, width=col_width - 3)
                item = [("", " "), *item, ("", " ")]
                item = apply_style(item, "class:completion")
                if i == index:
                    item = apply_style(item, "class:current")
                item = [*item, ("", " ")]
            else:
                item = [("", " " * col_width)]
            items.append(item)

        # Construct rows
        overflow_left = offset > height
        overflow_right = (len(completions) - offset) - (visible_cols * height) > 0
        lines: list[StyleAndTextTuples] = (
            [
                [("class:overflow", "◀" if i == height // 2 else " ")]
                for i in range(height)
            ]
            if overflow_left
            else [[] for _ in range(height)]
        )
        for i, item in enumerate(items):
            row = i % height
            col = i // height
            if col == visible_cols:
                item = [
                    *truncate(
                        item,
                        width - overflow_left - overflow_right - col_width * col,
                        placeholder="",
                    ),
                    ("class:overflow", "▶" if row == height // 2 else " "),
                ]
            lines[row].extend(item)

        def get_line(i: int) -> StyleAndTextTuples:
            return lines[i]

        return UIContent(
            get_line=get_line,
            cursor_position=Point(x=0, y=0),
            line_count=len(lines),
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events."""
        return NotImplemented

    def move_cursor_down(self) -> None:
        """Request to move cursor down."""

    def move_cursor_up(self) -> None:
        """Request to move cursor up."""

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Return key bindings for this control."""
        return None


class _CompletionMetaControl(UIControl):
    """Control that shows meta information of the selected completion."""

    def preferred_width(self, max_available_width: int) -> int | None:
        """Report width of active meta text."""
        if (
            (state := get_app().current_buffer.complete_state)
            and (current_completion := state.current_completion)
            and (text := current_completion.display_meta_text)
        ):
            return get_cwidth(text) + 2
        return 0

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Maintain a single line."""
        return 1

    def create_content(self, width: int, height: int) -> UIContent:
        """Format the current completion meta text.

        Args:
            width: Available width.
            height: Available height.

        Returns:
            UIContent with meta text.
        """
        ft: StyleAndTextTuples = []
        if (
            (state := get_app().current_buffer.complete_state)
            and (current_completion := state.current_completion)
            and (meta := current_completion.display_meta)
        ):
            ft = apply_style([("", " "), *meta, ("", " ")], style="class:meta")

        def get_line(i: int) -> StyleAndTextTuples:
            return ft

        return UIContent(get_line=get_line, line_count=1 if ft else 0)


class HorizontalCompletionsMenu(ConditionalContainer):
    """Horizontal grid-based completion menu for toolbars.

    Displays completions in a horizontal grid layout with overflow indicators,
    suitable for use in toolbar contexts.

    Args:
        filter: Additional filter for when to show the menu.
        min_item_width: Minimum width for each completion item.
        max_item_width: Maximum width for each completion item.
        max_height: Maximum height of the menu.
        show_meta: Whether to show meta information for selected completion.
        style: Style class for the menu.
    """

    def __init__(
        self,
        filter: FilterOrBool = True,
        min_item_width: int = 5,
        max_item_width: int = 30,
        max_height: int = 8,
        show_meta: bool = True,
        style: str = "class:completion-toolbar",
    ) -> None:
        """Create a new horizontal completions menu."""
        children: list[AnyContainer] = []

        if show_meta:
            children.append(
                ConditionalContainer(
                    Window(
                        content=_CompletionMetaControl(),
                        height=1,
                        dont_extend_width=True,
                    ),
                    filter=Condition(
                        lambda: bool(
                            (complete_state := get_app().current_buffer.complete_state)
                            and (completion := complete_state.current_completion)
                            and completion.display_meta
                        )
                    ),
                )
            )

        children.append(
            Window(
                content=_HorizontalCompletionMenuControl(
                    min_item_width=min_item_width,
                    max_item_width=max_item_width,
                ),
                height=Dimension(min=1, max=max_height),
                dont_extend_height=True,
                dont_extend_width=False,
            )
        )

        super().__init__(
            content=HSplit(children, style=style),
            filter=has_completions & ~is_done & to_filter(filter),
        )
