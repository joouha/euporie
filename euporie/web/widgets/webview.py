"""Defines a web-view control."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.eventloop.utils import run_in_executor_with_context
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.commands import add_cmd
from euporie.core.formatted_text.html import HTML, Node
from euporie.core.formatted_text.utils import max_line_width, paste
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.path import parse_path

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Iterable

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.layout.controls import GetLinePrefixCallable
    from prompt_toolkit.layout.mouse_handlers import MouseHandler


log = logging.getLogger(__name__)


@Condition
def webview_has_focus() -> bool:
    """Determine if there is a currently focused webview."""
    return isinstance(get_app().layout.current_control, WebViewControl)


class WebViewControl(UIControl):
    """Web view displays.

    A control which displays rendered HTML content.
    """

    def __init__(self, url: str | Path) -> None:
        """Create a new web-view control instance."""
        self._cursor_position = Point(0, 0)
        self.dirty = False
        self.fragments: StyleAndTextTuples = []
        self.width = 0
        self.height = 0
        self.url: Path | None = None
        self.status = ""

        self.rendered = Event(self)
        self.on_cursor_position_changed = Event(self)

        self.prev_stack: list[Path] = []
        self.next_stack: list[Path] = []

        # self.cursor_processor = CursorProcessor(
        #     lambda: self.cursor_position, style="fg:red"
        # )

        self.key_bindings = load_registered_bindings(
            "euporie.web.widgets.webview.WebViewControl"
        )

        self._dom_cache: FastDictCache[tuple[Path], HTML] = FastDictCache(
            get_value=self.get_dom, size=100
        )
        self._fragment_cache: FastDictCache[
            tuple[HTML, int, int], StyleAndTextTuples
        ] = FastDictCache(get_value=self.get_fragments, size=100_000)
        self._content_cache: FastDictCache = FastDictCache(self.get_content, size=1_000)

        self.load_url(url)

        # Start a new event loop in a thread
        self.thread = None

    @cached_property
    def window(self) -> Window:
        """Get the control's window."""
        for window in get_app().layout.find_all_windows():
            if window.content == self:
                return window
        return Window()

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

    def get_dom(self, url: Path) -> HTML:
        """Load a HTML page as renderable formatted text."""
        return HTML(
            markup=url.read_text(),
            base=url,
            mouse_handler=self._node_mouse_handler,
            paste_fixed=False,
        )

    def get_fragments(self, dom: HTML, width: int, height: int) -> StyleAndTextTuples:
        """Render a HTML page as lines of formatted text."""
        return dom.render(width, height)

    def load_url(self, url: str | Path, save: bool = True) -> None:
        """Load a new URL."""
        # Update navigation history
        if self.url and save:
            self.prev_stack.append(self.url)
            self.next_stack.clear()
        # Update url
        url = parse_path(url)
        self.url = url
        # Reset rendering
        self.dirty = True
        self.rendered.fire()

    def nav_prev(self) -> None:
        """Navigate forwards through the browser history."""
        if self.url and self.prev_stack:
            self.next_stack.append(self.url)
            self.load_url(self.prev_stack.pop(), save=False)

    def nav_next(self) -> None:
        """Navigate backwards through the browser history."""
        if self.url and self.next_stack:
            self.prev_stack.append(self.url)
            self.load_url(self.next_stack.pop(), save=False)

    def render(self) -> None:
        """Render the HTML DOM in a thread."""

        def _render_in_thread() -> None:
            assert self.url is not None
            dom = self._dom_cache[self.url,]
            self.fragments = self._fragment_cache[dom, self.width, self.height]
            self.dirty = False
            # Scroll to the top
            self.window.vertical_scroll = 0
            self.cursor_position = Point(0, 0)
            self.rendered.fire()

        # self.thread = threading.Thread(target=_render_in_thread, daemon=True)
        # self.thread.start()
        if self.url:
            run_in_executor_with_context(_render_in_thread)

    def reset(self) -> None:
        """Reset the state of the control."""

    def preferred_width(self, max_available_width: int) -> int | None:
        """Calculate and return the preferred width of the control."""
        return None

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Calculate and return the preferred height of the control."""
        return None

    def is_focusable(self) -> bool:
        """Tell whether this user control is focusable."""
        return True

    def get_content(
        self, url: Path, dirty: bool, width: int, height: int, cursor_position: Point
    ) -> UIContent:
        """Create a cacheable UIContent."""
        if self.dirty:
            lines = [[], [("", " " * ((width - 8) // 2)), ("fg:#888888", "Loading…")]]
        else:
            lines = list(split_lines(self.fragments))

        def get_line(i: int) -> StyleAndTextTuples:
            try:
                line = lines[i]
            except IndexError:
                return []

            # Paste fixed elements
            if (dom := self._dom_cache[url,]).fixed:
                visible_line = max(0, i - self.window.vertical_scroll)
                fixed_lines = list(split_lines(dom.fixed_mask))
                if visible_line < len(fixed_lines):
                    line = paste(
                        fixed_lines[visible_line], line, 0, 0, transparent=True
                    )

            # Apply processors
            # merged_processor = self.cursor_processor
            # line = lines[i]
            # transformation = merged_processor.apply_transformation(
            #     TransformationInput(
            #         buffer_control=self, document=Document(), lineno=i, source_to_display=lambda i: i, fragments=line, width=width, height=height,
            #     )
            # )
            # return transformation.fragments

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
        # Trigger a re-render if things have changed
        if self.dirty or width != self.width or height != self.height:
            self.width = width
            self.height = height
            self.render()

        return self._content_cache[
            self.url, self.dirty, width, height, self.cursor_position
        ]

    def _node_mouse_handler(
        self, node: Node, mouse_event: MouseEvent
    ) -> NotImplementedOrNone:
        """Handle click events."""
        if url := node.attrs.get("_link_path"):
            # TODO - Check for #anchor links and scroll accordingly
            if (
                mouse_event.button == MouseButton.LEFT
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.load_url(url)
                return None
            elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
                self.status = str(url)
                return None
        return NotImplemented

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events.

        When `NotImplemented` is returned, it means that the given event is not
        handled by the `UIControl` itself. The `Window` or key bindings can
        decide to handle this event as scrolling or changing focus.

        Args:
            mouse_event: `MouseEvent` instance.

        Returns:
            NotImplemented if the UI does not need to be updates, None if it does
        """
        # Focus on click
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
        # if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
        # self.cursor_position = mouse_event.position

        # if mouse_event.event_type == MouseEventType.MOUSE_UP:
        handler: MouseHandler | None = None
        try:
            content = self._content_cache[
                self.url, self.dirty, self.width, self.height, self.cursor_position
            ]
            line = content.get_line(mouse_event.position.y)
        except IndexError:
            return NotImplemented
        else:
            # Find position in the fragment list.
            xpos = mouse_event.position.x
            # Find mouse handler for this character.
            count = 0
            for item in line:
                count += len(item[1])
                if count > xpos:
                    if len(item) >= 3:
                        handler = item[2]
                        if callable(handler):
                            return handler(mouse_event)
                    else:
                        break

        if callable(handler):
            return handler

        self.status = ""

        return NotImplemented

    @property
    def content_width(self) -> int:
        """Return the width of the content."""
        # return max(fragment_list_width(line) for line in self.lines)
        return max_line_width(self.fragments)

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
        """Return a list of `Event` objects, which can be a generator.

        the application collects all these events, in order to bind redraw
        handlers to these events.
        """
        yield self.rendered
        yield self.on_cursor_position_changed

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _webview_nav_prev() -> None:
        """Navigate backwards in the browser history."""
        from euporie.web.widgets.webview import WebViewControl

        current_control = get_app().layout.current_control
        if isinstance(current_control, WebViewControl):
            current_control.nav_prev()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _webview_nav_next() -> None:
        """Navigate forwards in the browser history."""
        from euporie.web.widgets.webview import WebViewControl

        current_control = get_app().layout.current_control
        if isinstance(current_control, WebViewControl):
            current_control.nav_next()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _scroll_webview_left() -> None:
        """Scroll the display up one line."""
        from euporie.core.widgets.display import DisplayWindow

        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_left()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _scroll_webview_right() -> None:
        """Scroll the display down one line."""
        from euporie.core.widgets.display import DisplayWindow

        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_right()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _scroll_webview_up() -> None:
        """Scroll the display up one line."""
        get_app().layout.current_window._scroll_up()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _scroll_webview_down() -> None:
        """Scroll the display down one line."""
        get_app().layout.current_window._scroll_down()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _page_up_webview() -> None:
        """Scroll the display up one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_up()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _page_down_webview() -> None:
        """Scroll the display down one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_down()

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _go_to_start_of_webview() -> None:
        """Scroll the display to the top."""
        from euporie.web.widgets.webview import WebViewControl

        current_control = get_app().layout.current_control
        if isinstance(current_control, WebViewControl):
            current_control.cursor_position = Point(0, 0)

    @staticmethod
    @add_cmd(filter=webview_has_focus)
    def _go_to_end_of_webview() -> None:
        """Scroll the display down one page."""
        from euporie.web.widgets.webview import WebViewControl

        layout = get_app().layout
        current_control = layout.current_control
        window = layout.current_window
        if (
            isinstance(current_control, WebViewControl)
            and window.render_info is not None
        ):
            current_control.cursor_position = Point(
                0, window.render_info.ui_content.line_count - 1
            )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.web.widgets.webview.WebViewControl": {
                "scroll-webview-left": "left",
                "scroll-webview-right": "right",
                "scroll-webview-up": ["up", "k"],
                "scroll-webview-down": ["down", "j"],
                "page-up-webview": "pageup",
                "page-down-webview": "pagedown",
                "go-to-start-of-webview": "home",
                "go-to-end-of-webview": "end",
                "webview-nav-prev": ("escape", "left"),
                "webview-nav-next": ("escape", "right"),
            }
        }
    )


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.key_binding.key_bindings import KeyBindings
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.output.color_depth import ColorDepth
    from prompt_toolkit.styles.style import Style

    from euporie.core.style import HTML_STYLE
    from euporie.core.widgets.display import DisplayWindow
    from euporie.web.widgets.webview import WebViewControl  # noqa F811

    kb = KeyBindings()
    kb.add("q")(lambda event: event.app.exit())
    layout = Layout(container=DisplayWindow(WebViewControl(UPath(sys.argv[-1]))))
    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        style=Style(HTML_STYLE),
        mouse_support=True,
        color_depth=ColorDepth.DEPTH_24_BIT,
    )
    app.run()
