"""Contains a sixel terminal graphic class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.graphics.base import TerminalGraphic
from euporie.render import SixelRenderer

if TYPE_CHECKING:
    from typing import Any, Optional

    from prompt_toolkit.filters import FilterOrBool

__all__ = ["SixelTerminalGraphic"]

log = logging.getLogger(__name__)


class SixelTerminalGraphic(TerminalGraphic):
    """A terminal graphic class which uses sixels to render images."""

    def __init__(
        self,
        id: "int",
        data: "str",
        visible: "FilterOrBool",
        bg_color: "Optional[str]" = None,
    ) -> "None":
        """Creates a new sixel graphic."""
        super().__init__(id, data, visible, bg_color)
        self.renderer = SixelRenderer.select(bg_color=self.bg_color)
        self.redraw = True
        self.command = ""
        self.refresh = True
        self.on_move += self.trigger_refresh

    def trigger_refresh(self, caller: "Any") -> "None":
        """Tells the graphic system this graphic needs to be redrawn."""
        self.rerender = True

    def load(self) -> "None":
        """Loads the sixel command."""
        self.command = self.renderer.render(self.data, self.width, self.height)

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
