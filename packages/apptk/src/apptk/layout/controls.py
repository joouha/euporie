"""Miscellaneous control fields."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.data_structures import Point
from apptk.filters.modes import helix_mode
from apptk.lexers import DynamicLexer
from apptk.lexers.pygments import PygmentsLexer
from apptk.mouse_events import MouseEventType
from apptk.selection import SelectionType
from apptk.utils import get_cwidth
from prompt_toolkit.layout.controls import (
    BufferControl as PtkBufferControl,
)
from prompt_toolkit.layout.controls import (
    GetLinePrefixCallable,
    UIControl,
)
from prompt_toolkit.layout.controls import UIContent as PtkUIContent

if TYPE_CHECKING:
    from apptk.formatted_text import StyleAndTextTuples
    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from apptk.mouse_events import MouseEvent as PtkMouseEvent

__all__ = [
    "BufferControl",
    "DummyControl",
    "FocusableDummyControl",
    "GetLinePrefixCallable",
    "UIContent",
]

log = logging.getLogger(__name__)


class BufferControl(PtkBufferControl):
    """Extended BufferControl with Helix cursor semantics and language info."""

    @property
    def language(self) -> str | None:
        """Return the language of the buffer based on the current lexer.

        Returns:
            The language name in lowercase, or an empty string if unknown.
        """
        lexer = self.lexer
        if isinstance(lexer, DynamicLexer):
            lexer = lexer.get_lexer()
        if isinstance(lexer, PygmentsLexer):
            return lexer.pygments_lexer_cls.name.lower()
        return None

    def create_content(
        self, width: int, height: int, preview_search: bool = False
    ) -> PtkUIContent:
        """Render content with the block cursor placed at the correct position.

        In Helix mode the head sits one past the last selected character
        (gap-indexed ``[anchor, head)``).  For character selections the block
        appears at ``head - 1``.  For line selections the block appears at
        the end of the last selected line (the newline position = beyond the
        last visible character), and the spurious one-character highlight
        that ptk's vi-mode inclusive-end rule bleeds onto the following line
        is stripped.
        """
        content = super().create_content(width, height, preview_search=preview_search)

        if not helix_mode():
            return content

        buff = self.buffer
        sel = buff.selection_state
        if sel is None:
            return content

        head = buff.cursor_position
        anchor = sel.original_cursor_position
        if head <= anchor:
            return content  # backward or point selection - block at head is correct

        if sel.type == SelectionType.LINES:
            # Line selection: the block cursor sits at the end of the last
            # selected line (the newline position = beyond the last visible
            # character).  When head is at the start of a line the block goes
            # to the preceding character (the newline of the previous line).
            head_row, head_col = buff.document.translate_index_to_position(head)
            if head_col == 0 and head_row > 0:
                block_idx = head - 1
            else:
                block_idx = head
            row, col = buff.document.translate_index_to_position(block_idx)
            if self._last_get_processed_line is not None:
                content.cursor_position = Point(
                    x=self._last_get_processed_line(row).source_to_display(col),
                    y=row,
                )
            # ptk's vi-mode inclusive-end rule (``to_column += 1`` in
            # ``Document.selection_range_at_line``) causes the selection
            # highlight to bleed one character onto the line *after* head
            # whenever head sits at a line start.  Strip that spurious
            # highlight by removing ``class:selected`` from any line whose
            # start index is at or beyond the head.
            original_get_line = content.get_line

            def _get_line_no_selection_bleed(line_number: int) -> list[tuple[str, str]]:
                frags = original_get_line(line_number)
                row_start = buff.document.translate_row_col_to_index(line_number, 0)
                if row_start >= head:
                    return [
                        (item[0].replace("class:selected", "").strip(), *item[1:])
                        for item in frags
                    ]
                return frags

            content.get_line = _get_line_no_selection_bleed
        else:
            # Character / block selection: draw block at the last selected
            # character (head - 1).
            adj_idx = max(0, head - 1)
            row, col = buff.document.translate_index_to_position(adj_idx)
            if self._last_get_processed_line is not None:
                content.cursor_position = Point(
                    x=self._last_get_processed_line(row).source_to_display(col),
                    y=row,
                )

        return content

    def mouse_handler(self, mouse_event: PtkMouseEvent) -> NotImplementedOrNone:
        """Mouse handler using Helix cursor semantics.

        In Helix mode, forward selections place the head one past the last
        selected character and the anchor follows Helix's 1-width rule, so the
        rendered block cursor stays directly under the mouse while dragging.
        All other modes delegate to the base implementation.
        """
        if not helix_mode():
            return super().mouse_handler(mouse_event)

        from apptk.key_binding.bindings.helix import _helix_put_cursor
        from prompt_toolkit.mouse_events import MouseButton

        buffer = self.buffer
        mouse_pos = mouse_event.position

        if get_app().layout.current_control == self:
            if self._last_get_processed_line is None:
                return NotImplemented

            processed_line = self._last_get_processed_line(mouse_pos.y)
            xpos = processed_line.display_to_source(mouse_pos.x)
            index = buffer.document.translate_row_col_to_index(mouse_pos.y, xpos)
            event_type = mouse_event.event_type

            if event_type == MouseEventType.MOUSE_DOWN:
                buffer.exit_selection()
                buffer.cursor_position = index

            elif (
                event_type == MouseEventType.MOUSE_MOVE
                and mouse_event.button != MouseButton.NONE
            ):
                if (
                    buffer.selection_state is None
                    and abs(buffer.cursor_position - index) > 0
                ):
                    # Ensure the anchor sits at the position where the drag
                    # started (the MOUSE_DOWN position).
                    buffer.start_selection(selection_type=SelectionType.CHARACTERS)
                _helix_put_cursor(buffer, index, extend=True)

            elif event_type == MouseEventType.MOUSE_UP:
                if buffer.selection_state is not None:
                    _helix_put_cursor(buffer, index, extend=True)
        else:
            if (
                self.focus_on_click()
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                get_app().layout.current_control = self
            else:
                return NotImplemented

        return None


class UIContent(PtkUIContent):
    """Content generated by a user control.

    Adds ability to search for the position of graphics.
    """

    @cached_property
    def graphic_positions(self) -> dict[str, Point]:
        """Scan content lines for graphic markers and return their positions.

        Returns:
            Dictionary mapping graphic keys to their (x, y) positions in content coordinates.
        """
        positions: dict[str, Point] = {}
        get_line = self.get_line
        for y in range(self.line_count):
            line = get_line(y)
            x = 0
            for style, text, *_ in line:
                for part in style.split():
                    if part.startswith("[Graphic_") and part.endswith("]"):
                        key = part[9:-1]  # Extract key from [Graphic_xxx]
                        positions[key] = Point(x, y)
                    if part.startswith("[") and part.endswith("]"):
                        break
                else:
                    x += get_cwidth(text)
        return positions


class DummyControl(UIControl):
    """A dummy control object that doesn't paint any content."""

    def create_content(self, width: int, height: int) -> UIContent:
        """Return one blank line only."""

        def get_line(i: int) -> StyleAndTextTuples:
            return []

        return UIContent(get_line=get_line, line_count=1)


class FocusableDummyControl(DummyControl):
    """A dummy control object that doesn't paint any content."""

    def is_focusable(self) -> bool:
        """Make this control focusable."""
        return True
