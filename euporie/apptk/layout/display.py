"""Define custom controls which re-render on resize."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from functools import lru_cache, partial
from math import ceil
from typing import TYPE_CHECKING, cast

from euporie.apptk.application.current import get_app
from euporie.apptk.filters.utils import to_filter
from euporie.apptk.key_binding.key_bindings import KeyBindings
from euporie.apptk.layout.dimension import Dimension, to_dimension
from euporie.apptk.utils import Event, to_str

from euporie.apptk.cache import FastDictCache, SimpleCache
from euporie.apptk.color import style_fg_bg
from euporie.apptk.commands import add_cmd, get_cmd
from euporie.apptk.convert.datum import Datum
from euporie.apptk.data_structures import Point, Size
from euporie.apptk.filters.app import display_has_focus, scrollable
from euporie.apptk.formatted_text.utils import fragment_list_width, split_lines, wrap
from euporie.apptk.layout.containers import (
    ConditionalContainer,
    Container,
    MarginContainer,
    VSplit,
    Window,
)
from euporie.apptk.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from euporie.apptk.layout.margins import ScrollbarMargin
from euporie.apptk.mouse_events import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import Any, ClassVar

    from euporie.apptk.key_binding.key_bindings import NotImplementedOrNone
    from euporie.apptk.layout.dimension import AnyDimension
    from euporie.apptk.layout.mouse_handlers import MouseHandlers

    from euporie.apptk.filters import FilterOrBool
    from euporie.apptk.formatted_text import StyleAndTextTuples
    from euporie.apptk.key_binding import KeyBindingsBase
    from euporie.apptk.layout.screen import Screen, WritePosition


log = logging.getLogger(__name__)


class FitMode(Enum):
    """Fitting mode for display content scaling.

    Controls how content is scaled relative to available space.
    """

    NONE = "none"  # Use natural size, may overflow
    SHRINK = "shrink"  # Scale down if too large, but never up
    GROW = "grow"  # Scale up if too small, but never down
    SCALE = "scale"  # Scale in either direction to fit


@lru_cache(maxsize=10240)
def calculate_render_size(
    natural: int | None,
    available: int,
    fit_mode: FitMode,
) -> int | None:
    """Calculate the size to request during conversion.

    Args:
        natural: The natural/intrinsic size of the content, or None if unknown.
        available: The available space.
        fit_mode: The fitting mode to apply.

    Returns:
        The size to use for conversion, or None if unconstrained.
    """
    if natural is None:
        # Unknown natural size, use available if fitting
        return available if fit_mode != FitMode.NONE else None

    match fit_mode:
        case FitMode.NONE:
            return None  # Don't constrain conversion
        case FitMode.SHRINK:
            return min(natural, available)
        case FitMode.GROW:
            return max(natural, available)
        case FitMode.SCALE:
            return available


class DisplayControl(UIControl):
    """Web view displays.

    A control which displays rendered graphical content.
    """

    def __init__(
        self,
        datum: Datum,
        style: str | Callable[[], str] = "",
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        fit_width: FitMode = FitMode.SHRINK,
        fit_height: FitMode = FitMode.NONE,
        expand_width: FilterOrBool = True,
        expand_height: FilterOrBool = False,
        threaded: bool = False,
        mouse_handler: Callable[[MouseEvent], NotImplementedOrNone] | None = None,
        convert_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Create a new web-view control instance.

        Args:
            datum: The data to display.
            style: Style string or callable returning style.
            focusable: Whether the control can receive focus.
            focus_on_click: Whether clicking focuses the control.
            wrap_lines: Whether to wrap long lines.
            fit_width: How to fit content horizontally.
            fit_height: How to fit content vertically.
            expand_width: Whether to pad content to fill available width.
            expand_height: Whether to pad content to fill available height.
            threaded: Whether to render in a background thread.
            mouse_handler: Optional mouse event handler.
            convert_kwargs: Additional arguments for datum conversion.
        """
        self._datum = datum
        self.style = style
        self.focusable = to_filter(focusable)
        self.focus_on_click = to_filter(focus_on_click)
        self.wrap_lines = to_filter(wrap_lines)
        self.fit_width = fit_width
        self.fit_height = fit_height
        self.expand_width = to_filter(expand_width)
        self.expand_height = to_filter(expand_height)
        self.threaded = threaded
        self.convert_kwargs = convert_kwargs or {}

        self._cursor_position = Point(0, 0)
        self.loading = False
        self.resizing = False
        self.rendering = False
        self.lines: list[StyleAndTextTuples] = []

        self.width: int | None = None
        self.height: int | None = None

        self._mouse_handler = mouse_handler

        self.rendered = Event(self)
        self.on_cursor_position_changed = Event(self)
        self.invalidate_events: list[Event[object]] = [
            self.rendered,
            self.on_cursor_position_changed,
        ]

        # Caches
        self._content_cache: FastDictCache = FastDictCache(self.get_content, size=1000)
        self._line_cache: FastDictCache[
            tuple[Datum, int | None, int | None, str, str, bool],
            list[StyleAndTextTuples],
        ] = FastDictCache(get_value=self.get_lines, size=1000)
        self._line_width_cache: SimpleCache[
            tuple[Datum, int | None, int | None, bool, int], int
        ] = SimpleCache(maxsize=10_000)
        self._max_line_width_cache: FastDictCache[
            tuple[Datum, int | None, int | None, bool], int
        ] = FastDictCache(get_value=self.get_max_line_width, size=1000)

    @property
    def datum(self) -> Datum:
        """Return the control's display data."""
        return self._datum

    @datum.setter
    def datum(self, value: Datum) -> None:
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

    def _calculate_render_dimensions(
        self, available_width: int, available_height: int | None
    ) -> tuple[int | None, int | None]:
        """Calculate the dimensions to use for rendering.

        Args:
            available_width: The available width in cells.
            available_height: The available height in cells, or None if unconstrained.

        Returns:
            Tuple of (render_width, render_height) to pass to conversion.
        """
        max_cols, aspect = self.datum.cell_size()
        natural_width = max_cols if max_cols else None
        natural_height = ceil(max_cols * aspect) if max_cols and aspect else None

        # Calculate render width
        render_width = calculate_render_size(
            natural_width, available_width, self.fit_width
        )

        # Calculate render height
        if available_height is not None:
            render_height = calculate_render_size(
                natural_height, available_height, self.fit_height
            )
        else:
            render_height = None

        # If we have aspect ratio and only one dimension, calculate the other
        _max_cols, aspect = self.datum.cell_size()
        if aspect and render_width is not None and render_height is None:
            render_height = ceil(render_width * aspect)
        elif aspect and render_height is not None and render_width is None:
            render_width = ceil(render_height / aspect) if aspect else None

        return render_width, render_height

    def get_lines(
        self,
        datum: Datum,
        width: int | None,
        height: int | None,
        fg: str,
        bg: str,
        wrap_lines: bool = False,
    ) -> list[StyleAndTextTuples]:
        """Render the lines to display in the control."""
        ft = datum.convert(
            to="ft",
            cols=width,
            rows=height,
            fg=fg,
            bg=bg,
            extend=self.expand_width(),
            # Use as extra cache key to force re-rendering when wrap_lines changes
            wrap_lines=wrap_lines,
            **self.convert_kwargs,
        )
        if width and height:
            key = Datum.add_size(datum, Size(height, width))
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
        # Ensure we have enough lines to fill the requested height if expanding
        if height is not None and self.expand_height():
            lines.extend([[]] * max(0, height - len(lines)))
        return lines

    @property
    def max_line_width(self) -> int:
        """Return the current maximum line width."""
        return self._max_line_width_cache[
            self.datum, self.width, self.height, self.wrap_lines()
        ]

    def get_max_line_width(
        self,
        datum: Datum,
        width: int | None,
        height: int | None,
        wrap_lines: bool = False,
    ) -> int:
        """Get the maximum lines width for a given rendering."""
        fg, bg = style_fg_bg(self.style)
        lines = self._line_cache[datum, width, height, fg, bg, wrap_lines]
        return max(
            self._line_width_cache.get(
                (datum, width, height, wrap_lines, i),
                partial(fragment_list_width, line),
            )
            for i, line in enumerate(lines)
        )

    def render(self, fg: str, bg: str) -> None:
        """Render the content in a thread."""
        datum = self.datum
        wrap_lines = self.wrap_lines()

        cols, rows = self._calculate_render_dimensions(self.width or 80, self.height)

        def _render() -> None:
            self.lines = self._line_cache[datum, cols, rows, fg, bg, wrap_lines]
            self.loading = False
            self.resizing = False
            self.rendering = False
            self.rendered.fire()

        if not self.rendering:
            self.rendering = True
            if self.threaded:
                get_app().create_background_task(asyncio.to_thread(_render))
            else:
                _render()

    def reset(self) -> None:
        """Reset the state of the control."""

    def preferred_width(self, max_available_width: int) -> int | None:
        """Calculate and return the preferred width of the control."""
        natural_width, _ = self.datum.cell_size()
        return (
            calculate_render_size(natural_width, max_available_width, self.fit_width)
            or max_available_width
        )

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Calculate and return the preferred height of the control."""
        # Calculate render dimensions
        render_width, render_height = self._calculate_render_dimensions(
            width, max_available_height
        )

        # Get actual lines to determine real height
        fg, bg = style_fg_bg(self.style)
        self.lines = self._line_cache[
            self.datum,
            render_width,
            render_height,
            fg,
            bg,
            self.wrap_lines(),
        ]

        content_height = len(self.lines)

        # Apply expand_height
        if self.expand_height():
            return max(content_height, max_available_height)
        return content_height

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
        fg: tuple[int, int, int],
        bg: tuple[int, int, int],
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
            A :py:class:`UIContent` instance.
        """
        # Trigger a re-render in the future if things have changed
        render = False
        if self.loading:
            render = True
        if width != self.width or height != self.height:
            self.resizing = True
            self.width = width
            self.height = height
            render = True
        fg, bg = style_fg_bg(self.style)
        if render:
            self.render(fg, bg)
        content = self._content_cache[
            self.datum, width, height, self.loading, self.cursor_position, fg, bg
        ]

        return content

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Mouse handler for this control."""
        result: NotImplementedOrNone = NotImplemented
        if (
            self.focus_on_click()
            and mouse_event.event_type == MouseEventType.MOUSE_DOWN
        ):
            get_app().layout.current_control = self
            result = None
        if callable(_mouse_handler := self._mouse_handler):
            return _mouse_handler(mouse_event)
        return result

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

    def get_invalidate_events(self) -> Iterable[Event[object]]:
        """Return the Window invalidate events."""
        yield from self.invalidate_events
        # Re-render control on terminal color change
        yield get_app().on_color_change


class Display(Container):
    """Rich output displays.

    A container for displaying rich output data.

    """

    commands = (
        "display-scroll-left",
        "display-scroll-right",
        "display-scroll-up",
        "display-scroll-down",
        "display-page-up",
        "display-page-down",
        "display-go-to-start",
        "display-go-to-end",
    )

    def __init__(
        self,
        datum: Datum,
        height: AnyDimension = None,
        width: AnyDimension = None,
        fit_width: FitMode = FitMode.SHRINK,
        fit_height: FitMode = FitMode.NONE,
        expand_width: FilterOrBool = True,
        expand_height: FilterOrBool = False,
        style: str | Callable[[], str] = "",
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        always_hide_cursor: FilterOrBool = True,
        scrollbar: FilterOrBool = True,
        scrollbar_autohide: FilterOrBool = True,
        mouse_handler: Callable[[MouseEvent], NotImplementedOrNone] | None = None,
        convert_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Instantiate an Output container object.

        Args:
            datum: Displayable data
            height: The height of the output in terminal cells
            width: The width of the output in terminal cells
            fit_width: How to fit content horizontally (NONE/SHRINK/GROW/SCALE)
            fit_height: How to fit content vertically (NONE/SHRINK/GROW/SCALE)
            expand_width: Whether to pad content to fill available width
            expand_height: Whether to pad content to fill available height
            style: The style to apply to the output
            focusable: If the output should be focusable
            focus_on_click: If the output should become focused when clicked
            wrap_lines: If the output's lines should be wrapped
            always_hide_cursor: When true, the cursor is never shown
            scrollbar: Whether to show a scrollbar
            scrollbar_autohide: Whether to automatically hide the scrollbar
            mouse_handler: Optional mouse handler for the display control
            convert_kwargs: Key-word arguments to pass to :py:method:`Datum.convert`

        """
        self._style = style
        self._width = width
        self._height = height
        self.fit_width = fit_width
        self.fit_height = fit_height
        self.expand_width = to_filter(expand_width)
        self.expand_height = to_filter(expand_height)

        self.control = DisplayControl(
            datum,
            style=self._get_style,
            focusable=focusable,
            focus_on_click=focus_on_click,
            wrap_lines=wrap_lines,
            fit_width=fit_width,
            fit_height=fit_height,
            expand_width=expand_width,
            expand_height=expand_height,
            mouse_handler=mouse_handler,
            convert_kwargs=convert_kwargs,
        )

        # Calculate dont_extend based on expand settings
        dont_extend_width = ~to_filter(expand_width)
        dont_extend_height = ~to_filter(expand_height)

        self.window = Window(
            content=self.control,
            height=height,
            width=width,
            wrap_lines=False,
            always_hide_cursor=always_hide_cursor,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            style=self._get_style,
            char=" ",
        )

        self._container = VSplit(
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

        # Store the parent style received during write_to_screen
        self._parent_style = ""

        # Key-bindings
        self.key_bindings = KeyBindings.from_commands(self.commands)

    def _get_style(self) -> str:
        """Get the combined style including parent style and background color."""
        style = to_str(self._style)
        # Include parent style so it's available to the control
        return f"{self._parent_style} {style}"

    @property
    def datum(self) -> Any:
        """Return the display's current data."""
        return self.control.datum

    @datum.setter
    def datum(self, value: Datum) -> None:
        """Set the display container's data."""
        self.control.datum = value

    def reset(self) -> None:
        """Reset the state of this container and all the children."""
        self._container.reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the preferred width for this container."""
        if self._width is not None:
            return to_dimension(self._width)

        # Delegate to control for preferred calculation
        preferred = self.control.preferred_width(max_available_width)

        # If expand_width, we want to fill available space
        if self.expand_width():
            return Dimension(min=1, preferred=preferred or max_available_width)
        else:
            # Don't extend beyond content
            return Dimension(
                min=1, preferred=preferred or 1, max=preferred or max_available_width
            )

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the preferred height for this container."""
        if self._height is not None:
            return to_dimension(self._height)

        # Delegate to container which will ask the control
        dim = self._container.preferred_height(width, max_available_height)

        # Adjust based on expand_height
        if self.expand_height():
            return Dimension(
                min=dim.min, preferred=max(dim.preferred, max_available_height)
            )
        return dim

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Write the container content to the screen.

        Args:
            screen: The screen to write to.
            mouse_handlers: The mouse handlers collection.
            write_position: The position and dimensions to write to.
            parent_style: Style string from the parent container.
            erase_bg: Whether to erase the background.
            z_index: The z-index for rendering.
        """
        # Store parent style so it can be used by _get_style
        self._parent_style = parent_style

        # Delegate to the internal container, passing through the parent_style
        self._container.write_to_screen(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
            z_index,
        )

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Return key bindings that are specific for this user control.

        Returns:
            A :class:`.KeyBindings` object if some key bindings are specified, or
                `None` otherwise.
        """
        return self.key_bindings

    def get_children(self) -> list[Container]:
        """Return the list of child containers."""
        return [self._container]

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(keys=["left"], filter=display_has_focus)
    def _display_scroll_left() -> None:
        """Scroll the display up one line."""
        window = get_app().layout.current_window
        window._scroll_left()

    @staticmethod
    @add_cmd(keys=["right"], filter=display_has_focus)
    def _display_scroll_right() -> None:
        """Scroll the display down one line."""
        window = get_app().layout.current_window
        window._scroll_right()

    @staticmethod
    @add_cmd(keys=["up", "k"], filter=display_has_focus)
    def _display_scroll_up() -> None:
        """Scroll the display up one line."""
        get_app().layout.current_window._scroll_up()

    @staticmethod
    @add_cmd(keys=["down", "j"], filter=display_has_focus)
    def _display_scroll_down() -> None:
        """Scroll the display down one line."""
        get_app().layout.current_window._scroll_down()

    @staticmethod
    @add_cmd(keys=["pageup"], filter=display_has_focus)
    def _display_page_up() -> None:
        """Scroll the display up one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_up()

    @staticmethod
    @add_cmd(keys=["pagedown"], filter=display_has_focus)
    def _display_page_down() -> None:
        """Scroll the display down one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_down()

    @staticmethod
    @add_cmd(keys=["home"], filter=display_has_focus)
    def _display_go_to_start() -> None:
        """Scroll the display to the top."""
        current_control = get_app().layout.current_control
        if isinstance(current_control, DisplayControl):
            current_control.cursor_position = Point(0, 0)

    @staticmethod
    @add_cmd(keys=["end"], filter=display_has_focus)
    def _display_go_to_end() -> None:
        """Scroll the display down one page."""
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
