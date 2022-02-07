"""Contains a sixel terminal graphic class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# from euporie.render import SixelRenderer
from euporie.convert.base import convert
from euporie.graphics.base import TerminalGraphic

if TYPE_CHECKING:
    from typing import Any, Optional

    from prompt_toolkit.filters import FilterOrBool

__all__ = ["SixelTerminalGraphic"]

log = logging.getLogger(__name__)


class SixelTerminalGraphic(TerminalGraphic):
    """A terminal graphic class which uses sixels to render images."""

    final_format = "sixel"

    def __init__(
        self,
        id: "int",
        data: "str",
        format_: "str",
        visible: "FilterOrBool",
        fg_color: "Optional[str]" = None,
        bg_color: "Optional[str]" = None,
    ) -> "None":
        """Creates a new sixel graphic."""
        super().__init__(id, data, format_, visible, fg_color, bg_color)
        self.redraw = True
        self.command = ""
        self.refresh = True
        self.on_resize += self.trigger_refresh

    def trigger_refresh(self, caller: "Any") -> "None":
        """Tells the graphic system this graphic needs to be rerenderer."""
        self.refresh = True

    def load(self) -> "None":
        """Loads the sixel command."""
        self.command = convert(
            self.data,
            from_=self.format_,
            to=self.final_format,
            cols=self.width,
            rows=self.height,
            fg=self.fg_color,
            bg=self.bg_color,
        )

    def draw(self) -> "str":
        """Returns a sixel escape code for drawing the graphic."""
        if self.refresh:
            self.load()
            self.refresh = False
        return self.command

    def hide(self) -> "str":
        """Does nothing."""
        return ""

    def delete(self) -> "str":
        """Does nothing."""
        return ""
