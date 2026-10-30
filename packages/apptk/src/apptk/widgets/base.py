"""Extended widget components for building full screen applications.

This module provides enhanced versions of prompt_toolkit widgets with additional
functionality such as custom border styles and selective border visibility.

All of these widgets implement the ``__pt_container__`` method, which makes
them usable in any situation where we are expecting a `prompt_toolkit`
container object.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apptk.border import ThinGrid, ThinLine
from apptk.data_structures import DiStr
from apptk.filters import to_filter
from apptk.formatted_text.base import to_formatted_text
from apptk.layout.containers import (
    Container,
    DummyContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    to_container,
)
from apptk.layout.decor import DropShadow
from apptk.layout.dimension import Dimension
from apptk.layout.screen import _CHAR_CACHE, Screen, WritePosition
from apptk.utils import get_cwidth
from prompt_toolkit.widgets.base import Frame as PtkFrame
from prompt_toolkit.widgets.base import Shadow as PtkShadow

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.border import GridStyle
    from apptk.filters.core import FilterOrBool
    from apptk.layout.containers import AnyContainer
    from apptk.layout.mouse_handlers import MouseHandlers
    from apptk.mouse_events import MouseEvent
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.key_binding.key_bindings import KeyBindings
    from prompt_toolkit.layout.dimension import AnyDimension

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)

# Override prompt_toolkit's `Border` class with a backwards compatible grid instance
# from the new :py:mod:`apptk.border` system
Border = ThinGrid


class _FrameContainer(Container):
    """Draw a frame border and an optional title around a body in one pass.

    This replaces the 3x3 grid of border :class:`~apptk.layout.containers.Window`
    objects used by :class:`~prompt_toolkit.widgets.base.Frame` (eight
    decorative edge and corner windows) with a single container which paints
    the border and title directly to the screen.
    """

    def __init__(self, frame: Frame, grid: GridStyle) -> None:
        """Wrap the body of ``frame`` and draw its border using ``grid``."""
        self.frame = frame
        self.grid = grid

    def reset(self) -> None:
        """Reset the wrapped container."""
        to_container(self.frame.body).reset()

    def _visible_edges(self) -> tuple[bool, bool, bool, bool]:
        """Return whether the (top, right, bottom, left) edges are visible."""
        frame = self.frame
        return (
            frame.sb_top(),
            frame.sb_right(),
            frame.sb_bottom(),
            frame.sb_left(),
        )

    def _title_fragments(self) -> list[tuple[str, str]]:
        """Return the frame title as a list of style, text tuples."""
        title = self.frame.title
        if not title:
            return []
        if callable(title):
            title = title()
        return [(fragment[0], fragment[1]) for fragment in to_formatted_text(title)]

    @staticmethod
    def _fragments_width(fragments: list[tuple[str, str]]) -> int:
        """Return the display width of a list of formatted text fragments."""
        return sum(get_cwidth(text) for _style, text in fragments)

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the body's preferred width, expanded for the border."""
        top, right, _bottom, left = self._visible_edges()
        extra = int(right) + int(left)
        dim = to_container(self.frame.body).preferred_width(
            max(max_available_width - extra, 0)
        )
        preferred = dim.preferred + extra
        maximum = dim.max + extra
        # The title, when shown in the top edge, can be wider than the body.
        if top:
            title_width = self._fragments_width(self._title_fragments())
            preferred = max(preferred, title_width)
            maximum = max(maximum, title_width)
        return Dimension(min=dim.min + extra, max=maximum, preferred=preferred)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the body's preferred height, expanded for the border."""
        top, right, bottom, left = self._visible_edges()
        extra = int(top) + int(bottom)
        dim = to_container(self.frame.body).preferred_height(
            max(width - int(left) - int(right), 0),
            max(max_available_height - extra, 0),
        )
        return Dimension(
            min=dim.min + extra,
            max=dim.max + extra,
            preferred=dim.preferred + extra,
        )

    def _draw_title(
        self,
        row: list,
        xpos: int,
        width: int,
        style: str,
        fragments: list[tuple[str, str]],
    ) -> None:
        """Draw the title (centered) in a border row."""
        title_width = self._fragments_width(fragments)
        padding = 1 if title_width + 2 <= width else 0
        remaining = max(width - title_width - 2 * padding, 0)
        left_fill = (remaining + 1) // 2
        x = xpos + left_fill + padding
        end = xpos + width

        # Leave a single blank cell either side of the title, like the
        # original frame layout did with its collapsible padding windows.
        if padding:
            blank = _CHAR_CACHE[" ", style]
            row[xpos + left_fill] = blank
            if x + title_width < end:
                row[x + title_width] = blank

        for fragment_style, text in fragments:
            full_style = f"{style} {fragment_style}".strip()
            for char in text:
                char_width = get_cwidth(char)
                if char_width == 0:
                    continue
                if x + char_width > end:
                    return
                row[x] = _CHAR_CACHE[char, full_style]
                if char_width > 1:
                    row[x + 1] = _CHAR_CACHE["", full_style]
                x += char_width

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw the border, title and wrapped body in a single pass."""
        wp = write_position
        if wp.width <= 0 or wp.height <= 0:
            return

        top, right, bottom, left = self._visible_edges()

        # Draw the body in the inset region.
        body_width = max(wp.width - int(left) - int(right), 0)
        body_height = max(wp.height - int(top) - int(bottom), 0)
        if body_width > 0 and body_height > 0:
            to_container(self.frame.body).write_to_screen(
                screen,
                mouse_handlers,
                WritePosition(
                    xpos=wp.xpos + int(left),
                    ypos=wp.ypos + int(top),
                    width=body_width,
                    height=body_height,
                ),
                parent_style,
                erase_bg,
                z_index,
            )

        if not (top or right or bottom or left):
            return

        frame = self.frame
        grid = self.grid
        data_buffer = screen.data_buffer
        x0 = wp.xpos
        y0 = wp.ypos
        x1 = wp.xpos + wp.width - 1
        y1 = wp.ypos + wp.height - 1

        style_top = f"{parent_style} {frame.add_styles(frame.bs_top)()}"
        style_right = f"{parent_style} {frame.add_styles(frame.bs_right)()}"
        style_bottom = f"{parent_style} {frame.add_styles(frame.bs_bottom)()}"
        style_left = f"{parent_style} {frame.add_styles(frame.bs_left)()}"

        if top:
            row = data_buffer[y0]
            if left:
                row[x0] = _CHAR_CACHE[
                    grid.TOP_LEFT,
                    f"{parent_style} {frame.add_styles(frame.bs_top, frame.bs_left)()}",
                ]
            if right:
                row[x1] = _CHAR_CACHE[
                    grid.TOP_RIGHT,
                    f"{parent_style} {frame.add_styles(frame.bs_top, frame.bs_right)()}",
                ]
            mid = _CHAR_CACHE[grid.TOP_MID, style_top]
            for x in range(x0 + int(left), x1 - int(right) + 1):
                row[x] = mid
            title = self._title_fragments()
            if title:
                self._draw_title(
                    row,
                    x0 + int(left),
                    wp.width - int(left) - int(right),
                    parent_style,
                    title,
                )

        if bottom and y1 != y0:
            row = data_buffer[y1]
            if left:
                row[x0] = _CHAR_CACHE[
                    grid.BOTTOM_LEFT,
                    f"{parent_style} {frame.add_styles(frame.bs_bottom, frame.bs_left)()}",
                ]
            if right:
                row[x1] = _CHAR_CACHE[
                    grid.BOTTOM_RIGHT,
                    f"{parent_style} {frame.add_styles(frame.bs_bottom, frame.bs_right)()}",
                ]
            mid = _CHAR_CACHE[grid.BOTTOM_MID, style_bottom]
            for x in range(x0 + int(left), x1 - int(right) + 1):
                row[x] = mid

        y_start = y0 + int(top)
        y_end = y1 + (0 if bottom else 1)
        if left:
            mid_left = _CHAR_CACHE[grid.MID_LEFT, style_left]
            for y in range(y_start, y_end):
                data_buffer[y][x0] = mid_left
        if right:
            mid_right = _CHAR_CACHE[grid.MID_RIGHT, style_right]
            for y in range(y_start, y_end):
                data_buffer[y][x1] = mid_right

    def get_children(self) -> list:
        """Return the wrapped body container."""
        return [to_container(self.frame.body)]


class Frame(PtkFrame):
    """Draw a border around any container, optionally with a title text.

    Extends the prompt_toolkit Frame with support for custom border styles
    and selective border visibility.

    Args:
        body: Another container object.
        title: Text to be displayed in the top of the frame (can be formatted text).
        style: Style string to be applied to this widget.
        border_style: Style string to be applied to the border elements.
        width: Width of the frame.
        height: Height of the frame.
        key_bindings: Optional key bindings.
        modal: Whether the frame is modal.
        border: The grid style to use for the border.
        show_borders: Which of the four borders should be displayed (top, right, bottom, left).
    """

    def __init__(
        self,
        body: AnyContainer,
        title: AnyFormattedText = "",
        style: str | Callable[[], str] = "class:frame",
        width: AnyDimension = None,
        height: AnyDimension = None,
        key_bindings: KeyBindings | None = None,
        modal: bool = False,
        border: GridStyle | None = ThinLine.grid,
        border_style: str
        | Callable[[], str]
        | tuple[
            str | Callable[[], str],
            str | Callable[[], str],
            str | Callable[[], str],
            str | Callable[[], str],
        ]
        | None = None,
        show_borders: FilterOrBool
        | tuple[FilterOrBool, FilterOrBool, FilterOrBool, FilterOrBool]
        | None = None,
    ) -> None:
        """Initialize the Frame widget."""
        self.body = body
        self.title = title
        self.style = style

        # Handle show_borders parameter
        if show_borders is None:
            show_borders = True
        if not isinstance(show_borders, tuple):
            show_borders = (show_borders, show_borders, show_borders, show_borders)
        sb_top = to_filter(show_borders[0])
        sb_right = to_filter(show_borders[1])
        sb_bottom = to_filter(show_borders[2])
        sb_left = to_filter(show_borders[3])

        # Handle border style parameter
        if border_style is None:
            border_style = DiStr(
                "class:border,top",
                "class:border,right",
                "class:border,bottom",
                "class:border,left",
            )
        if not isinstance(border_style, tuple):
            border_style = (border_style, border_style, border_style, border_style)
        bs_top = border_style[0]
        bs_right = border_style[1]
        bs_bottom = border_style[2]
        bs_left = border_style[3]

        self.sb_top = sb_top
        self.sb_right = sb_right
        self.sb_bottom = sb_bottom
        self.sb_left = sb_left
        self.bs_top = bs_top
        self.bs_right = bs_right
        self.bs_bottom = bs_bottom
        self.bs_left = bs_left

        self.container: AnyContainer
        if border is not None and any(show_borders):
            self.container = HSplit(
                [_FrameContainer(self, border)],
                width=width,
                height=height,
                key_bindings=key_bindings,
                modal=modal,
            )
        else:
            self.container = body

    def add_styles(self, *styles: str | Callable[[], str]) -> Callable[[], str]:
        """Return a function which adds a style string to the border style."""
        return lambda: " ".join(
            style() if callable(style) else style for style in [self.style, *styles]
        )


class Shadow(PtkShadow):
    """Draw a shadow underneath/behind this container.

    The container must be in a float.
    """

    def __init__(self, body: AnyContainer, filter: FilterOrBool = True) -> None:
        """Initialize a new drop-shadow container.

        Args:
            body: Another container object.
            filter: Determines if the shadow should be applied
        """
        filter = to_filter(filter)

        spacer = DummyContainer(width=1, height=1)
        shadow = VSplit(
            [
                HSplit([body, VSplit([spacer, DropShadow()])]),
                HSplit([spacer, DropShadow()]),
            ]
        )

        def get_contents() -> AnyContainer:
            if filter():
                return shadow
            else:
                return body

        self.container = DynamicContainer(get_contents)
