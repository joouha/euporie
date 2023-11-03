"""Decorative widgets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.filters import has_focus, to_filter
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    to_container,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.mouse_events import MouseEventType

from euporie.core.border import ThinLine
from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.data_structures import DiBool
from euporie.core.style import ColorPaletteColor

if TYPE_CHECKING:
    from typing import Callable

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.border import GridStyle
    from euporie.core.style import ColorPalette

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
                :py:class:`euporie.core.box.grid` is used
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
        """Reet the state of the line. Does nothing."""

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
            screen: The :class:`~prompt_toolkit.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`prompt_toolkit.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`prompt_toolkit.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`prompt_toolkit.layout.containers.HSplit` can use it to pass
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
    """Fill an area with a repeating background pattern."""

    def __init__(
        self,
        char: str | Callable[[], str],
        pattern: int | Callable[[], int] = 1,
    ) -> None:
        """Initialize the :class:`Pattern`."""
        self.bg = Char(" ", "class:pattern")
        self.char = char
        self.pattern = pattern

    def reset(self) -> None:
        """Reet the pattern. Does nothing."""

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
            screen: The :class:`~prompt_toolkit.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`prompt_toolkit.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`prompt_toolkit.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`prompt_toolkit.layout.containers.HSplit` can use it to pass
                their style down to the windows that they contain.
            z_index: Used for propagating z_index from parent to child.

        """
        bg = self.bg
        pattern = self.pattern() if callable(self.pattern) else self.pattern
        if callable(self.char):
            char = Char(self.char(), "class:pattern")
        else:
            char = Char(self.char, "class:pattern")

        ypos = write_position.ypos
        xpos = write_position.xpos

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + write_position.width):
                if (
                    (pattern == 1)
                    or (pattern == 2 and (x + y) % 2 == 0)
                    or (pattern == 3 and (x + 2 * y) % 4 == 0)
                    or (pattern == 4 and (x + y) % 3 == 0)
                    or (pattern == 5 and ((x + y % 2 * 3) % 6) % 4 == 0)
                ):
                    row[x] = char
                else:
                    row[x] = bg

    def get_children(self) -> list:
        """Return an empty list of the container's children."""
        return []


class Border:
    """Draw a border around any container."""

    def __init__(
        self,
        body: AnyContainer,
        border: GridStyle | None = ThinLine.grid,
        style: str | Callable[[], str] = "class:border",
        show_borders: DiBool | None = None,
    ) -> None:
        """Create a new border widget which wraps another container.

        Args:
            body: The container to surround with a border
            border: The grid style to use
            style: The style to apply to the border
            show_borders: Which of the four borders should be displayed

        """
        self.body = body
        self.style = style

        if show_borders:
            show_borders = DiBool(*show_borders)
        else:
            show_borders = DiBool(True, True, True, True)
        border_top = to_filter(show_borders.top)
        border_right = to_filter(show_borders.right)
        border_bottom = to_filter(show_borders.bottom)
        border_left = to_filter(show_borders.left)

        self.container: AnyContainer
        if border is not None and any(show_borders):
            self.container = HSplit(
                [
                    ConditionalContainer(
                        VSplit(
                            [
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.TOP_LEFT,
                                        style=self.add_style("class:left,top"),
                                    ),
                                    filter=border_top & border_left,
                                ),
                                ConditionalContainer(
                                    Window(
                                        char=border.TOP_MID,
                                        style=self.add_style("class:top"),
                                    ),
                                    filter=border_top,
                                ),
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.TOP_RIGHT,
                                        style=self.add_style("class:right,top"),
                                    ),
                                    filter=border_top & border_right,
                                ),
                            ],
                            height=1,
                        ),
                        filter=border_top,
                    ),
                    VSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_LEFT,
                                    style=self.add_style("class:left"),
                                ),
                                filter=border_left,
                            ),
                            DynamicContainer(lambda: self.body),
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_RIGHT,
                                    style=self.add_style("class:right"),
                                ),
                                filter=border_right,
                            ),
                            # Padding is required to make sure that if the content is
                            # too small, the right frame border is still aligned.
                        ],
                        padding=0,
                    ),
                    ConditionalContainer(
                        VSplit(
                            [
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.BOTTOM_LEFT,
                                        style=self.add_style("class:left,bottom"),
                                    ),
                                    filter=border_bottom & border_left,
                                ),
                                ConditionalContainer(
                                    Window(
                                        char=border.BOTTOM_MID,
                                        style=self.add_style("class:bottom"),
                                    ),
                                    filter=border_bottom,
                                ),
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.BOTTOM_RIGHT,
                                        style=self.add_style("class:right,bottom"),
                                    ),
                                    filter=border_bottom & border_right,
                                ),
                            ],
                            # specifying height here will increase the rendering speed.
                            height=1,
                        ),
                        filter=border_bottom,
                    ),
                ],
            )
        else:
            self.container = body

    def add_style(self, extra: str) -> Callable[[], str]:
        """Return a function which adds a style string to the border style."""

        def _style() -> str:
            if callable(self.style):
                return f"{self.style()} {extra}"
            else:
                return f"{self.style} {extra}"

        return _style

    def __pt_container__(self) -> AnyContainer:
        """Return the border widget's container."""
        return self.container


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
        """Reet the wrapped container."""
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

            mouse_handler_wrappers: FastDictCache[
                tuple[Callable], MouseHandler
            ] = FastDictCache(get_value=_wrap_mouse_handler)
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

    def __init__(self, amount: float = 0.5) -> None:
        """Create a new instance."""
        self.amount = amount
        self.renderer = get_app().renderer

    @property
    def cp(self) -> ColorPalette:
        """Get the current app's current color palette."""
        return get_app().color_palette

    def reset(self) -> None:
        """Reet the wrapped container - here, do nothing."""

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
        attr_cache = self.renderer._attrs_for_style
        if attr_cache is not None:
            ypos = write_position.ypos
            xpos = write_position.xpos
            amount = self.amount
            for y in range(ypos, ypos + write_position.height):
                row = screen.data_buffer[y]
                for x in range(xpos, xpos + write_position.width):
                    char = row[x]
                    style = char.style
                    attrs = attr_cache[style]

                    if not (fg := attrs.color) or fg == "default":
                        color = self.cp.fg
                        style += f" fg:{color.darker(amount)}"
                    else:
                        try:
                            color = ColorPaletteColor(fg)
                        except ValueError:
                            pass
                        else:
                            style += f" fg:{color.darker(amount)}"

                    if not (bg := attrs.bgcolor) or bg == "default":
                        color = self.cp.bg
                        style += f" bg:{color.darker(amount)}"
                    else:
                        try:
                            color = ColorPaletteColor(bg)
                        except ValueError:
                            pass
                        else:
                            style += f" bg:{color.darker(amount)}"

                    row[x] = Char(char=char.char, style=style)

    def get_children(self) -> list[Container]:
        """Return an empty list of child :class:`.Container` objects."""
        return []


class Shadow:
    """Draw a shadow underneath/behind this container.

    This is a globally configurable version of the
    :py:class:`prompt_toolkit.widows.base.Shadow` class.
    """

    def __init__(self, body: AnyContainer) -> None:
        """Initialize a new drop-shadow container.

        Args:
            body: Another container object.
        """
        filter_ = get_app().config.filter("show_shadows")
        shadow = FloatContainer(
            content=body,
            floats=[
                Float(
                    bottom=-1,
                    height=1,
                    left=1,
                    right=0,
                    transparent=True,
                    content=DropShadow(),
                ),
                Float(
                    bottom=-1,
                    top=1,
                    width=1,
                    right=-1,
                    transparent=True,
                    content=DropShadow(),
                ),
            ],
        )

        def get_contents() -> AnyContainer:
            if filter_():
                return shadow
            else:
                return body

        self.container = DynamicContainer(get_contents)

    def __pt_container__(self) -> AnyContainer:
        """Return the container's content."""
        return self.container

    # ################################### Settings ####################################

    add_setting(
        name="show_shadows",
        flags=["--show-shadows"],
        type_=bool,
        help_="Show or hide shadows under menus and dialogs",
        default=True,
        description="""
            Sets whether shadows are shown under dialogs and popup-menus.
        """,
    )
