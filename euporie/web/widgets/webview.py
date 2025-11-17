"""Defines a web-view control."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.app.current import get_app
from euporie.core.async_utils import get_or_create_loop, run_coro_async
from euporie.core.commands import add_cmd
from euporie.core.convert.datum import Datum
from euporie.core.convert.mime import get_format
from euporie.core.ft.html import HTML, Node
from euporie.core.ft.utils import fragment_list_width, paste
from euporie.core.graphics import GraphicProcessor
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.path import parse_path

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.formatted_text.base import AnyFormattedText, StyleAndTextTuples
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

    _window: Window

    def __init__(
        self,
        url: str | Path = "about:blank",
        link_handler: Callable | None = None,
    ) -> None:
        """Create a new web-view control instance."""
        self._cursor_position = Point(0, 0)
        self.loading = False
        self.resizing = False
        self.rendering = False
        self.stale = False
        self.lines: list[StyleAndTextTuples] = []
        self.graphic_processor = GraphicProcessor(control=self)
        self.width = 0
        self.height = 0
        self.url: Path = UPath(url)
        self.status: list[AnyFormattedText] = []
        self.link_handler = link_handler or self.load_url

        self.render_task: asyncio.Future | None = None
        self.rendered = Event(self)
        self.on_cursor_position_changed = Event(self)

        self.prev_stack: list[Path] = []
        self.next_stack: list[Path] = []

        # self.cursor_processor = CursorProcessor(
        #     lambda: self.cursor_position, style="fg:red"
        # )

        self.loop = get_or_create_loop("convert")

        self.key_bindings = load_registered_bindings(
            "euporie.web.widgets.webview:WebViewControl",
            config=get_app().config,
        )

        self._dom_cache: FastDictCache[tuple[Path], HTML] = FastDictCache(
            get_value=self.get_dom, size=100
        )
        self._content_cache: FastDictCache = FastDictCache(self.get_content, size=1_000)

        self.load_url(url)

    @property
    def window(self) -> Window:
        """Get the control's window."""
        try:
            return self._window
        except AttributeError:
            for window in get_app().layout.find_all_windows():
                if window.content == self:
                    self._window = window
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
        markup = str(
            Datum(
                data=url.read_text(),
                format=(format_ := get_format(url, default="html")),
                path=url,
            ).convert(to="html")
        )
        return HTML(
            markup=markup,
            base=url,
            mouse_handler=self._node_mouse_handler,
            paste_fixed=False,
            _initial_format=format_,
            defer_assets=False,
            on_change=lambda dom: self.invalidate(),
        )

    def invalidate(self) -> None:
        """Trigger a redraw of the webview."""
        self.stale = True
        self.rendered.fire()

    @property
    def dom(self) -> HTML:
        """Return the dom for the current URL."""
        return self._dom_cache[self.url,]

    @property
    def title(self) -> str:
        """Return the title of the current HTML page."""
        if self.loading:
            return self.url.name
        if dom := self.dom:
            return dom.title
        return ""

    def load_url(self, url: str | Path, **kwargs: Any) -> None:
        """Load a new URL."""
        save_to_history = kwargs.get("save_to_history", True)
        # Trigger "loading" view
        self.loading = True
        # Update navigation history
        if self.url and save_to_history:
            self.prev_stack.append(self.url)
            self.next_stack.clear()
        # Update url
        self.url = UPath(url)
        # Scroll to the top
        # self.window.vertical_scroll = 0  # TODO - save scroll in history
        self.cursor_position = Point(0, 0)
        # Signal that the webview has updated
        self.rendered.fire()

    def nav_prev(self) -> None:
        """Navigate forwards through the browser history."""
        if self.url and self.prev_stack:
            self.next_stack.append(self.url)
            self.load_url(self.prev_stack.pop(), save_to_history=False)

    def nav_next(self) -> None:
        """Navigate backwards through the browser history."""
        if self.url and self.next_stack:
            self.prev_stack.append(self.url)
            self.load_url(self.next_stack.pop(), save_to_history=False)

    def render(self, force: bool = False) -> None:
        """Render the HTML DOM in a thread."""
        dom = self.dom

        async def _render() -> None:
            assert self.url is not None
            # Potentially redirect url
            self.url = parse_path(self.url)
            self.lines = list(split_lines(await dom._render(self.width, self.height)))
            # Reset all possible reasons for rendering
            self.loading = self.resizing = self.rendering = self.stale = False
            # Let the app know we're re-rerenderd and the output needs redrawing
            self.rendered.fire()

        if not self.rendering or force:
            self.rendering = True

            if self.render_task:
                self.render_task.cancel()

            self.render_task = run_coro_async(_render(), self.loop)

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
        self,
        url: Path,
        loading: bool,
        resizing: bool,
        width: int,
        height: int,
        cursor_position: Point,
        assets_loaded: bool,
    ) -> UIContent:
        """Create a cacheable UIContent."""
        dom = self._dom_cache[url,]
        if self.loading:
            lines = [
                cast("StyleAndTextTuples", []),
                cast(
                    "StyleAndTextTuples",
                    [("", " " * ((width - 8) // 2)), ("class:loading", "Loading…")],
                ),
            ]
        else:
            lines = self.lines[:]

        def get_line(i: int) -> StyleAndTextTuples:
            try:
                line = lines[i]
            except IndexError:
                line = []

            # Overlay fixed lines onto this line
            if not loading and dom.fixed:
                visible_line = max(0, i - self.window.vertical_scroll)
                fixed_lines = list(split_lines(dom.fixed_mask))
                if visible_line < len(fixed_lines):
                    # Paste the fixed line over the current line
                    fixed_line = fixed_lines[visible_line]
                    line = paste(fixed_line, line, 0, 0, transparent=True)

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
        if self.stale or self.loading:
            self.render()
        if width != self.width:  # or height != self.height:
            # self.resizing = True
            self.width = width
            self.height = height
            self.render()

        content = self._content_cache[
            self.url,
            self.loading,
            self.resizing,
            width,
            height,
            self.cursor_position,
            self.dom.render_count,
        ]

        # Check for graphics in content
        self.graphic_processor.load(content)

        return content

    def _node_mouse_handler(
        self, node: Node, mouse_event: MouseEvent
    ) -> NotImplementedOrNone:
        """Handle click events."""
        url = node.attrs.get("_link_path")
        title = node.attrs.get("title")
        alt = node.attrs.get("alt")
        if url:
            # TODO - Check for #anchor links and scroll accordingly
            if (
                mouse_event.button == MouseButton.LEFT
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.link_handler(url, save_to_history=True, new_tab=False)
                return None
            elif (
                mouse_event.button == MouseButton.MIDDLE
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.link_handler(url, save_to_history=False, new_tab=True)
                return None
        if (url or title) and mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            self.status.clear()
            if title:
                self.status.append(str(title))
            if title:
                self.status.append(str(alt))
            if url:
                self.status.append(str(url))
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
        # Focus on mouse down
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            if not (layout := get_app().layout).has_focus(self):
                layout.focus(self)
                return None
            return NotImplemented
        # if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
        # self.cursor_position = mouse_event.position

        # if mouse_event.event_type == MouseEventType.MOUSE_UP:
        handler: MouseHandler | None = None
        try:
            content = self._content_cache[
                self.url,
                self.loading,
                self.resizing,
                self.width,
                self.height,
                self.cursor_position,
                self.dom.render_count,
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

        if self.status:
            self.status.clear()
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
        """Return a list of `Event` objects, which can be a generator.

        the application collects all these events, in order to bind redraw
        handlers to these events.
        """
        yield self.rendered
        yield self.on_cursor_position_changed
        if dom := self.dom:
            yield dom.on_update

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
            "euporie.web.widgets.webview:WebViewControl": {
                "scroll-webview-left": "left",
                "scroll-webview-right": "right",
                "scroll-webview-up": ["up", "k"],
                "scroll-webview-down": ["down", "j"],
                "page-up-webview": "pageup",
                "page-down-webview": "pagedown",
                "go-to-start-of-webview": "home",
                "go-to-end-of-webview": "end",
                "webview-nav-prev": ("A-left"),
                "webview-nav-next": ("A-right"),
            }
        }
    )


if __name__ == "__main__":
    import sys

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.key_binding.key_bindings import KeyBindings
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.output.color_depth import ColorDepth
    from prompt_toolkit.styles.style import Style

    from euporie.core.style import HTML_STYLE
    from euporie.core.widgets.display import DisplayWindow
    from euporie.web.widgets.webview import WebViewControl

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
