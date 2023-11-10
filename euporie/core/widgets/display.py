"""Define custom controls which re-render on resize."""

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING, cast

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.formatted_text.utils import fragment_list_width, split_lines
from prompt_toolkit.layout.containers import ConditionalContainer, VSplit, Window
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event, to_str

from euporie.core.commands import add_cmd
from euporie.core.convert.datum import Datum
from euporie.core.current import get_app
from euporie.core.filters import (
    display_has_focus,
    scrollable,
)
from euporie.core.ft.utils import wrap
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.utils import run_in_thread_with_context
from euporie.core.widgets.graphics import (
    GraphicProcessor,
)

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition


log = logging.getLogger(__name__)


class DisplayControl(UIControl):
    """Web view displays.

    A control which displays rendered HTML content.
    """

    _window: Window

    def __init__(
        self,
        datum: Datum,
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        threaded: bool = False,
    ) -> None:
        """Create a new web-view control instance."""
        self._datum = datum
        self.focusable = to_filter(focusable)
        self.focus_on_click = to_filter(focus_on_click)
        self.wrap_lines = to_filter(wrap_lines)
        self.threaded = threaded

        self._cursor_position = Point(0, 0)
        self.loading = False
        self.resizing = False
        self.rendering = False
        self.lines: list[StyleAndTextTuples] = []

        self.graphic_processor = GraphicProcessor(control=self)

        self.width = 0
        self.height = 0

        self.key_bindings = load_registered_bindings(
            "euporie.core.widgets.display.DisplayControl"
        )

        self.rendered = Event(self)
        self.on_cursor_position_changed = Event(self)
        self.invalidate_events: list[Event[object]] = [
            self.rendered,
            self.on_cursor_position_changed,
        ]

        self._line_cache: FastDictCache[
            tuple[Datum, int | None, int | None, bool], list[StyleAndTextTuples]
        ] = FastDictCache(get_value=self.get_lines, size=100_000)
        self._content_cache: FastDictCache = FastDictCache(self.get_content, size=1_000)

    @property
    def datum(self) -> Any:
        """Return the control's display data."""
        return self._datum

    @datum.setter
    def datum(self, value: Any) -> None:
        """Set the control's data."""
        self._datum = value
        # Trigger "loading" view
        self.loading = True
        # Signal that the control has updated
        self.rendered.fire()
        self.reset()

    @property
    def cursor_position(self) -> Point:
        """Get the cursor position."""
        return self._cursor_position

    @cursor_position.setter
    def cursor_position(self, value: Point) -> None:
        """Set the cursor position."""
        changed = self._cursor_position != value
        self._cursor_position = value
        if changed:
            self.on_cursor_position_changed.fire()

    def get_lines(
        self,
        datum: Datum,
        width: int | None,
        height: int | None,
        wrap_lines: bool = False,
    ) -> list[StyleAndTextTuples]:
        """Render the lines to display in the control."""
        ft = datum.convert(to="ft", cols=width, rows=height)
        if width and height:
            key = Datum.add_size(datum, Size(height, self.width))
            ft = [(f"[Graphic_{key}]", ""), *ft]
        lines = list(split_lines(ft))
        if wrap_lines and width:
            lines = [
                wrapped_line
                for line in lines
                for wrapped_line in split_lines(
                    wrap(line, width, truncate_long_words=False)
                )
            ]
        # Ensure we have enough lines to fill the requested height
        if height is not None:
            lines.extend([[]] * max(0, height - len(lines)))
        return lines

    def render(self) -> None:
        """Render the HTML DOM in a thread."""
        datum = self.datum
        wrap_lines = self.wrap_lines()

        max_cols, aspect = self.datum.cell_size()
        cols = min(max_cols, self.width) if max_cols else self.width
        rows = ceil(cols * aspect) if aspect else self.height

        def _render() -> None:
            # Potentially redirect url
            self.lines = self._line_cache[datum, cols, rows, wrap_lines]
            self.loading = False
            self.resizing = False
            self.rendering = False
            self.rendered.fire()

        if not self.rendering:
            self.rendering = True
            if self.threaded:
                run_in_thread_with_context(_render)
            else:
                _render()

    def reset(self) -> None:
        """Reset the state of the control."""

    def preferred_width(self, max_available_width: int) -> int | None:
        """Calculate and return the preferred width of the control."""
        max_cols, aspect = self.datum.cell_size()
        return min(max_cols, max_available_width) if max_cols else max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Calculate and return the preferred height of the control."""
        max_cols, aspect = self.datum.cell_size()
        if aspect:
            return ceil(min(width, max_cols) * aspect)

        self.lines = self._line_cache[self.datum, width, None, self.wrap_lines()]
        return len(self.lines)

    def is_focusable(self) -> bool:
        """Tell whether this user control is focusable."""
        return self.focusable()

    def get_content(
        self,
        datum: Datum,
        width: int,
        height: int,
        loading: bool,
        cursor_position: Point,
    ) -> UIContent:
        """Create a cacheable UIContent."""
        if self.loading:
            lines = [
                cast("StyleAndTextTuples", []),
                cast(
                    "StyleAndTextTuples",
                    [
                        ("", " " * ((self.width - 8) // 2)),
                        ("class:loading", "Loading…"),
                    ],
                ),
            ]
        else:
            lines = self.lines

        def get_line(i: int) -> StyleAndTextTuples:
            try:
                line = lines[i]
            except IndexError:
                return []
            return line

        return UIContent(
            get_line=get_line,
            line_count=len(lines),
            cursor_position=self.cursor_position,
            show_cursor=False,
        )

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate the content for this user control.

        Returns:
            A :class:`.UIContent` instance.
        """
        # Trigger a re-render in the future if things have changed
        if self.loading:
            self.render()
        if width != self.width:
            self.resizing = True
            self.width = width
            self.height = height
            self.render()

        content = self._content_cache[
            self.datum,
            width,
            height,
            self.loading,
            self.cursor_position,
        ]

        # Check for graphics in content
        self.graphic_processor.load(content)

        return content

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Mouse handler for this control."""
        if self.focus_on_click() and mouse_event.event_type == MouseEventType.MOUSE_UP:
            get_app().layout.current_control = self
            return None
        return NotImplemented

    @property
    def content_width(self) -> int:
        """Return the width of the content."""
        return max(fragment_list_width(line) for line in self.lines)

    def move_cursor_down(self) -> None:
        """Move the cursor down one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x, y=y + 1)

    def move_cursor_up(self) -> None:
        """Move the cursor up one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x, y=max(0, y - 1))

    def move_cursor_left(self) -> None:
        """Move the cursor down one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=max(0, x - 1), y=y)

    def move_cursor_right(self) -> None:
        """Move the cursor up one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x + 1, y=y)

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Return key bindings that are specific for this user control.

        Returns:
            A :class:`.KeyBindings` object if some key bindings are specified, or
                `None` otherwise.
        """
        return self.key_bindings

    def get_invalidate_events(self) -> Iterable[Event[object]]:
        """Return the Window invalidate events."""
        yield from self.invalidate_events


class DisplayWindow(Window):
    """A window sub-class which can scroll left and right."""

    content: DisplayControl
    vertical_scroll: int

    def _write_to_screen_at_index(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
    ) -> None:
        """Enure the :attr:`horizontal_scroll` is recorded."""
        super()._write_to_screen_at_index(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
        )
        # Set the horizontal scroll offset on the render info
        # TODO - fix this upstream
        if self.render_info is not None:
            setattr(  # noqa B010
                self.render_info, "horizontal_scroll", self.horizontal_scroll
            )

    def _scroll_up(self) -> NotImplementedOrNone:  # type: ignore [override]
        """Scroll window up."""
        info = self.render_info
        if info is None:
            return NotImplemented
        if info.vertical_scroll > 0:
            # TODO: not entirely correct yet in case of line wrapping and long lines.
            if (
                info.cursor_position.y
                >= info.window_height - 1 - info.configured_scroll_offsets.bottom
            ):
                self.content.move_cursor_up()
            self.vertical_scroll -= 1
            return None
        return NotImplemented

    def _scroll_down(self) -> NotImplementedOrNone:  # type: ignore [override]
        """Scroll window down."""
        info = self.render_info

        if info is None:
            return NotImplemented

        if self.vertical_scroll < info.content_height - info.window_height:
            if info.cursor_position.y <= info.configured_scroll_offsets.top:
                self.content.move_cursor_down()
            self.vertical_scroll += 1
            return None

        return NotImplemented

    def _scroll_right(self) -> NotImplementedOrNone:
        """Scroll window right."""
        info = self.render_info
        if info is None:
            return NotImplemented
        content_width = self.content.content_width
        if self.horizontal_scroll < content_width - info.window_width:
            if info.cursor_position.y <= info.configured_scroll_offsets.right:
                self.content.move_cursor_right()
            self.horizontal_scroll += 1
            return None
        return NotImplemented

    def _scroll_left(self) -> NotImplementedOrNone:
        """Scroll window left."""
        info = self.render_info
        if info is None:
            return NotImplemented
        horizontal_scroll = getattr(self.render_info, "horizontal_scroll", 0)  # B009
        if horizontal_scroll > 0:
            self.content.move_cursor_left()
            self.horizontal_scroll -= 1
            return None
        return NotImplemented

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_left() -> None:
        """Scroll the display up one line."""
        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_left()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_right() -> None:
        """Scroll the display down one line."""
        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_right()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_up() -> None:
        """Scroll the display up one line."""
        get_app().layout.current_window._scroll_up()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_down() -> None:
        """Scroll the display down one line."""
        get_app().layout.current_window._scroll_down()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _page_up_display() -> None:
        """Scroll the display up one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_up()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _page_down_display() -> None:
        """Scroll the display down one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_down()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _go_to_start_of_display() -> None:
        """Scroll the display to the top."""
        from euporie.core.widgets.display import DisplayControl

        current_control = get_app().layout.current_control
        if isinstance(current_control, DisplayControl):
            current_control.cursor_position = Point(0, 0)

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _go_to_end_of_display() -> None:
        """Scroll the display down one page."""
        from euporie.core.widgets.display import DisplayControl

        layout = get_app().layout
        current_control = layout.current_control
        window = layout.current_window
        if (
            isinstance(current_control, DisplayControl)
            and window.render_info is not None
        ):
            current_control.cursor_position = Point(
                0, window.render_info.ui_content.line_count - 1
            )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.widgets.display.DisplayControl": {
                "scroll-display-left": "left",
                "scroll-display-right": "right",
                "scroll-display-up": ["up", "k"],
                "scroll-display-down": ["down", "j"],
                "page-up-display": "pageup",
                "page-down-display": "pagedown",
                "go-to-start-of-display": "home",
                "go-to-end-of-display": "end",
            }
        }
    )


class Display:
    """Rich output displays.

    A container for displaying rich output data.

    """

    def __init__(
        self,
        datum: Datum,
        height: AnyDimension = None,
        width: AnyDimension = None,
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        always_hide_cursor: FilterOrBool = True,
        scrollbar: FilterOrBool = True,
        scrollbar_autohide: FilterOrBool = True,
        dont_extend_height: FilterOrBool = True,
        style: str | Callable[[], str] = "",
    ) -> None:
        """Instantiate an Output container object.

        Args:
            datum: Displayable data
            height: The height of the output in terminal cells
            width: The width of the output in terminal cells
            focusable: If the output should be focusable
            focus_on_click: If the output should become focused when clicked
            wrap_lines: If the output's lines should be wrapped
            always_hide_cursor: When true, the cursor is never shown
            scrollbar: Whether to show a scrollbar
            scrollbar_autohide: Whether to automatically hide the scrollbar
            dont_extend_height: Whether the window should fill the available height
            style: The style to apply to the output

        """
        self._style = style

        self.control = DisplayControl(
            datum,
            focusable=focusable,
            focus_on_click=focus_on_click,
            wrap_lines=wrap_lines,
        )

        self.window = DisplayWindow(
            content=self.control,
            height=height,
            width=width,
            wrap_lines=False,
            always_hide_cursor=always_hide_cursor,
            dont_extend_height=dont_extend_height,
            style=self.style,
            char=" ",
        )

        self.container = VSplit(
            [
                self.window,
                ConditionalContainer(
                    MarginContainer(ScrollbarMargin(), target=self.window),
                    filter=to_filter(scrollbar)
                    & (
                        ~to_filter(scrollbar_autohide)
                        | (to_filter(scrollbar_autohide) & scrollable(self.window))
                    ),
                ),
            ]
        )

    def style(self) -> str:
        """Use the background color of the data as the default style."""
        style = to_str(self._style)
        if bg := self.control.datum.bg:
            style = f"bg:{bg} {style}"
        return style

    @property
    def datum(self) -> Any:
        """Return the display's current data."""
        return self.control.datum

    @datum.setter
    def datum(self, value: Datum) -> None:
        """Set the display container's data."""
        self.control.datum = value

    def __pt_container__(self) -> AnyContainer:
        """Return the content of this output."""
        return self.container
