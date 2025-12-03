"""Define a minimap display widget."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from code_minimap import render as render_minimap
from prompt_toolkit.cache import FastDictCache, SimpleCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
)
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, UIContent, UIControl
from prompt_toolkit.mouse_events import MouseButton, MouseEventType

from euporie.core.app.current import get_app
from euporie.core.margins import MarginContainer, ScrollbarMargin

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterable

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.controls import GetLinePrefixCallable
    from prompt_toolkit.mouse_events import MouseEvent
    from prompt_toolkit.utils import Event

    from euporie.core.tabs.base import Tab


log = logging.getLogger(__name__)


class MiniMapControl(UIControl):
    """A control to render minimaps for all buffers in the current tab."""

    def __init__(self, hscale: float = 0.5, vscale: float = 0.25) -> None:
        """Initialize the control.

        Args:
            hscale: Horizontal scale factor for the minimap.
            vscale: Vertical scale factor for the minimap.
        """
        self.hscale = hscale
        self.vscale = vscale
        self.cursor_position = Point(0, 0)
        self._window_lines: list[tuple[Window, int]] = []

        self._minimap_cache: FastDictCache[tuple[str, float, float], list[str]] = (
            FastDictCache(self._render_minimap, size=100)
        )
        self._content_cache: SimpleCache[
            Hashable, tuple[UIContent, list[tuple[Window, int]]]
        ] = SimpleCache(maxsize=8)

    def _render_minimap(self, text: str, hscale: float, vscale: float) -> list[str]:
        """Render the minimap for the given text.

        Args:
            text: The text content to render.
            hscale: Horizontal scale factor.
            vscale: Vertical scale factor.

        Returns:
            A list of strings representing the minimap lines.
        """
        try:
            minimap_str = render_minimap(text, hscale=hscale, vscale=vscale)
            return minimap_str.split("\n")
        except Exception:
            log.exception("Error rendering minimap")
            return []

    def reset(self) -> None:
        """Reset the control."""
        self._minimap_cache.clear()
        self._content_cache.clear()

    def preferred_width(self, max_available_width: int) -> int | None:
        """Use all available width."""
        return max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Use all available height."""
        return max_available_height

    def is_focusable(self) -> bool:
        """Tell whether this user control is focusable."""
        return True

    def _get_buffers(self, tab: Tab) -> dict[Buffer, Window]:
        """Get all buffers from the current tab.

        Args:
            tab: The current tab.

        Returns:
            A list of (buffer, window) tuples.
        """
        buffers: dict[Buffer, Window] = {}
        try:
            windows = tab.__pt_searchables__()
        except NotImplementedError:
            return buffers

        for window in windows:
            if isinstance(control := window.content, BufferControl):
                buffers[control.buffer] = window
        return buffers

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate the content for this user control."""
        tab = get_app().tab

        # Build cache key from buffer texts and dimensions
        buffers: dict[Buffer, Window] = {}
        buffer_texts: tuple[str, ...] = ()
        if tab is not None:
            buffers.update(self._get_buffers(tab))
            buffer_texts = tuple(buffer.document.text for buffer in buffers)

        cache_key: Hashable = (
            buffer_texts,
            tuple(id(w) for w in buffers),
            width,
            self.hscale,
            self.vscale,
            self.cursor_position,
        )

        def get_content() -> tuple[UIContent, list[tuple[Window, int]]]:
            lines: list[StyleAndTextTuples] = []
            window_lines: list[tuple[Window, int]] = []

            for buffer, window in buffers.items():
                text = buffer.document.text
                minimap_lines = self._minimap_cache[text, self.hscale, self.vscale]

                # Add a separator between buffers, or top border of first buffer minimap
                sep = "🮀" if lines else "🭻"
                lines.append([("class:border", " " + sep * (width - 2))])
                window_lines.append((window, -1))

                # Add minimap lines for this buffer
                for i, line in enumerate(minimap_lines):
                    # Pad or truncate to fit width
                    line = line[: width - 2].ljust(width - 2)
                    lines.append(
                        [
                            ("class:border", "🮇"),
                            ("class:kernel-input", line),
                            ("class:border", "▎"),
                        ]
                    )
                    window_lines.append((window, i))
            # Add final border below last buffer minimap
            if lines:
                lines.append([("class:border", " " + "🭶" * (width - 2))])
                window_lines.append((window, -1))

            def get_line(i: int) -> StyleAndTextTuples:
                return lines[i] if i < len(lines) else [("", " " * width)]

            return (
                UIContent(
                    get_line=get_line,
                    line_count=max(len(lines), 1),
                    cursor_position=self.cursor_position,
                    show_cursor=False,
                ),
                window_lines,
            )

        content, self._window_lines = self._content_cache.get(cache_key, get_content)
        return content

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events to navigate to the corresponding line."""
        if (
            mouse_event.event_type == MouseEventType.MOUSE_DOWN
            and mouse_event.button == MouseButton.LEFT
        ):
            y = mouse_event.position.y
            if 0 <= y < len(self._window_lines):
                window, minimap_line = self._window_lines[y]
                if (
                    isinstance((control := window.content), BufferControl)
                    # Not a border
                    and minimap_line >= 0
                ):
                    # Calculate the approximate line in the source buffer
                    buffer = control.buffer
                    text = buffer.document.text
                    minimap_lines = self._minimap_cache[text, self.hscale, self.vscale]
                    if minimap_lines:
                        total_source_lines = buffer.document.line_count
                        total_minimap_lines = len(minimap_lines)
                        if total_minimap_lines > 0:
                            # Map click position to source line
                            source_line = int(
                                (minimap_line / total_minimap_lines)
                                * total_source_lines
                            )
                            source_line = max(
                                0, min(source_line, total_source_lines - 1)
                            )
                            buffer.cursor_position = (
                                buffer.document.translate_row_col_to_index(
                                    source_line, 0
                                )
                            )
                            # Focus the source window
                            get_app().layout.current_window = window
                            return None
        return NotImplemented

    def move_cursor_down(self) -> None:
        """Request to move the cursor down."""
        self.cursor_position = self.cursor_position._replace(
            y=self.cursor_position.y + 1
        )

    def move_cursor_up(self) -> None:
        """Request to move the cursor up."""
        self.cursor_position = self.cursor_position._replace(
            y=max(0, self.cursor_position.y - 1)
        )

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Key bindings that are specific for this user control."""
        return None

    def get_invalidate_events(self) -> Iterable[Event[object]]:
        """Return a list of `Event` objects."""
        return []


class MiniMap:
    """A minimap widget displaying minimaps of all buffers in the current tab."""

    def __init__(self, hscale: float = 0.5, vscale: float = 1) -> None:
        """Construct the widget.

        Args:
            hscale: Horizontal scale factor for the minimap.
            vscale: Vertical scale factor for the minimap.
        """
        window = Window(
            MiniMapControl(hscale=hscale, vscale=vscale),  # style="class:face"
        )
        self.container = HSplit(
            [VSplit([window, MarginContainer(ScrollbarMargin(), target=window)])],
            style="class:minimap",
        )

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container
