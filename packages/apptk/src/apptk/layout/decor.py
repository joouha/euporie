"""Decorative widgets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.border import ThinLine
from apptk.cache import FastDictCache, SimpleCache
from apptk.color import Color
from apptk.filters import has_focus
from apptk.layout.containers import (
    Container,
    Window,
    to_container,
)
from apptk.layout.dimension import AnyDimension, Dimension, to_dimension
from apptk.layout.screen import _CHAR_CACHE, Char, Screen, WritePosition
from apptk.mouse_events import MouseEventType
from apptk.output.vt100 import ANSI_COLORS_TO_RGB, TERMINAL_COLORS_TO_RGB
from apptk.utils import to_str

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.color import ColorPalette
    from apptk.key_binding.key_bindings import (
        NotImplementedOrNone,
    )
    from apptk.layout.containers import AnyContainer
    from apptk.layout.mouse_handlers import MouseHandlers
    from apptk.mouse_events import MouseEvent

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class Line(Container):
    """Draw a horizontal or vertical line."""

    def __init__(
        self,
        char: str | None = None,
        width: int | None = None,
        height: int | None = None,
        collapse: bool = False,
        style: str = "class:grid-line",
    ) -> None:
        """Initialize a grid line.

        Args:
            char: The character to draw. If unset, the relevant character from
                :py:class:`apptk.box.grid` is used
            width: The length of the line. If specified, the line will be horizontal
            height: The height of the line. If specified, the line will be vertical
            collapse: Whether to hide the line when there is not enough space
            style: Style to apply to the line

        Raises:
            ValueError: If both width and height are specified. A line must only have a
                single dimension.

        """
        if width and height:
            raise ValueError("Only one of `width` or `height` must be set")
        self.width = width
        self.height = height
        if char is None:
            char = ThinLine.grid.VERTICAL if width else ThinLine.grid.HORIZONTAL
        self.char = Char(char, style)
        self.collapse = collapse

    def reset(self) -> None:
        """Reset the state of the line. Does nothing."""

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the preferred width of the line."""
        return Dimension(min=int(not self.collapse), max=self.width)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the preferred height of the line."""
        return Dimension(min=int(not self.collapse), max=self.height)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw a continuous line in the ``write_position`` area.

        Args:
            screen: The :class:`~apptk.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`apptk.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`apptk.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`apptk.layout.containers.HSplit` can use it to pass
                their style down to the windows that they contain.
            z_index: Used for propagating z_index from parent to child.

        """
        ypos = write_position.ypos
        xpos = write_position.xpos

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + write_position.width):
                row[x] = self.char

    def get_children(self) -> list:
        """Return an empty list of the container's children."""
        return []


class Fill(Container):
    """Fill an area with a character.

    This is a lightweight replacement for a
    :class:`~apptk.layout.containers.Window` backed by a
    :class:`~apptk.layout.controls.DummyControl`, which is commonly used for
    padding and background fills. It reports the same dimensions as such a
    window but skips the control, render info and mouse handler machinery.
    """

    def __init__(
        self,
        char: str | Callable[[], str] | None = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        style: str = "",
    ) -> None:
        """Initialize the fill.

        Args:
            char: The character to fill the area with.
            width: The width dimension of the fill.
            height: The height dimension of the fill.
            style: Style to apply to the filled area.
        """
        self.char = char
        self.width = width
        self.height = height
        self.style = style

    def reset(self) -> None:
        """Reset the fill. Does nothing."""

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the preferred width of the fill."""
        return Window._merge_dimensions(to_dimension(self.width), lambda: None)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the preferred height of the fill."""
        return Window._merge_dimensions(to_dimension(self.height), lambda: None)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Fill the ``write_position`` area with the fill character and style."""
        wp = write_position
        if wp.width <= 0 or wp.height <= 0:
            return

        char = self.char() if callable(self.char) else self.char
        if erase_bg or char:
            char_obj = _CHAR_CACHE[char or " ", ""]
            for y in range(wp.ypos, wp.ypos + wp.height):
                row = screen.data_buffer[y]
                for x in range(wp.xpos, wp.xpos + wp.width):
                    row[x] = char_obj

        style = f"{parent_style} {to_str(self.style)}"
        screen.fill_area(wp, style=style, after=False)

    def get_children(self) -> list:
        """Return an empty list of the container's children."""
        return []


class Pattern(Container):
    """Fill an area with a repeating background pattern.

    Example pattern functions:

        >>> lambda x, y: False
        >>> lambda x, y: True
        >>> lambda x, y: (x + y) % 2 == 0
        >>> lambda x, y: (x + 2 * y) % 4 == 0
        >>> lambda x, y: (x + y) % 3 == 0
        >>> lambda x, y: ((x + y % 2 * 3) % 6) % 4 == 0
    """

    def __init__(
        self,
        char: str | Callable[[], str] = "·",
        pattern: Callable[[int, int], bool] = lambda x, y: (x + y) % 2 == 0,
        style: str = "class:pattern",
    ) -> None:
        """Initialize the :class:`Pattern`."""
        self.bg = Char(" ", style)
        self.char = char
        self.pattern = pattern
        self.style = style

    def reset(self) -> None:
        """Reset the pattern. Does nothing."""

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return an empty dimension (expand to available width)."""
        return Dimension()

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return an empty dimension (expand to available height)."""
        return Dimension()

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Fill the whole area of write_position with a pattern.

        Args:
            screen: The :class:`~apptk.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`apptk.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`apptk.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`apptk.layout.containers.HSplit` can use it to pass
                their style down to the windows that they contain.
            z_index: Used for propagating z_index from parent to child.

        """
        bg = self.bg
        pattern = self.pattern
        if callable(self.char):
            char = Char(self.char(), self.style)
        else:
            char = Char(self.char, self.style)

        ypos = write_position.ypos
        xpos = write_position.xpos

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + write_position.width):
                row[x] = char if pattern(x, y) else bg

    def get_children(self) -> list:
        """Return an empty list of the container's children."""
        return []


class Border(Container):
    """Draw a single-window border around a wrapped container.

    This replaces the common pattern of building a 3x3 grid of fill
    :class:`~apptk.layout.containers.Window` objects (eight decorative edge and
    corner windows plus the body) with a single container that paints all four
    edges and corners directly to the screen in one pass. This avoids the
    per-window overhead (render info, mouse handler ranges, body copies) for the
    purely decorative border cells.
    """

    def __init__(
        self,
        body: AnyContainer,
        grid: Callable[[], object],
        style: str | Callable[[], str] = "class:border",
        top: bool = True,
        right: bool = True,
        bottom: bool = True,
        left: bool = True,
        corner: AnyContainer | None = None,
    ) -> None:
        """Create a new border decoration.

        Args:
            body: The container to wrap and draw the border around.
            grid: A callable returning a grid style object exposing
                ``TOP_LEFT``, ``TOP_MID``, ``TOP_RIGHT``, ``MID_LEFT``,
                ``MID_RIGHT``, ``BOTTOM_LEFT``, ``BOTTOM_MID`` and
                ``BOTTOM_RIGHT`` border character attributes.
            style: The style (or a callable returning one) for the border cells.
            top: Whether to draw the top edge.
            right: Whether to draw the right edge.
            bottom: Whether to draw the bottom edge.
            left: Whether to draw the left edge.
            corner: An optional container to draw in the top-left corner instead
                of the ``TOP_LEFT`` border character. This can be used to make
                the corner focusable.
        """
        self.body = body
        self.grid = grid
        self.style = style
        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left
        self.corner = corner

    def reset(self) -> None:
        """Reset the wrapped container."""
        to_container(self.body).reset()
        if self.corner is not None:
            to_container(self.corner).reset()

    def _insets(self) -> tuple[int, int, int, int]:
        """Return the (top, right, bottom, left) border widths."""
        return (
            int(self.top),
            int(self.right),
            int(self.bottom),
            int(self.left),
        )

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the body's preferred width, expanded for the border."""
        _t, right, _b, left = self._insets()
        extra = left + right
        dim = to_container(self.body).preferred_width(
            max(max_available_width - extra, 0)
        )
        return Dimension(
            min=dim.min + extra,
            max=(dim.max + extra) if dim.max is not None else None,
            preferred=dim.preferred + extra,
        )

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the body's preferred height, expanded for the border."""
        top, right, bottom, left = self._insets()
        extra = top + bottom
        dim = to_container(self.body).preferred_height(
            max(width - left - right, 0), max(max_available_height - extra, 0)
        )
        return Dimension(
            min=dim.min + extra,
            max=(dim.max + extra) if dim.max is not None else None,
            preferred=dim.preferred + extra,
        )

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw the border and the wrapped body in a single pass."""
        top, right, bottom, left = self._insets()
        wp = write_position

        # Draw the body in the inset region.
        body_width = max(wp.width - left - right, 0)
        body_height = max(wp.height - top - bottom, 0)
        if body_width > 0 and body_height > 0:
            to_container(self.body).write_to_screen(
                screen,
                mouse_handlers,
                WritePosition(
                    xpos=wp.xpos + left,
                    ypos=wp.ypos + top,
                    width=body_width,
                    height=body_height,
                ),
                parent_style,
                erase_bg,
                z_index,
            )

        # Nothing to draw if the border is entirely disabled.
        if not (top or right or bottom or left):
            return

        grid = self.grid()
        style = self.style() if callable(self.style) else self.style
        style = f"{parent_style} {style}"

        data_buffer = screen.data_buffer
        x0 = wp.xpos
        y0 = wp.ypos
        x1 = wp.xpos + wp.width - 1
        y1 = wp.ypos + wp.height - 1

        def char(name: str) -> Char:
            return _CHAR_CACHE[getattr(grid, name), style]

        # Top and bottom edges (including corners).
        if top:
            row = data_buffer[y0]
            if left and self.corner is None:
                row[x0] = char("TOP_LEFT")
            if right:
                row[x1] = char("TOP_RIGHT")
            mid = char("TOP_MID")
            for x in range(x0 + left, x1 + (0 if right else 1)):
                row[x] = mid
        if bottom and y1 != y0:
            row = data_buffer[y1]
            if left:
                row[x0] = char("BOTTOM_LEFT")
            if right:
                row[x1] = char("BOTTOM_RIGHT")
            mid = char("BOTTOM_MID")
            for x in range(x0 + left, x1 + (0 if right else 1)):
                row[x] = mid

        # Left and right edges (excluding corners already drawn).
        y_start = y0 + top
        y_end = y1 + (0 if bottom else 1)
        if left:
            mid_left = char("MID_LEFT")
            for y in range(y_start, y_end):
                data_buffer[y][x0] = mid_left
        if right:
            mid_right = char("MID_RIGHT")
            for y in range(y_start, y_end):
                data_buffer[y][x1] = mid_right

        # Draw an optional focusable corner over the top-left border character.
        if self.corner is not None and top and left:
            to_container(self.corner).write_to_screen(
                screen,
                mouse_handlers,
                WritePosition(xpos=x0, ypos=y0, width=1, height=1),
                parent_style,
                erase_bg,
                z_index,
            )

    def get_children(self) -> list:
        """Return the wrapped body (and optional corner) containers."""
        children = [to_container(self.body)]
        if self.corner is not None:
            children.append(to_container(self.corner))
        return children


class FocusedStyle(Container):
    """Apply a style to child containers when focused or hovered."""

    def __init__(
        self,
        body: AnyContainer,
        style_focus: str | Callable[[], str] = "class:focused",
        style_hover: str | Callable[[], str] = "",
    ) -> None:
        """Create a new instance of the widget.

        Args:
            body: The container to act on
            style_focus: The style to apply when the body has focus
            style_hover: The style to apply when the body is hovered
        """
        self.body = body
        self.style_focus = style_focus
        self.style_hover = style_hover
        self.hover = False
        self.has_focus = has_focus(self.body)

    def reset(self) -> None:
        """Reset the wrapped container."""
        to_container(self.body).reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the wrapped container's preferred width."""
        return to_container(self.body).preferred_width(max_available_width)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the wrapped container's preferred height."""
        return to_container(self.body).preferred_height(width, max_available_height)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw the wrapped container with the additional style."""
        to_container(self.body).write_to_screen(
            screen,
            mouse_handlers,
            write_position,
            f"{parent_style} {self.get_style()}",
            erase_bg,
            z_index,
        )

        if self.style_hover:
            x_min = write_position.xpos
            x_max = x_min + write_position.width
            y_min = write_position.ypos
            y_max = y_min + write_position.height

            # Wrap mouse handlers to add "hover" class on hover
            def _wrap_mouse_handler(handler: Callable) -> MouseHandler:
                def wrapped_mouse_handler(
                    mouse_event: MouseEvent,
                ) -> NotImplementedOrNone:
                    result = handler(mouse_event)

                    if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
                        app = get_app()
                        if (
                            mouse_event.position.x,
                            mouse_event.position.y,
                        ) == app.mouse_position:
                            app.mouse_limits = write_position
                            self.hover = True
                        else:
                            app.mouse_limits = None
                            self.hover = False
                        result = None
                    return result

                return wrapped_mouse_handler

            mouse_handler_wrappers: FastDictCache[tuple[Callable], MouseHandler] = (
                FastDictCache(get_value=_wrap_mouse_handler)
            )
            for y in range(y_min, y_max):
                row = mouse_handlers.mouse_handlers[y]
                for x in range(x_min, x_max):
                    row[x] = mouse_handler_wrappers[(row[x],)]

    def get_style(self) -> str:
        """Determine the style to apply depending on the focus status."""
        style = ""
        if self.has_focus():
            style += (
                self.style_focus() if callable(self.style_focus) else self.style_focus
            )
        if self.hover:
            style += " " + (
                self.style_hover() if callable(self.style_hover) else self.style_hover
            )
        return style

    def get_children(self) -> list[Container]:
        """Return the list of child :class:`.Container` objects."""
        return [to_container(self.body)]


class DropShadow(Container):
    """A transparent container which shifts colors toward a target."""

    _SHADOW_STYLE_CACHE = SimpleCache(maxsize=255)

    def __init__(self, amount: float = 0.5, color: str | Color = "#000000") -> None:
        """Create a new instance.

        Args:
            amount: How far to shift colors toward the color color.
            color: The color to shift toward.
        """
        self.amount = amount
        self.color = color

    @property
    def cp(self) -> ColorPalette:
        """Get the current app's current color palette."""
        return get_app().color_palette

    @property
    def color(self) -> Color:
        """Shadow color."""
        return self._color

    @color.setter
    def color(self, value: str | Color) -> None:
        """Set color color."""
        self._color = Color(value)

    def reset(self) -> None:
        """Reset the wrapped container - here, do nothing."""

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return the wrapped container's preferred width."""
        return Dimension(weight=1)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the wrapped container's preferred height."""
        return Dimension(weight=1)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw the wrapped container with the additional style."""
        app = get_app()
        attr_cache = app.renderer._attrs_for_style
        if attr_cache is not None and self.amount:

            def _calculate_color(style: str) -> str:
                """Calculate a transformed style."""
                attrs = attr_cache[style]

                fgcolor = attrs.color
                if not fgcolor or fgcolor == "default":
                    fg = Color.from_rgb(*TERMINAL_COLORS_TO_RGB["fg"])
                elif fgcolor in ANSI_COLORS_TO_RGB:
                    fg = Color.from_rgb(*ANSI_COLORS_TO_RGB[fgcolor], name=fgcolor)
                else:
                    fg = Color(fgcolor)
                style += f" fg:{fg.towards(target, amount)}"

                bgcolor = attrs.bgcolor
                if not bgcolor or bgcolor == "default":
                    bg = Color.from_rgb(*TERMINAL_COLORS_TO_RGB["bg"])
                elif bgcolor in ANSI_COLORS_TO_RGB:
                    bg = Color.from_rgb(*ANSI_COLORS_TO_RGB[bgcolor], name=bgcolor)
                else:
                    bg = Color(bgcolor)
                style += f" bg:{bg.towards(target, amount)}"

                return style

            ypos = write_position.ypos
            xpos = write_position.xpos
            amount = self.amount
            target = self.color
            for y in range(ypos, ypos + write_position.height):
                row = screen.data_buffer[y]
                for x in range(xpos, xpos + write_position.width):
                    char = row[x]
                    style = char.style

                    key = (
                        app.style,
                        app.style_transformation.invalidation_hash(),
                        amount,
                        target,
                        style,
                    )
                    new_style = self._SHADOW_STYLE_CACHE.get(
                        key, lambda style=style: _calculate_color(style)
                    )
                    # We need to copy the char rather than just update the style, as the
                    # same char instance may be used in multiple positions on the screen
                    row[x] = Char(char=char.char, style=new_style)

    def get_children(self) -> list[Container]:
        """Return an empty list of child :class:`.Container` objects."""
        return []
