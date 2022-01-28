# -*- coding: utf-8 -*-
"""Contains renderer classes which convert rich content to displayable output."""
from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from euporie.render.base import DataRenderer
from euporie.render.image.base import ImageRenderer
from euporie.render.mixin import PythonRenderMixin, SubprocessRenderMixin

if TYPE_CHECKING:
    from typing import Any, Union

__all__ = ["SVGRenderer", "svg_librsvg", "svg_imagemagik"]

log = logging.getLogger(__name__)


class SVGRenderer(DataRenderer):
    """Grouping class for SVG renderers."""

    pass


class svg_librsvg(PythonRenderMixin, SVGRenderer):
    """Renders SVGs using `cairosvg`."""

    modules = ["cairosvg"]
    priority = 0

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Creates a new svg renderer using cairosvg."""
        super().__init__(*args, **kwargs)
        self.image_renderer = ImageRenderer.select(
            width=self.width,
            height=self.height,
            graphic=self.graphic,
            bg_color=self.bg_color,
        )

    def process(self, data: "str") -> "Union[bytes, str]":
        """Converts SVG text data to a base64 encoded PNG image and renders that.

        Args:
            data: The SVG text data.

        Returns:
            An string of ANSI escape sequences representing the input image.

        """
        import cairosvg  # type: ignore

        png_bytes = cairosvg.surface.PNGSurface.convert(data, write_to=None)
        png_b64str = base64.b64encode(png_bytes).decode()
        # Update the graphic's data
        if self.graphic:
            self.graphic.data = png_b64str
        output = self.image_renderer.render(png_b64str, self.width, self.height)
        self.width, self.height = self.image_renderer.width, self.image_renderer.height
        return output


class svg_imagemagik(SubprocessRenderMixin, SVGRenderer):
    """Renders SVGs using `imagemagik`."""

    cmd = "magick"

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Creates a new svg renderer using imagemagick."""
        super().__init__(*args, **kwargs)
        self.image_renderer = ImageRenderer.select(
            width=self.width,
            height=self.height,
            graphic=self.graphic,
            bg_color=self.bg_color,
        )

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = [
            "-background",
            self.bg_color or self.app.term_info.background_color.value,
            "-",
            "PNG:-",
        ]

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Converts SVG text data to a base64 encoded PNG image and renders that.

        Args:
            data: The SVG text data.

        Returns:
            An string of ANSI escape sequences representing the input image.

        """
        png_bytes = super().call_subproc(str(data).encode())
        png_b64str = base64.b64encode(png_bytes).decode()
        # Update the graphic's data
        if self.graphic:
            self.graphic.data = png_b64str
        output = self.image_renderer.render(png_b64str, self.width, self.height)
        self.width, self.height = self.image_renderer.width, self.image_renderer.height
        return output
