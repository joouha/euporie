"""Contains the terminal graphics display system."""

import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from prompt_toolkit.filters import to_filter
from prompt_toolkit.utils import Event

if TYPE_CHECKING:
    from typing import Any, MutableMapping, Optional, Type

    from prompt_toolkit.application import Application
    from prompt_toolkit.filters import FilterOrBool

__all__ = ["TerminalGraphicsRenderer", "TerminalGraphic"]

log = logging.getLogger(__name__)


class TerminalGraphicsRenderer:
    """Defines a terminal graphics display manager."""

    def __init__(
        self,
        graphic_class: "Optional[Type[TerminalGraphic]]" = None,
    ):
        """Creates a terinal graphics display manager."""
        self.graphics: "MutableMapping[int, TerminalGraphic]" = {}
        self.graphic_class = graphic_class
        self.next_id = 1
        self.hide_all = False

    def before_render(self, app: "Application[Any]") -> "None":
        """Hide graphics as necessary before rendering the display."""
        if self.graphic_class:
            for graphic in self.graphics.values():
                visible = graphic.visible()
                if not visible or self.hide_all:
                    graphic._hide(app)

    def after_render(self, app: "Application[Any]") -> "None":
        """Display or hide graphics as necessary after rendering the display."""
        if self.graphic_class and not self.hide_all:
            for graphic in self.graphics.values():
                if not self.hide_all and graphic.visible() and graphic.redraw:
                    graphic._draw(app)
                else:
                    graphic._hide(app)

    def add(
        self,
        data: "str",
        visible: "FilterOrBool" = False,
        bg_color: "Optional[str]" = None,
    ) -> "Optional[TerminalGraphic]":
        """Method used to register a new terminal graphic."""
        if self.graphic_class:
            data = "".join(data.split("\n"))
            graphic = self.graphic_class(self.next_id, data, visible, bg_color)
            self.next_id += 1
            self.graphics[graphic.id] = graphic
            return graphic
        return None

    def remove(self, id_: "int") -> "None":
        """Removes a terminal graphic by it ID."""
        if self.graphic_class:
            if graphic := self.graphics.get(id_):
                graphic.delete()
                del self.graphics[id_]


class TerminalGraphic(metaclass=ABCMeta):
    """Defines a base class for terminal graphics."""

    def __init__(
        self,
        id: "int",
        data: "str",
        visible: "FilterOrBool" = False,
        bg_color: "Optional[str]" = None,
    ) -> "None":
        """Creates a new terminal graphic."""
        self.id = id
        self.data = data[:]
        self._visible = to_filter(visible)
        self.last_visible_value = self._visible()
        self.bg_color = bg_color

        self.xpos = 0
        self.ypos = 0
        self.width = 0
        self.height = 0
        self.redraw = False

        self.on_move = Event(self, None)
        self.on_resize = Event(self, None)

    def visible(self) -> "bool":
        """Determines if the terminal graphic should be visible."""
        visible_value = self._visible()
        if self.last_visible_value != visible_value:
            self.redraw = True
        self.last_visible_value = visible_value
        return self.last_visible_value

    def load(self) -> "None":
        """Loads or renders the graphic."""
        ...

    def _draw(self, app: "Application") -> "None":
        """Draws the terminal graphic."""
        output = app.output
        output.hide_cursor()
        # Save cursor position
        app.output.write_raw("\x1b[s")
        # Move the cursor to where we want the image
        output.cursor_goto(self.ypos + 1, self.xpos + 1)
        output.flush()
        # Write image
        app.output.write_raw(self.draw())
        # Restore cursor
        app.output.write_raw("\x1b[u")
        # Show the cursor if it was already showing
        if (
            app.renderer._last_screen is not None
            and app.renderer._last_screen.show_cursor
        ):
            output.show_cursor()
        output.flush()

    @abstractmethod
    def draw(self) -> "str":
        """Returns a command to draw the terminal graphic."""
        ...

    def _draw_inline(self) -> "str":
        """Returns a command to draw the current graphic inline.

        Used when dumping notebooks to the terminal.

        Returns:
            A terminal command to draw the graphic inline

        """
        cmd = ""
        # Save cursor position
        cmd += "\x1b[s"
        # Move back to start of image position
        cmd += f"\x1b[{self.height-1}A\x1b[{self.width-1}D"
        # Place image
        cmd += self.draw_inline()
        # Restore cursor
        cmd += "\x1b[u"
        return cmd

    def draw_inline(self) -> "str":
        """Draw an inline version of the graphic."""
        return self.draw()

    def _hide(self, app: "Application") -> "None":
        """Hides the terminal graphic."""
        cmd = self.hide()
        if cmd:
            app.output.write_raw(cmd)
            app.output.flush()

    @abstractmethod
    def hide(self) -> "str":
        """Returns a command to hide the terminal graphic."""
        ...

    @abstractmethod
    def delete(self) -> "str":
        """Returns a command to delete the terminal graphic."""
        ...

    def set_position(self, xpos: "int", ypos: "int") -> "None":
        """Sets the graphic's display position, triggering a redraw if changed.

        Args:
            xpos: The top row of the graphic
            ypos: The left-most column of the graphic

        """
        if self.xpos != xpos or self.ypos != ypos:
            self.xpos = xpos
            self.ypos = ypos
            self.redraw = True
            self.on_resize.fire()

    def set_size(self, width: "int", height: "int") -> "None":
        """Sets the graphic's display dimensions, triggering a redraw if changed.

        Args:
            width: The width of the graphic in terminal cells
            height: The height of the graphic in terminal cells

        """
        if self.width != width or self.height != height:
            self.width = width
            self.height = height
            self.redraw = True
            self.on_move.fire()

    def __repr__(self):
        """Returns A string representation of the graphic."""
        return (
            f"<{self.__class__.__name__} "
            + " ".join(
                [
                    f"{key}={value}"
                    for key, value in {
                        "id": self.id,
                        "data": self.data[-5:],
                        "x": self.xpos,
                        "y": self.ypos,
                        "w": self.width,
                        "h": self.height,
                    }.items()
                ]
            )
            + ">"
        )
