"""Contains renderer classes which display images using terminal graphics."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.config import config
from euporie.render.image.ansi import AnsiImageRenderer
from euporie.render.image.base import ImageRenderer

if TYPE_CHECKING:
    from typing import Any, Union

__all__ = ["TerminalGraphicsImageRenderer"]

log = logging.getLogger(__name__)


class TerminalGraphicsImageRenderer(ImageRenderer):
    """Use the terminal graphics system to display images."""

    priority = 0

    @classmethod
    def validate(cls) -> "bool":
        """Checks if terminal graphics can be used."""
        # TODO - infer validity from terminal query
        return True

    def __init__(self, *args: "Any", **kwargs: "Any"):
        """When initiating the render, load an ansi renderer.

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        """
        super().__init__(*args, **kwargs)
        self.ansi_renderer = AnsiImageRenderer.select(*args, **kwargs)

    def process(self, data: "str") -> "Union[bytes, str]":
        """Convert a image to kitty graphics escape sequences which display the image.

        Args:
            data: The base64 encoded image data.

        Returns:
            An ANSI escape sequence for displaying the image using the kitty graphics
                protocol.

        """
        output = ""
        if self.graphic is not None and (self.graphic.visible() or config.dump):
            output += "\n" * (self.height - 1)
            output += " " * (self.width - 1)
            if config.dump:
                self.graphic.set_size(width=self.width, height=self.height)
                output += "\001"
                output += self.graphic._draw_inline()
                output += "\002"
        else:
            image_lines = self.ansi_renderer.render(
                data, width=self.width, height=self.height
            )
            output += image_lines

        # Expand or trim height of ansi output to match expected height
        output = "\n".join(
            output.splitlines()[: self.height]
            + ["\n"] * (self.height - len(output.split("\n")))
        )

        return output
