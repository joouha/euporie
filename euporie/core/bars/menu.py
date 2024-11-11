"""Contains a completion menu for toolbars."""

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition, has_completions, is_done
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.utils import get_cwidth

from euporie.core.app.current import get_app
from euporie.core.filters import has_toolbar
from euporie.core.ft.utils import apply_style, pad, truncate
from euporie.core.layout.containers import HSplit

if TYPE_CHECKING:
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.mouse_events import MouseEvent

log = logging.getLogger(__name__)


class ToolbarCompletionMenuControl(UIControl):
    """A completion menu for toolbars."""

    def __init__(self, min_item_width: int = 5, max_item_width: int = 30) -> None:
        """Define minimum and maximum item widhth."""
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
        """Calculate how many rows to use, filling the width first then overflowing."""
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
        """Calculate the optimal width for the items in the menu."""
        completions = complete_state.completions
        item_width = max(
            min(
                max(get_cwidth(c.display_text) + 3 for c in completions),
                self.max_item_width,
            ),
            self.min_item_width,
        )
        col_count = width // item_width
        # With an overflow reduce column width to show more of the truncated column
        if len(completions) > col_count * height:
            col_width = min((width - 6) // col_count, item_width)
        # With an exact width expand columns to fill the space
        elif len(completions) == col_count * height:
            col_width = max(width // col_count, item_width)
        # Otherwise use the calculated item width
        else:
            col_width = item_width
        return col_width

    def create_content(self, width: int, height: int) -> UIContent:
        """Create a UIContent object for this control."""
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return UIContent()

        completions = complete_state.completions
        index = complete_state.complete_index  # Can be None!

        # Calculate width of completions menu.
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
            cursor_position=Point(x=0, y=0),  # y=index or 0),
            line_count=len(lines),
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events.

        When `NotImplemented` is returned, it means that the given event is not
        handled by the `UIControl` itself. The `Window` or key bindings can
        decide to handle this event as scrolling or changing focus.

        :param mouse_event: `MouseEvent` instance.
        """
        return NotImplemented

    def move_cursor_down(self) -> None:
        """Request to move the cursor down.

        This happens when scrolling down and the cursor is completely at the top.
        """

    def move_cursor_up(self) -> None:
        """Request to move the cursor up."""

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Key bindings that are specific for this user control.

        Return a :class:`.KeyBindings` object if some key bindings are
        specified, or `None` otherwise.
        """


class SelectedCompletionMetaControl(UIControl):
    """Control that shows the meta information of the selected completion."""

    def preferred_width(self, max_available_width: int) -> int | None:
        """Report the width of the active meta text."""
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
        """Format the current completion meta text."""
        ft: StyleAndTextTuples = []
        state = get_app().current_buffer.complete_state
        if (
            (state := get_app().current_buffer.complete_state)
            and (current_completion := state.current_completion)
            and (meta := current_completion.display_meta)
        ):
            ft = apply_style([("", " "), *meta, ("", " ")], style="class:meta")

        def get_line(i: int) -> StyleAndTextTuples:
            return ft

        return UIContent(get_line=get_line, line_count=1 if ft else 0)


class ToolbarCompletionsMenu(ConditionalContainer):
    """A completion menu widget for toolbars."""

    def __init__(self) -> None:
        """Create a pre-populated conditional container."""
        super().__init__(
            content=HSplit(
                [
                    ConditionalContainer(
                        Window(
                            content=SelectedCompletionMetaControl(),
                            height=1,
                            dont_extend_width=True,
                        ),
                        filter=Condition(
                            lambda: bool(
                                (
                                    complete_state
                                    := get_app().current_buffer.complete_state
                                )
                                and (completion := complete_state.current_completion)
                                and completion.display_meta
                            )
                        ),
                    ),
                    Window(
                        content=ToolbarCompletionMenuControl(),
                        height=Dimension(min=1, max=8),
                        dont_extend_height=True,
                        dont_extend_width=False,
                    ),
                ],
                style="class:toolbar,menu",
            ),
            filter=has_toolbar & has_completions & ~is_done,
        )
