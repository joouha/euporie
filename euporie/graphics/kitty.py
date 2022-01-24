"""Contains the kitty terminal graphic class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.app import get_app
from euporie.graphics.base import TerminalGraphic

if TYPE_CHECKING:
    from typing import Any, Optional

    from prompt_toolkit.filters import FilterOrBool

__all__ = ["KittyTerminalGraphic"]

log = logging.getLogger(__name__)


class KittyTerminalGraphic(TerminalGraphic):
    """Defines a kitty terminal graphic."""

    def __init__(self, id: "int", data: "str", visible: "FilterOrBool") -> "None":
        """Creates a new kitty terminal graphic."""
        super().__init__(id, data, visible)
        self.loaded = False
        self.kitty_image_id: "Optional[int]" = None
        self.shown = False

    def load(self) -> "None":
        """Sends the graphic to the terminal without displaying it."""
        # Build the terminal query
        self.delete()
        data = self.data[:]
        query = ""
        while data:
            chunk, data = data[:4096], data[4096:]
            query += _kitty_cmd(
                chunk=chunk,
                a="t",  # We are sending an image without displaying it
                t="d",  # Transferring the image directly
                I=self.id + 1,  # Send and image number, wait for an image id
                p=1,  # Placement ID
                q=0,
                f=100,  # Sending a PNG image
                m=1 if data else 0,  # Data will be chunked
            )
        if result := get_app().term_info.query_terminal(query):
            apc_string = result.get("apc_string", "")
            if apc_string and apc_string.startswith("G"):
                if len(response := apc_string.lstrip("G").split(";")) >= 2:
                    for part in response[0].split(","):
                        key, _, value = part.partition("=")
                        if key == "i":
                            self.kitty_image_id = int(value)
        self.loaded = True

    def draw(self) -> "str":
        """Displays the graphic at its current location with its current dimensions."""
        if not self.loaded:
            self.load()
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
