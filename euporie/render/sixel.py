"""Contains renderer classes which convert rich content to displayable output."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from PIL import Image  # type: ignore

from euporie.render.base import DataRenderer
from euporie.render.mixin import ImageMixin, PythonRenderMixin, SubprocessRenderMixin

if TYPE_CHECKING:
    from typing import Union

__all__ = [
    "SixelRenderer",
    "sixel_img2sixel",
    "sixel_imagemagik",
    "sixel_chafa",
    "sixel_timg_py",
    "sixel_teimpy",
]

log = logging.getLogger(__name__)


class SixelRenderer(ImageMixin, DataRenderer):
    """Grouping class for sixel image renderers."""


class sixel_img2sixel(SubprocessRenderMixin, SixelRenderer):
    """Render images as sixel using libsixel' ``img2sixel`` command."""

    cmd = "img2sixel"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering.

        Additionally sets the default image size and background colour if they have not
        yet been passed to the render function (i.e. during validation).

        Args:
            data: The cell output data to be rendered.

        """
        super().load(data)
        if not hasattr(self, "px"):
            self.px = self.py = 0
        bg_color = self.bg_color or self.app.term_info.background_color.value
        self.args = [
            f"--width={self.px}",
            f"--height={self.py}",
            f"--bgcolor={bg_color}",
        ]

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Decode the base64 encoded image data before processing.

        Args:
            data: base64 encoded image data

        Returns:
            An ANSI string representing the rendered input.

        """
        data_bytes = base64.b64decode(data)
        output = super().process(data_bytes)
        return output


class sixel_imagemagik(SubprocessRenderMixin, SixelRenderer):
    """Render images as sixel using ImageMagic."""

    cmd = "magick"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering.

        Additionally sets the default image size and background colour if they have not
        yet been passed to the render function (i.e. during validation).

        Args:
            data: The cell output data to be rendered.

        """
        super().load(data)
        if not hasattr(self, "px"):
            self.px = self.py = 0
        bg_color = self.bg_color or self.app.term_info.background_color.value
        self.args = [
            "-",
            "-geometry",
            f"{self.px}x{self.py}",
            "-background",
            bg_color,
            "-flatten",
            "sixel:-",
        ]

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Decode the base64 encoded image data before processing.

        Args:
            data: base64 encoded image data

        Returns:
            An ANSI string representing the rendered input.

        """
        data_bytes = base64.b64decode(data)
        output = super().process(data_bytes)
        return output


class sixel_chafa(SubprocessRenderMixin, SixelRenderer):
    """Render images as sixel using chafa."""

    cmd = "chafa"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering.

        Additionally sets the default image size and background colour if they have not
        yet been passed to the render function (i.e. during validation).

        Args:
            data: The cell output data to be rendered.

        """
        super().load(data)
        self.args = [
            "--format=sixel",
            f"--size={self.width}x{self.height}",
            "-",
        ]

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Decode the base64 encoded image data before processing.

        Args:
            data: base64 encoded image data

        Returns:
            An ANSI string representing the rendered input.

        """
        data_bytes = base64.b64decode(data)
        output = super().process(data_bytes)
        return output


class sixel_timg_py(PythonRenderMixin, SixelRenderer):
    """Render images as sixels using `timg`."""

    modules = ["timg"]

    def process(self, data: "str") -> "Union[bytes, str]":
        """Converts a `PIL.Image` to a sixel string using `timg`.

        It is necessary to set transparent parts of the image to the terminal
        background colour.

        Args:
            data: The base64 encoded image data.

        Returns:
            An ANSI escape sequence for displaying the image using the sixel graphics
                protocol.

        """
        import timg  # type: ignore

        self.image.thumbnail((self.px, self.px))
        # Set transparent colour to terminal background
        if self.image.mode in ("RGBA", "LA") or (
            self.image.mode == "P" and "transparency" in self.image.info
        ):
            bg_color = self.bg_color or self.app.term_info.background_color.value
            alpha = self.image.convert("RGBA").getchannel("A")
            bg = Image.new("RGBA", self.image.size, bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg
        self.image = self.image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
            "RGB", palette=Image.ADAPTIVE, colors=16
        )
        data = timg.SixelMethod(self.image).to_string()
        return data


class sixel_teimpy(PythonRenderMixin, SixelRenderer):
    """Render images as sixels using `teimpy`."""

    modules = ["teimpy"]

    def process(self, data: "str") -> "Union[bytes, str]":
        """Converts a `PIL.Image` to a sixel string using `teimpy`.

        It is necessary to set transparent parts of the image to the terminal
        background colour.

        Args:
            data: The base64 encoded image data.

        Returns:
            An ANSI string representing the rendered input.

        """
        import numpy as np  # type: ignore
        import teimpy  # type: ignore

        self.image.thumbnail((self.px, self.px))
        # Set transparent colour to terminal background
        if self.image.mode in ("RGBA", "LA") or (
            self.image.mode == "P" and "transparency" in self.image.info
        ):
            alpha = self.image.convert("RGBA").getchannel("A")
            bg = Image.new("RGBA", self.image.size, self.bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg.convert("RGB")
        data = teimpy.get_drawer(teimpy.Mode.SIXEL).draw(np.asarray(self.image))
        return data
