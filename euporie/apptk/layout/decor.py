"""Decorative widgets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app
from euporie.apptk.layout.dimension import Dimension

from euporie.apptk.border import ThinLine
from euporie.apptk.cache import FastDictCache, SimpleCache
from euporie.apptk.color import Color
from euporie.apptk.filters import has_focus
from euporie.apptk.layout.containers import (
    Container,
    to_container,
)
from euporie.apptk.layout.screen import Char, Screen, WritePosition
from euporie.apptk.mouse_events import MouseEventType
from euporie.apptk.output.vt100 import ANSI_COLORS_TO_RGB, TERMINAL_COLORS_TO_RGB

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.key_binding.key_bindings import (
        NotImplementedOrNone,
    )
    from euporie.apptk.layout.mouse_handlers import MouseHandlers

    from euporie.apptk.color import ColorPalette
    from euporie.apptk.layout.containers import AnyContainer
    from euporie.apptk.mouse_events import MouseEvent

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
                :py:class:`euporie.apptk.box.grid` is used
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
            screen: The :class:`~euporie.apptk.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`euporie.apptk.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`euporie.apptk.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`euporie.apptk.layout.containers.HSplit` can use it to pass
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
        char: str | Callable[[], str],
        pattern: Callable[[int, int], bool],
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
            screen: The :class:`~euporie.apptk.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`euporie.apptk.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`euporie.apptk.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`euporie.apptk.layout.containers.HSplit` can use it to pass
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
    """A transparent container which makes the background darker."""

    _SHADOW_STYLE_CACHE = SimpleCache(maxsize=255)

    def __init__(self, amount: float = 0.5) -> None:
        """Create a new instance."""
        self.amount = amount

    @property
    def cp(self) -> ColorPalette:
        """Get the current app's current color palette."""
        return get_app().color_palette

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

                color = attrs.color
                if not color or color == "default":
                    fg = Color.from_rgb(*TERMINAL_COLORS_TO_RGB["fg"])
                elif color in ANSI_COLORS_TO_RGB:
                    fg = Color.from_rgb(*ANSI_COLORS_TO_RGB[color], name=color)
                else:
                    fg = Color(color)
                style += f" fg:{fg.darker(amount)}"

                bgcolor = attrs.bgcolor
                if not bgcolor or bgcolor == "default":
                    bg = Color.from_rgb(*TERMINAL_COLORS_TO_RGB["bg"])
                elif bgcolor in ANSI_COLORS_TO_RGB:
                    bg = Color.from_rgb(*ANSI_COLORS_TO_RGB[bgcolor], name=bgcolor)
                else:
                    bg = Color(bgcolor)
                style += f" bg:{bg.darker(amount)}"

                return style

            ypos = write_position.ypos
            xpos = write_position.xpos
            amount = self.amount
            for y in range(ypos, ypos + write_position.height):
                row = screen.data_buffer[y]
                for x in range(xpos, xpos + write_position.width):
                    char = row[x]
                    style = char.style

                    key = (
                        app.style,
                        app.style_transformation.invalidation_hash(),
                        amount,
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
