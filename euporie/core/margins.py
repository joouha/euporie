"""Contains margins."""

from __future__ import annotations

import asyncio
import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, cast

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.layout.containers import Container, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.margins import Margin
from prompt_toolkit.mouse_events import MouseButton, MouseEventType
from prompt_toolkit.mouse_events import MouseEvent as PtkMouseEvent

from euporie.core.current import get_app
from euporie.core.key_binding.bindings.mouse import MouseEvent, RelativePosition

if TYPE_CHECKING:
    from typing import Callable, Optional, Protocol

    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.layout.containers import WindowRenderInfo
    from prompt_toolkit.layout.controls import UIContent
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition

    class ScrollableContainer(Protocol):
        """Protocol for a scrollable container."""

        render_info: WindowRenderInfo
        vertical_scroll: int


log = logging.getLogger(__name__)


class ClickableMargin(Margin, metaclass=ABCMeta):
    """A margin sub-class which handles mouse events."""

    write_position: "Optional[WritePosition]"

    def set_write_position(self, write_position: "WritePosition") -> "None":
        """Set the write position of the menu."""
        self.write_position = write_position


class MarginContainer(Window):
    """A container which renders a stand-alone margin."""

    def __init__(self, margin: "Margin", target: "ScrollableContainer") -> "None":
        """Create a new instance."""
        self.margin = margin
        self.target = target
        self.render_info: "Optional[WindowRenderInfo]" = None
        self.content = FormattedTextControl(self.create_fragments)

    def create_fragments(self) -> "StyleAndTextTuples":
        """Generate text fragments to display."""
        return self.margin.create_margin(
            self.target.render_info,
            self.write_position.width,
            self.write_position.height,
        )

    def reset(self) -> "None":
        """Reset the state of this container and all the children."""

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Return a the desired width for this container."""
        width = self.margin.get_width(lambda: self.target.render_info.ui_content)
        return Dimension(min=width, max=width)

    def preferred_height(
        self, width: "int", max_available_height: "int"
    ) -> "Dimension":
        """Return a thedesired height for this container."""
        return Dimension()

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Write the actual content to the screen."""
        self.write_position = write_position
        if isinstance(self.margin, ClickableMargin):
            self.margin.set_write_position(write_position)

        margin_content: "UIContent" = self.content.create_content(
            write_position.width + 1, write_position.height
        )
        visible_line_to_row_col, rowcol_to_yx = self._copy_body(
            margin_content, screen, write_position, 0, write_position.width
        )

        # Set mouse handlers.
        def mouse_handler(mouse_event: PtkMouseEvent) -> "NotImplementedOrNone":
            """Turns screen coordinates into line coordinates."""
            # Don't handle mouse events outside of the current modal part of the UI
            if self not in get_app().layout.walk_through_modal_area():
                return NotImplemented

            # Find row/col position first.
            yx_to_rowcol = {v: k for k, v in rowcol_to_yx.items()}
            y = mouse_event.position.y
            x = mouse_event.position.x

            # If clicked below the content area, look for a position in the
            # last line instead
            max_y = write_position.ypos + len(visible_line_to_row_col) - 1
            y = min(max_y, y)
            result: "NotImplementedOrNone" = NotImplemented

            while x >= 0:
                try:
                    row, col = yx_to_rowcol[y, x]
                except KeyError:
                    # Try again. (When clicking on the right side of double
                    # width characters, or on the right side of the input.)
                    x -= 1
                else:
                    # Found position, call handler of UIControl.
                    if isinstance(mouse_event, MouseEvent):
                        cell_position = mouse_event.cell_position
                    else:
                        cell_position = RelativePosition(0.5, 0.5)
                    result = self.content.mouse_handler(
                        MouseEvent(
                            position=Point(x=col, y=row),
                            event_type=mouse_event.event_type,
                            button=mouse_event.button,
                            modifiers=mouse_event.modifiers,
                            cell_position=cell_position,
                        )
                    )
                    break

            return result

        mouse_handlers.set_mouse_handler_for_range(
            x_min=write_position.xpos,
            x_max=write_position.xpos + write_position.width,
            y_min=write_position.ypos,
            y_max=write_position.ypos + write_position.height,
            handler=mouse_handler,
        )

    def is_modal(self) -> "bool":
        """When this container is modal."""
        return False

    def get_key_bindings(self) -> "Optional[KeyBindingsBase]":
        """Returns a :class:`.KeyBindings` object."""
        return None

    def get_children(self) -> "list[Container]":
        """Return the list of child :class:`.Container` objects."""
        return []


class ScrollbarMargin(ClickableMargin):
    """Margin displaying a scrollbar.

    Args:
        display_arrows: Display scroll up/down arrows.
        up_arrow: Character to use for the scrollbar's up arrow
        down_arrow: Character to use for the scrollbar's down arrow
        smooth: Use block character to move scrollbar more smoothly

    """

    eighths = "█▇▆▅▄▃▂▁ "

    def __init__(
        self,
        display_arrows: "FilterOrBool" = True,
        up_arrow_symbol: "str" = "▴",
        down_arrow_symbol: "str" = "▾",
        autohide: "FilterOrBool" = True,
        smooth: "bool" = True,
        style: "str" = "",
    ) -> "None":
        """Creates a new scrollbar instance."""
        self.display_arrows = to_filter(display_arrows)
        self.up_arrow_symbol = up_arrow_symbol
        self.down_arrow_symbol = down_arrow_symbol
        self.smooth = smooth
        self.style = style

        self.repeat_task: "Optional[asyncio.Task[None]]" = None
        self.dragging = False
        self.drag_start_scroll = 0
        self.drag_start_offset = 0.0

        self.thumb_top = 0.0
        self.thumb_size = 0.0

        self.window_render_info: "Optional[WindowRenderInfo]" = None
        self.write_position: "Optional[WritePosition]" = None

    def get_width(self, get_ui_content: "Callable[[], UIContent]") -> "int":
        """Return the scrollbar width: always 1."""
        return 1

    def create_margin(
        self,
        window_render_info: "WindowRenderInfo",
        width: "int",
        height: "int",
        margin_render_info: "Optional[WindowRenderInfo]" = None,
    ) -> "StyleAndTextTuples":
        """Creates the margin's formatted text."""
        result: StyleAndTextTuples = []

        self.window_render_info = window_render_info
        self.margin_render_info = margin_render_info

        if not width:
            return result

        # Show we render the arrow buttons?
        display_arrows = self.display_arrows()

        # The height of the scrollbar, excluding the optional buttons
        self.track_height = window_render_info.window_height
        if display_arrows:
            self.track_height -= 2

        # Height of all text in the output: If there is none, we cannot divide
        # by zero so we hide the thumb
        content_height = window_render_info.content_height
        if content_height == 0 or content_height <= len(
            window_render_info.displayed_lines
        ):
            self.thumb_size = 0
        else:
            # The thumb is the part which moves, floating on the track: calculate its size
            fraction_visible = len(window_render_info.displayed_lines) / (
                content_height
            )
            self.thumb_size = (
                int(
                    min(self.track_height, max(1, self.track_height * fraction_visible))
                    * 8
                )
                / 8
            )
        if not self.smooth:
            self.thumb_size = int(self.thumb_size)

        # Calculate the position of the thumb
        if content_height <= len(window_render_info.displayed_lines):
            fraction_above = 0.0
        else:
            fraction_above = window_render_info.vertical_scroll / (
                content_height - len(window_render_info.displayed_lines)
            )
        self.thumb_top = max(
            0,
            min(
                self.track_height - self.thumb_size,
                (int((self.track_height - self.thumb_size) * fraction_above * 8) / 8),
            ),
        )
        if not self.smooth:
            self.thumb_top = int(self.thumb_top)

        # Determine which characters to use for the ends of the thumb
        thumb_top_char = self.eighths[int(self.thumb_top % 1 * 8)]
        thumb_bottom_char = self.eighths[
            int((self.thumb_top + self.thumb_size) % 1 * 8)
        ]

        # Calculate thumb dimensions
        show_thumb_top = (self.thumb_top % 1) != 0
        thumb_top_size = 1 - self.thumb_top % 1
        show_thumb_bottom = (self.thumb_top + self.thumb_size) % 1 != 0
        thumb_bottom_size = (self.thumb_top + self.thumb_size) % 1
        thumb_middle_size = int(
            self.thumb_size
            - show_thumb_top * thumb_top_size
            - show_thumb_bottom * thumb_bottom_size
        )
        rows_after_thumb = (
            self.track_height
            - int(self.thumb_top)
            - show_thumb_top
            - thumb_middle_size
            - show_thumb_bottom
        )

        # Construct the scrollbar

        mouse_handler = cast("Callable[[PtkMouseEvent], None]", self.mouse_handler)

        # Up button
        if display_arrows:
            result += [
                ("class:scrollbar.arrow", self.up_arrow_symbol, mouse_handler),
                ("class:scrollbar", "\n", mouse_handler),
            ]
        # Track above the thumb
        for _ in range(int(self.thumb_top)):
            result += [
                ("class:scrollbar.background", " ", mouse_handler),
                ("class:scrollbar", "\n", mouse_handler),
            ]
        # Top of thumb
        if show_thumb_top:
            result += [
                (
                    "class:scrollbar.background,scrollbar.start",
                    thumb_top_char,
                    mouse_handler,
                ),
                ("class:scrollbar", "\n", mouse_handler),
            ]
        # Middle of thumb
        for _ in range(thumb_middle_size):
            result += [
                ("class:scrollbar.button", " ", mouse_handler),
                ("class:scrollbar", "\n", mouse_handler),
            ]
        # Bottom of thumb
        if show_thumb_bottom:
            result += [
                (
                    "class:scrollbar.background,scrollbar.end",
                    thumb_bottom_char,
                    mouse_handler,
                ),
                ("class:scrollbar", "\n", mouse_handler),
            ]
        # Track below the thumb
        for _ in range(rows_after_thumb):
            result += [
                ("class:scrollbar.background", " ", mouse_handler),
                ("class:scrollbar", "\n", mouse_handler),
            ]
        # Down button
        if display_arrows:
            result += [
                ("class:scrollbar.arrow", self.down_arrow_symbol, mouse_handler),
            ]

        # if self.style:
        # result = [
        # (f"{self.style} {style}", text, *cb) for style, text, *cb in result
        # ]

        return result

    def _mouse_handler(
        self, mouse_event: "PtkMouseEvent", repeated: "bool" = False
    ) -> "NotImplementedOrNone":
        """Handle scrollbar mouse events.

        Scrolls up or down if the arrows are clicked, repeating while the mouse button
        is held down. Scolls up or down one page if the background is clicked,
        repeating while the left mouse button is held down. Scrolls if the
        scrollbar-button is dragged. Scrolls if the scroll-wheel is used on the
        scrollbar.

        Args:
            mouse_event: The triggering mouse event
            repeated: Set to True if the method is running as a repeated event

        Returns:
            :py:const:`NotImplemented` is eturned when the mouse event is unhandled;
            :py:const:`None` is returned when the mouse event is handled successfully

        """
        render_info = self.window_render_info
        assert render_info is not None

        content_height = render_info.content_height
        if isinstance(mouse_event, MouseEvent):
            cell_position = mouse_event.cell_position
        else:
            cell_position = RelativePosition(0.5, 0.5)
        row = mouse_event.position.y + cell_position.y

        # Handle scroll events on the scrollbar
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            render_info.window._scroll_up()
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            render_info.window._scroll_down()

        # Mouse drag events
        elif self.dragging and mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            # Add ½ so as to round to nearest integer
            target_scroll = int(
                (row - self.drag_start_offset) / self.track_height * content_height
                + 0.5
            )
            # Use the window's current vertical scroll as it may have changed since the
            # window_render_info was generated
            window = render_info.window
            delta = window.vertical_scroll - target_scroll

            if isinstance(window, Window):
                if delta < 0:
                    func = window._scroll_up
                else:
                    func = window._scroll_down
                for _ in range(abs(delta)):
                    func()
            elif hasattr(window, "scrolling"):
                render_info.window.scrolling = delta

        # Mouse down events
        elif mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            # Scroll up/down one line if clicking on the arrows
            arrows = self.display_arrows()
            if arrows and int(row) == 0:
                offset = -1
            elif arrows and int(row) == render_info.window_height - 1:
                offset = 1
            # Scroll up or down one page if clicking on the background
            elif row < self.thumb_top + 1 or self.thumb_top + 1 + self.thumb_size < row:
                direction = (row < (self.thumb_top + self.thumb_size // 2)) * -2 + 1
                offset = direction * render_info.window_height
            # We are on the scroll button - start a drag event if this is not a
            # repeated mouse event
            elif not repeated:
                self.dragging = True
                self.drag_start_scroll = render_info.vertical_scroll
                self.drag_start_offset = row - self.thumb_top
                # Restrict mouse events to this area
                get_app().mouse_limits = self.write_position
                return None
            # Otherwise this is a click on the centre scroll button - do nothing
            else:
                offset = 0

            if mouse_event.button == MouseButton.LEFT:
                func = None
                if offset < 0:
                    func = render_info.window._scroll_up
                elif offset > 0:
                    func = render_info.window._scroll_down
                if func is not None:
                    # Scroll the window multiple times to scroll by the offset
                    for _ in range(abs(int(offset))):
                        func()
                    # Trigger this mouse event to be repeated
                    self.repeat_task = get_app().create_background_task(
                        self.repeat(mouse_event)
                    )

        # Handle all other mouse events
        else:
            # Stop any repeated tasks
            if self.repeat_task is not None:
                self.repeat_task.cancel()
            # Cancel drags
            self.dragging = False
            get_app().mouse_limits = None
            return NotImplemented

        return None

    def mouse_handler(self, mouse_event: "PtkMouseEvent") -> "NotImplementedOrNone":
        """Type compatible mouse handler."""
        return self._mouse_handler(mouse_event, repeated=False)

    async def repeat(
        self, mouse_event: "PtkMouseEvent", timeout: "float" = 0.1
    ) -> "None":
        """Repeat a mouse event after a timeout."""
        await asyncio.sleep(timeout)
        self._mouse_handler(mouse_event, repeated=True)
        get_app().invalidate()


class NumberedDiffMargin(Margin):
    """Margin that displays the line numbers of a :class:`Window`."""

    style = "class:line-number"

    def get_width(self, get_ui_content: "Callable[[], UIContent]") -> "int":
        """Return the width of the margin."""
        line_count = get_ui_content().line_count
        return len("%s" % line_count) + 2

    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: "int", height: "int"
    ) -> "StyleAndTextTuples":
        """Generate the margin's content."""
        # Get current line number.
        current_lineno = window_render_info.ui_content.cursor_position.y
        # Construct margin.
        result: StyleAndTextTuples = []
        last_lineno = None
        for lineno in window_render_info.displayed_lines:
            # Only display line number if this line is not a continuation of the previous line.
            if lineno != last_lineno:
                if lineno is None:
                    pass
                linestr = str(lineno + 1).rjust(width - 2)
                style = self.style
                if lineno == current_lineno and get_app().layout.has_focus(
                    window_render_info.window
                ):
                    style = f"{style} class:line-number.current"
                result.extend(
                    [
                        (f"{style},edge", "▏"),
                        (style, linestr),
                        (f"{style},edge", "▕"),
                    ]
                )
            last_lineno = lineno
            result.append(("", "\n"))
        return result


class OverflowMargin(Margin):
    """A margin which indicates lines extending beyond the edge of the window."""

    def get_width(self, get_ui_content: "Callable[[], UIContent]") -> "int":
        """Return the width of the margin."""
        return 1

    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: "int", height: "int"
    ) -> "StyleAndTextTuples":
        """Generate the margin's content."""
        from prompt_toolkit.formatted_text.utils import fragment_list_width

        result: "StyleAndTextTuples" = []

        for lineno in window_render_info.displayed_lines:
            line = window_render_info.ui_content.get_line(lineno)
            if (
                fragment_list_width(line) - window_render_info.window.horizontal_scroll
                > window_render_info.window_width + 1
            ):
                result.append(("class:input,overflow", "▹"))
            result.append(("", "\n"))

        return result
