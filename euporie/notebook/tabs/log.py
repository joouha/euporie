"""Initiate logging for euporie.core."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import SearchToolbar

from euporie.core.log import LOG_QUEUE, QueueHandler
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.path import parse_path
from euporie.core.tabs.base import Tab
from euporie.core.widgets.formatted_text_area import FormattedTextArea

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from prompt_toolkit.formatted_text.base import FormattedText

    from euporie.core.app.app import BaseApp


class LogView(Tab):
    """A tab which allows you to view log entries."""

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Create a new log view tab instance."""
        super().__init__(app, path)
        # Build the container
        self.search_field = SearchToolbar(
            text_if_not_searching=[("class:not-searching", "Press '/' to search.")]
        )
        self.text_area = FormattedTextArea(
            formatted_text=[],
            read_only=True,
            scrollbar=False,
            line_numbers=Condition(lambda: self.app.config.line_numbers),
            search_field=self.search_field,
            focus_on_click=True,
            wrap_lines=False,
            dont_extend_width=False,
        )
        self.container = HSplit(
            [
                VSplit(
                    [
                        self.text_area,
                        MarginContainer(
                            ScrollbarMargin(), target=self.text_area.window
                        ),
                    ]
                ),
                self.search_field,
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )
        self.hook_id = QueueHandler.hook(self.add_record)
        # Add text to the textarea
        for record in LOG_QUEUE:
            self.add_record(record)
        # Hook the queue handler
        self.text_area.window.cursorline = has_focus(self)

    def add_record(self, message: FormattedText) -> None:
        """Add a single new record to the textarea.

        Args:
            message: The formatted log record to add

        """
        cp = self.text_area.buffer.cursor_position
        self.text_area.formatted_text += message
        self.text_area.buffer.cursor_position = cp

    @property
    def title(self) -> str:
        """Return the title of this tab."""
        suffix = (
            f" ({parse_path(self.app.config.log_file).name})"
            if self.app.config.log_file
            else ""
        )
        return f"Logs{suffix}"

    def close(self, cb: Callable | None = None) -> None:
        """Remove log queue handler hook on close."""
        QueueHandler.unhook(self.hook_id)
        super().close(cb=cb)
