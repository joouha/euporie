"""Contains the kitty terminal graphic class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.app import get_app
from euporie.graphics.base import TerminalGraphic

if TYPE_CHECKING:
    from typing import Any, Optional

    from prompt_toolkit.filters import FilterOrBool

    from euporie.terminal import TerminalQuery

__all__ = ["KittyTerminalGraphic"]

log = logging.getLogger(__name__)


class KittyTerminalGraphic(TerminalGraphic):
    """Defines a kitty terminal graphic."""

    def __init__(
        self,
        id: "int",
        data: "str",
        visible: "FilterOrBool",
        bg_color: "Optional[str]" = None,
    ) -> "None":
        """Creates a new kitty terminal graphic."""
        super().__init__(id, data, visible, bg_color)
        self.loaded = False
        self.kitty_image_id: "Optional[int]" = None
        self.shown = False
        self.app = get_app()
        self.kitty_event = self.app.term_info.kitty_graphic_id.event

    def load(self) -> "None":
        """Sends the graphic to the terminal without displaying it."""
        # Build the terminal query
        self.delete()
        data = self.data[:]
        while data:
            chunk, data = data[:4096], data[4096:]
            cmd = _kitty_cmd(
                chunk=chunk,
                a="t",  # We are sending an image without displaying it
                t="d",  # Transferring the image directly
                I=self.id,  # Send a unique image number, wait for an image id
                p=1,  # Placement ID
                q=0,
                f=100,  # Sending a PNG image
                m=1 if data else 0,  # Data will be chunked
            )
            self.app.output.write_raw(cmd)
        self.app.output.flush()

        # Listen for a kitty image id response
        self.kitty_event += self.update_kitty_image_id

    def update_kitty_image_id(self, query: "TerminalQuery") -> "None":
        """Sets the current graphic's image id base on the terminal's response."""
        if self.kitty_image_id is None and int(query.value.get("I", -1)) == self.id:
            self.kitty_image_id = int(query.value.get("i"))
            log.debug("Setting image id: %s", query.value)
            self.kitty_event -= self.update_kitty_image_id
            self.loaded = True

    def draw(self) -> "str":
        """Displays the graphic at its current location with its current dimensions."""
        if not self.loaded:
            self.load()
        if self.loaded:
            self.shown = True
            self.redraw = False
            # Place the image
            return _kitty_cmd(
                a="p",  # Display a previously transmitted image
                i=self.kitty_image_id,
                p=1,  # Placement ID
                m=0,  # No batches remaining
                q=2,  # No backchat
                c=self.width,
                r=self.height,
                C=1,  # Do not move the cursor
                z=-(2 ** 30) - 1,
            )
        return ""

    def draw_inline(self) -> "str":
        """Returns a command to draw the current graphic inline.

        Used when dumping notebooks to the terminal.

        Returns:
            A terminal command to draw the graphic inline

        """
        cmd = ""
        data = self.data[:]
        while data:
            chunk, data = data[:4096], data[4096:]
            cmd += _kitty_cmd(
                chunk=chunk,
                a="T",  # We are sending an image and displaying it
                t="d",  # Transferring the image directly
                I=self.id,  # Send a unique image number, wait for an image id
                p=1,  # Placement ID
                q=2,  # No chatback at all
                f=100,  # Sending a PNG image
                m=1 if data else 0,  # Data will be chunked
            )
        # Restore cursor
        cmd += "\x1b[u"
        return cmd

    def hide(self) -> "str":
        """Hides the graphic from show without deleting it."""
        if self.shown and not self.visible():
            self.shown = False
            return _kitty_cmd(
                a="d",
                d="i",
                i=self.kitty_image_id,
                q=1,
            )
        return ""

    def delete(self) -> "str":
        """Deletes the graphic from the terminal."""
        cmd = ""
        if self.loaded:
            cmd += _kitty_cmd(
                a="D",
                d="I",
                i=self.kitty_image_id,
                q=2,
            )
            self.shown = False
        return cmd


def _kitty_cmd(chunk: "str" = "", **params: "Any") -> "str":
    param_str = ",".join(
        [f"{key}={value}" for key, value in params.items() if value is not None]
    )
    cmd = f"\x1b_G{param_str}"
    if chunk:
        cmd += f";{chunk}"
    cmd += "\x1b\\"
    return cmd
