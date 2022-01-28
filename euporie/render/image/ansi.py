"""Contains renderer classes which convert images to ansi text."""

from __future__ import annotations

import io
import logging
from importlib import import_module
from math import ceil
from typing import TYPE_CHECKING

from PIL import Image  # type: ignore

from euporie.box import RoundBorder as Border
from euporie.render.image.base import ImageRenderer
from euporie.render.mixin import Base64Mixin, PythonRenderMixin, SubprocessRenderMixin

if TYPE_CHECKING:
    from typing import Union

__all__ = [
    "AnsiImageRenderer",
    "img_ansi_timg",
    "img_ansi_chafa",
    "img_ansi_catimg",
    "img_ansi_icat",
    "ansi_tiv",
    "img_ansi_timg_py",
    "img_ansi_img2unicode_py",
    "img_ansi_viu",
    "img_ansi_jp2a",
    "img_ansi_img2txt",
    "img_ansi_placeholder",
]

log = logging.getLogger(__name__)


class AnsiImageRenderer(ImageRenderer):
    """Grouping class for ANSI image renderers."""

    priority = 1


class img_ansi_timg(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `timg` command."""

    cmd = "timg"

    @classmethod
    def validate(cls) -> "bool":
        """Ensures the binary used for rendering exists."""
        # There is a python package called timg which provides an executable
        # That's not the one we are aftere here, so check if it is installed
        try:
            import_module(cls.cmd)  # noqa F401
        except ModuleNotFoundError:
            return super().validate()
        else:
            return False

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = [
            f"-g{self.width}x{self.width}",
            "--compress",
            "-pq",
            "--threads=-1",
            "-",
        ]
        if self.bg_color:
            self.args += ["-b", self.bg_color]


class img_ansi_chafa(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `chafa` command."""

    cmd = "chafa"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = [
            "--format=symbols",
            f"--size={self.width}x{self.height}",
            "--stretch",
            "-",
        ]


class img_ansi_catimg(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `catimg` command."""

    cmd = "catimg"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = ["-w", self.width * 2, "-"]


class img_ansi_icat(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `icat` command."""

    cmd = "icat"
    use_tempfile = True

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = ["-w", self.width, "--mode", "24bit"]


class ansi_tiv(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `tiv` command."""

    cmd = "tiv"
    use_tempfile = True

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = ["-w", self.width, "-h", self.height]


class img_ansi_timg_py(Base64Mixin, PythonRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `timg` python package."""

    modules = ["timg"]

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Converts a `PIL.Image` to a ansi text string using `timg`.

        It is necessary to set transparent parts of the image to the terminal
        background colour.

        Args:
            data: The base64 encoded image data.

        Returns:
            An string of ANSI escape sequences representing the input image.

        """
        import timg  # type: ignore

        self.image.thumbnail((self.px, self.py))
        # Set transparent colour to background colour
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
        w, h = self.image.size
        self.image = self.image.resize((self.width, ceil(self.width / w * h)))
        output = timg.Ansi24HblockMethod(self.image).to_string()
        return output


class img_ansi_img2unicode_py(Base64Mixin, PythonRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `img2unicode` python package."""

    modules = ["img2unicode"]

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Converts a `PIL.Image` to a sixel string using `img2unicode`.

        Args:
            data: The base64 encoded image data.

        Returns:
            An string of ANSI escape sequences representing the input image.

        """
        from img2unicode import FastQuadDualOptimizer, Renderer  # type: ignore

        output = io.StringIO()
        Renderer(
            FastQuadDualOptimizer(), max_w=self.width, max_h=self.height
        ).render_terminal(self.image, output)
        output.seek(0)
        return output.read()


class img_ansi_viu(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `viu` command."""

    cmd = "viu"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = ["-w", self.width, "-s", "-"]


class img_ansi_jp2a(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `jp2a` command."""

    cmd = "jp2a"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = ["--color", f"--height={self.height}", "-"]


class img_ansi_img2txt(Base64Mixin, SubprocessRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `img2txt` command."""

    cmd = "img2txt"
    use_tempfile = True

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = ["-W", self.width, "-H", self.height]


class img_ansi_placeholder(AnsiImageRenderer):
    """Render an image placeholder."""

    msg = "[Image]"

    @classmethod
    def validate(cls) -> "bool":
        """Always `True` as rendering an image placeholder is always possible.

        Returns:
            True.

        """
        # This is always an option
        return True

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Converts a `PIL.Image` to a sixel string using `img2unicode`.

        Args:
            data: The base64 encoded image data.

        Returns:
            An ANSI string representing a box with the same dimensions as the rendered
                image.

        """
        b = Border
        t = len(self.msg)
        w = max(self.width, t + 4)
        h = max(3, self.height)
        # Top border
        output = b.TOP_LEFT + (b.HORIZONTAL * (w - 2)) + b.TOP_RIGHT + "\n"
        # Space above message
        for _ in range((h - 3) // 2):
            output += b.VERTICAL + (" " * (w - 2)) + b.VERTICAL + "\n"
        # Display the message
        output += b.VERTICAL + " "
        output += " " * ((self.width - 4 - t) // 2)
        output += self.msg
        output += " " * ((self.width - 4 - t) - (self.width - 4 - t) // 2)
        output += " " + b.VERTICAL + "\n"
        # Space below above message
        for _ in range((h - 3) - ((h - 3) // 2)):
            output += b.VERTICAL + (" " * (w - 2)) + b.VERTICAL + "\n"
        output += b.BOTTOM_LEFT + (b.HORIZONTAL * (w - 2)) + b.BOTTOM_RIGHT
        return output
