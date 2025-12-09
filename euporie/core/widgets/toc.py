"""Define a table-of-contents display widget."""

from __future__ import annotations

import logging
from textwrap import wrap
from typing import TYPE_CHECKING, NamedTuple
from weakref import WeakKeyDictionary

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
)
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, UIContent, UIControl
from prompt_toolkit.mouse_events import MouseButton, MouseEventType
from prompt_toolkit.selection import SelectionState

from euporie.core.app.current import get_app
from euporie.core.border import InsetGrid
from euporie.core.cache import SimpleCache
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.widgets.decor import Border
from euporie.core.widgets.forms import Dropdown

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

TOCs = {
    "contents": {
        "pygments.generic.heading": 0,
        "pygments.generic.subheading": 1,
    },
    "symbols": {
        "pygments.name.class": 0,
        "pygments.name.function": 1,
    },
}


class TocEntry(NamedTuple):
    """Entry for tab table of contents."""

    level: int
    text: str
    token: str
    lines: slice
    window: Window


class TocControl(UIControl):
    """A control to render the current tab's table of contents.

    - Get list of current windows
    - store buffer -> window map
    - Retrieve entries for each buffer from entry cache
    - When buffer content changes, update entry list in cache
    """

    def __init__(self, kind: str = "contents") -> None:
        """Initialize the control."""
        self.kind = kind

        self.cursor_position = Point(0, 0)
        self.entries: tuple[TocEntry, ...] = ()

        self.buffer_window_map: WeakKeyDictionary[Buffer, Window] = WeakKeyDictionary()
        self._buffer_entry_cache: FastDictCache[
            tuple[Buffer, Hashable, str], list[TocEntry]
        ] = FastDictCache(self._build_buffer_toc, size=10000)
        self._fragment_cache: FastDictCache[
            tuple[tuple[TocEntry, ...], str, int], list[StyleAndTextTuples]
        ] = FastDictCache(self._get_fragments, size=10)
        self._content_cache: SimpleCache[Hashable, UIContent] = SimpleCache(maxsize=8)

    def reset(self) -> None:
        """Reset the control."""
        # self.entries = ()
        # self._buffer_entry_cache.clear()

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

    def _build_buffer_toc(
        self, buffer: Buffer, lexer_hash: Hashable, text: str
    ) -> list[TocEntry]:
        """Construct a list of TOC entries for a given buffer."""
        entries = []
        # Get lexed unprocessed line from BufferControl
        document = buffer.document
        window = self.buffer_window_map[buffer]
        control = window.content
        assert isinstance(control, BufferControl)
        get_line = control._get_formatted_text_for_line_func(document)
        # Loop variables
        start_line = last_line = last_level = -1
        last_token = text_buffer = ""
        for i in range(document.line_count):
            for style, text, *_ in get_line(i):
                for _type, tokens in TOCs.items():
                    for token, level in tokens.items():
                        if token in style:
                            if text_buffer and (
                                i > last_line + 1 or level != last_level
                            ):
                                entries.append(
                                    TocEntry(
                                        level=last_level,
                                        text=text_buffer.strip(" #=-*"),
                                        token=last_token,
                                        lines=slice(start_line, last_line),
                                        window=window,
                                    )
                                )
                                start_line = i
                                text_buffer = text
                            else:
                                text_buffer = f"{text_buffer} {text}"
                            if start_line < 0:
                                start_line = i
                            last_line = i
                            last_level = level
                            last_token = token
        if text_buffer:
            entries.append(
                TocEntry(
                    level=last_level,
                    text=text_buffer.strip(" #=-*"),
                    token=last_token,
                    lines=slice(start_line, last_line),
                    window=window,
                )
            )
        return entries

    def _build_toc(self, tab: Tab) -> tuple[TocEntry, ...]:
        entries = []
        try:
            windows = tab.__pt_searchables__()
        except NotImplementedError:
            pass
        else:
            for window in windows:
                if isinstance(control := window.content, BufferControl):
                    buffer = control.buffer
                    if window not in self.buffer_window_map:
                        self.buffer_window_map[buffer] = window
                        entries.extend(
                            [
                                entry
                                for entry in self._buffer_entry_cache[
                                    buffer,
                                    control.lexer.invalidation_hash(),
                                    buffer.document.text,
                                ]
                                if entry.token in TOCs[self.kind]
                            ]
                        )
        return tuple(entries)

    def _get_fragments(
        self,
        entries: tuple[TocEntry],
        kind: str,
        width: int,
    ) -> list[StyleAndTextTuples]:
        lines: list[StyleAndTextTuples] = []
        alt = False
        for entry in entries:
            if entry.token in TOCs[kind]:
                style = "class:alt" if alt else ""
                lines.append(
                    [
                        (style, " " + " " * entry.level),
                        (f"{style} class:{entry.token}", entry.text),
                        (style, " " * (width - 1 - len(entry.text) - entry.level)),
                    ]
                )
                alt = not alt
        if not entries:
            lines = [
                [],
                *(
                    [("bold class:placeholder", x.center(width))]
                    for x in wrap("No Headings", width)
                ),
                [],
                *(
                    [("class:placeholder", x.center(width))]
                    for x in wrap(
                        "The table of contents shows headings in "
                        "notebooks and supported files.",
                        width,
                    )
                ),
            ]

        return lines

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate the content for this user control."""
        tab = get_app().tab
        if tab is None:
            entries: tuple[TocEntry, ...] = ()
        else:
            entries = self._build_toc(tab)
        self.entries = entries

        # Create cache key based on all factors that affect content
        cache_key = (entries, self.kind, width, self.cursor_position)

        def get_content() -> UIContent:
            lines = self._fragment_cache[entries, self.kind, width]

            def get_line(i: int) -> StyleAndTextTuples:
                return lines[i] if i < len(lines) else [("", " " * width)]

            return UIContent(
                get_line=get_line,
                line_count=len(lines),
                cursor_position=self.cursor_position,
                show_cursor=False,
            )

        return self._content_cache.get(cache_key, get_content)

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events."""
        if (
            mouse_event.event_type == MouseEventType.MOUSE_DOWN
            and mouse_event.button == MouseButton.LEFT
            and (y := mouse_event.position.y) < len(self.entries)
        ):
            entry: TocEntry = self.entries[y]
            if isinstance(control := entry.window.content, BufferControl):
                buffer: Buffer = control.buffer
                buffer.selection_state = SelectionState(
                    buffer.document.translate_row_col_to_index(entry.lines.stop + 1, 0)
                    - 1
                )
                buffer.selection_state.shift_mode = True
                buffer.cursor_position = buffer.document.translate_row_col_to_index(
                    entry.lines.start, 0
                )
                # Focus the buffer's window
                get_app().layout.current_window = entry.window
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


class TableOfContents:
    """A table of contents widget, which allows switching between TOC types."""

    def __init__(self) -> None:
        """Construct the widget."""
        control = TocControl()
        window = Window(control, style="class:input,list,face,row")
        self.container = HSplit(
            [
                Dropdown(
                    options=list(TOCs),
                    labels=[x.title() for x in TOCs],
                    on_change=lambda s: setattr(control, "kind", s.value),
                ),
                Border(
                    VSplit(
                        [window, MarginContainer(ScrollbarMargin(), target=window)],
                    ),
                    border=InsetGrid,
                    style="class:input,inset,border",
                ),
            ],
            style="class:toc",
        )

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container
