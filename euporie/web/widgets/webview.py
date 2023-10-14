"""Defines a web-view control."""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING, cast

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.containers import Float, Window
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.screen import WritePosition
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.commands import add_cmd
from euporie.core.convert.core import convert, get_format
from euporie.core.current import get_app
from euporie.core.data_structures import DiInt
from euporie.core.ft.html import HTML, Node
from euporie.core.ft.utils import fragment_list_width, paste
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.path import parse_path
from euporie.core.utils import run_in_thread_with_context
from euporie.core.widgets.display import (
    GraphicWindow,
    NotVisible,
    select_graphic_control,
)
from euporie.core.widgets.page import BoundedWritePosition

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable, Iterable

    from prompt_toolkit.formatted_text.base import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.layout.controls import GetLinePrefixCallable
    from prompt_toolkit.layout.mouse_handlers import MouseHandler
    from prompt_toolkit.layout.screen import Screen


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
        self.lines: list[StyleAndTextTuples] = []
        self.graphic_positions: dict[str, tuple[int, int]] = {}
        self.width = 0
        self.height = 0
        self.url: Path = UPath(url)
        self.status: list[AnyFormattedText] = []
        self.link_handler = link_handler or self.load_url

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
        self._line_cache: FastDictCache[
            tuple[HTML, int, int], list[StyleAndTextTuples]
        ] = FastDictCache(get_value=self.get_lines, size=100_000)
        self._content_cache: FastDictCache = FastDictCache(self.get_content, size=1_000)
        self._graphic_float_cache: FastDictCache = FastDictCache(
            self.get_graphic_float, size=1_000
        )

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
            convert(
                data=url.read_text(),
                from_=(format_ := get_format(url, default="html")),
                to="html",
                path=url,
            )
        )
        return HTML(
            markup=markup,
            base=url,
            mouse_handler=self._node_mouse_handler,
            paste_fixed=False,
            _initial_format=format_,
        )

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

    def get_lines(self, dom: HTML, width: int, height: int) -> list[StyleAndTextTuples]:
        """Render a HTML page as lines of formatted text."""
        app = get_app()

        lines = list(split_lines(dom.render(width, height)))

        # Check for graphics
        self.graphic_positions.clear()
        for y, line in enumerate(lines):
            x = 0
            for style, text, *_ in line:
                for token in style.split():
                    token = token[1:-1]
                    if token.startswith("Image_"):
                        self.graphic_positions[token] = (x, y)
                        # Get graphic float for this image and update its position
                        graphic_float = self._graphic_float_cache[dom, token]
                        # Register graphic with application
                        if graphic_float:
                            app.graphics.add(graphic_float)
                        break
                if "[ZeroWidthEscape]" not in style:
                    x += len(text)

        # Check for floating graphics and create graphics (do not position them yet)
        for line in split_lines(dom.fixed_mask):
            for style, *_ in line:
                for token in style.split():
                    token = token[1:-1]
                    if token.startswith("Image_"):
                        # Get graphic float for this image and update its position
                        graphic_float = self._graphic_float_cache[dom, token]
                        # Register graphic with application
                        if graphic_float:
                            app.graphics.add(graphic_float)

        return lines

    def load_url(self, url: str | Path, **kwargs: Any) -> None:
        """Load a new URL."""
        save_to_history = kwargs.get("save_to_history", True)
        # Trigger "loading" view
        self.loading = True
        # Clear graphics
        self.graphic_positions.clear()
        # Update navigation history
        if self.url and save_to_history:
            self.prev_stack.append(self.url)
            self.next_stack.clear()
        # Update url
        self.url = UPath(url)
        # Scroll to the top
        self.window.vertical_scroll = 0
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

    def render(self) -> None:
        """Render the HTML DOM in a thread."""

        def _render() -> None:
            assert self.url is not None
            # Potentially redirect url
            self.url = parse_path(self.url)
            self.lines = self._line_cache[self.dom, self.width, self.height]
            self.loading = False
            self.resizing = False
            self.rendering = False
            self.rendered.fire()

        if not self.rendering:
            self.rendering = True
            run_in_thread_with_context(_render)

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

    def get_graphic_float(self, dom: HTML, key: str) -> Float | None:
        """Create a graphical float for an image."""
        graphic_info = dom.graphic_info.get(key)
        if graphic_info is None:
            return None

        GraphicControl = select_graphic_control(format_=graphic_info["format_"])
        if GraphicControl is None:
            return None

        # TODO - cache this
        def get_position(screen: Screen) -> tuple[WritePosition, DiInt]:
            """Get the position and bbox of a graphic."""
            if key not in self.graphic_positions:
                raise NotVisible

            # Hide graphic if webview is not in layout
            if screen.visible_windows_to_write_positions.get(self.window) is None:
                raise NotVisible

            graphic_info = dom.graphic_info.get(key)
            if graphic_info is None:
                raise NotVisible

            render_info = self.window.render_info
            if render_info is None:
                raise NotVisible

            x, y = self.graphic_positions[key]

            content_width = max(0, graphic_info["cols"])
            horizontal_scroll = getattr(render_info, "horizontal_scroll", 0)

            if horizontal_scroll >= x + content_width:
                raise NotVisible

            content_height = max(0, graphic_info["rows"])
            vertical_scroll = render_info.vertical_scroll

            if vertical_scroll >= y + content_height:
                raise NotVisible

            x_offset = render_info._x_offset
            y_offset = render_info._y_offset

            xpos = max(x_offset, x - horizontal_scroll + x_offset)
            if xpos >= x_offset + render_info.window_width:
                raise NotVisible
            ypos = max(y_offset, y - vertical_scroll + y_offset)
            if ypos >= y_offset + render_info.window_height:
                raise NotVisible

            bbox = DiInt(
                top=max(0, render_info.vertical_scroll - y),
                right=0,  # TODO
                bottom=max(
                    0,
                    content_height
                    - render_info.window_height
                    - (render_info.vertical_scroll - y),
                ),
                left=0,  # TODO
            )
            if (width := content_width - bbox.left - bbox.right) < 1:
                raise NotVisible
            if (height := content_height - bbox.top - bbox.bottom) < 1:
                raise NotVisible

            write_position = BoundedWritePosition(
                xpos=xpos,
                ypos=ypos,
                width=width,
                height=height,
                bbox=bbox,
            )

            return write_position, bbox

        def _sizing_func() -> tuple[int, float]:
            graphic_info = dom.graphic_info[key]
            return (
                graphic_info["cols"],
                graphic_info["aspect"],
            )

        bg_color = graphic_info["bg"]
        graphic_float = Float(
            graphic_window := GraphicWindow(
                content=(
                    graphic_control := GraphicControl(
                        graphic_info["data"],
                        format_=graphic_info["format_"],
                        path=graphic_info["path"],
                        fg_color=graphic_info["fg"],
                        bg_color=graphic_info["bg"],
                        sizing_func=_sizing_func,
                    )
                ),
                position=get_position,
                style=f"bg:{bg_color}" if bg_color else "",
            ),
        )
        # Hide the graphic if the float is deleted
        weak_float_ref = weakref.ref(graphic_float)
        graphic_window.filter &= Condition(
            lambda: weak_float_ref() in get_app().graphics
        )
        # Hide the graphic if the float is deleted
        weakref.finalize(graphic_float, graphic_control.close)

        return graphic_float

    def get_content(
        self,
        url: Path,
        loading: bool,
        resizing: bool,
        width: int,
        # height: int,
        cursor_position: Point,
    ) -> UIContent:
        """Create a cacheable UIContent."""
        if self.loading:
            lines = [
                cast("StyleAndTextTuples", []),
                cast(
                    "StyleAndTextTuples",
                    [("", " " * ((width - 8) // 2)), ("class:loading", "Loading…")],
                ),
            ]
        else:
            lines = self.lines

        def get_line(i: int) -> StyleAndTextTuples:
            try:
                line = lines[i]
            except IndexError:
                return []

            # Overlay fixed lines onto this line
            if not loading:
                dom = self._dom_cache[url,]
                if dom.fixed:
                    visible_line = max(0, i - self.window.vertical_scroll)
                    fixed_lines = list(split_lines(dom.fixed_mask))
                    if visible_line < len(fixed_lines):
                        # Paste the fixed line over the current line
                        fixed_line = fixed_lines[visible_line]
                        line = paste(
                            fixed_lines[visible_line], line, 0, 0, transparent=True
                        )
                        # Update graphic positions on the fixed line
                        x = 0
                        for style, text, *_ in fixed_line:
                            for token in style.split():
                                token = token[1:-1]
                                if token.startswith("Image_"):
                                    self.graphic_positions[token] = (x, i)
                                    break
                            if "[ZeroWidthEscape]" not in style:
                                x += len(text)

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
        if self.loading:
            self.render()
        if width != self.width:  # or height != self.height:
            self.resizing = True
            self.width = width
            self.height = height
            self.render()

        return self._content_cache[
            self.url,
            self.loading,
            False,  # self.resizing,
            width,
            # height,
            self.cursor_position,
        ]

    def _node_mouse_handler(
        self, node: Node, mouse_event: MouseEvent
    ) -> NotImplementedOrNone:
        """Handle click events."""
        url = node.attrs.get("_link_path")
        title = node.attrs.get("title")
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
        if url or title:
            if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
                self.status.clear()
                if title:
                    self.status.append(str(title))
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
                # self.height,
                self.cursor_position,
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
            "euporie.web.widgets.webview.WebViewControl": {
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
