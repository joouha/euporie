# -*- coding: utf-8 -*-
"""Contains renderer classes which convert rich content to displayable output."""
from __future__ import annotations

import base64
import io
import logging
import os
import subprocess  # noqa S404 - Security implications have been considered
import tempfile
from abc import ABCMeta, abstractmethod
from importlib import import_module
from math import ceil
from shutil import which
from typing import TYPE_CHECKING, Any, Optional, Type, Union, cast

import rich
from PIL import Image  # type: ignore
from prompt_toolkit.application import get_app

from euporie.box import Border

if TYPE_CHECKING:
    from os import PathLike

    from euporie.app import App
    from euporie.cell import Cell

log = logging.getLogger(__name__)


class DataRendererMixin(metaclass=ABCMeta):
    """Metaclass for DataRenderer Mixins."""

    width: "int"
    height: "int"

    def __init__(self, **kwargs: "Any"):
        """Initate the mixin.

        Args:
            **kwargs: Optional key-word arguments.

        """

    @abstractmethod
    def process(self, data: "Any") -> "Union[str, bytes]":
        """Abstract function which processes cell output data.

        Args:
            data: Cell output data.

        Returns:
            An empty string.

        """
        return ""


class DataRenderer(metaclass=ABCMeta):
    """Base class for rendering output data."""

    render_args: "dict"

    def __init__(self, **kwargs: "Any"):
        """Initiate the data renderer object."""
        self.width = 1
        self.height = 1
        for kwarg, value in kwargs.items():
            setattr(self, kwarg, value)

    def load(self, data: "Any") -> "None":
        """Function which performs setup tasks for the renderer.

        This is run after initiation and prior to each rendering.

        Args:
            data: Cell output data.

        """
        pass

    @classmethod
    def validate(cls) -> "bool":
        """Determine whether a DataRenderer should be used to render outputs."""
        return False

    @abstractmethod
    def process(self, data: "Any") -> "Union[str, bytes]":
        """Abstract function which processes cell output data.

        Args:
            data: Cell output data.

        Returns:
            NotImplemented

        """

    # async def _render(self, mime, data, **kwargs):
    # TODO - make this asynchronous again
    def render(
        self,
        data: "Any",
        width: "int",
        height: "int",
        render_args: "Optional[dict]" = None,
    ) -> "str":
        """Render the input data to ANSI.

        Args:
            data: The original data to be rendered.
            width: The desired output width in columns.
            height: The desired output height in rows.
            render_args: A dictionary of arguments to be made availiable during
                processing.

        Returns:
            An ANSI string.

        """
        self.width = width
        self.height = height
        if render_args is None:
            render_args = {}
        self.render_args = render_args

        self.load(data)
        output = self.process(data)

        if isinstance(output, bytes):
            ansi_data = output.decode()
        else:
            ansi_data = output

        return ansi_data

    @classmethod
    def select(cls, *args: "Any", **kwargs: "Any") -> "DataRenderer":
        """Selects a renderer of this type to use.

        If not valid renderer is found, return a fallback renderer.

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        Returns:
            A valid DataRenderer instance.

        """
        if Renderer := cls._select(*args, **kwargs):
            renderer = Renderer(*args, **kwargs)
            assert isinstance(renderer, DataRenderer)
            return renderer
        else:
            return FallbackRenderer(*args, **kwargs)

    @classmethod
    def _select(cls, *args: "Any", **kwargs: "Any") -> "Optional[Type[DataRenderer]]":
        """Returns an instance of the first valid sub-class of renderer.

        1. If the renderer has no sub-renderers, use it
        2.

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        Returns:
            An instance of the selected renderer.

        """
        # log.debug(f"Checking renderer {cls}")

        sub_renderers = cls.__subclasses__()

        # If there are no sub-renderers, try using the current renderer
        if not sub_renderers:
            log.debug(f"No sub-renderers found, validating {cls}")
            if cls.validate():
                # log.debug(f"{cls} is valid")
                return cls
            else:
                # log.debug(f"{cls} found to be invalid")
                return None

        # If there are sub-renderers, try selecting one
        # log.debug(f"Sub-renderers of {cls} are: {sub_renderers}")
        for Renderer in sub_renderers:
            selection = Renderer._select()
            if selection is not None:
                return selection
        else:
            return None


class Base64Mixin(DataRendererMixin):
    """Mixin to decode base64 encoded data."""

    def process(self, data: "Union[bytes, str]") -> "Union[str, bytes]":
        """Decode base64 encoded data.

        Args:
            data: The base64 encoded data.

        Returns:
            The decoded output as bytes.

        """
        data_bytes = base64.b64decode(data)
        output = super().process(data_bytes)
        return output


class SubprocessRenderMixin(DataRendererMixin):
    """A renderer mixin which processes the data by calling a sub-command."""

    # If True, the data will be written to a temporary file and the filename is passed
    # to the command. If False, the data is piped in as standard input
    use_tempfile = False

    cmd: "str"
    args: "list[Union[str, int, PathLike]]"

    @classmethod
    def validate(cls) -> "bool":
        """Determine if the executable to call exists on the users $PATH.

        Returns:
            True if the command exists on the user's $PATH, otherwise False.

        """
        return bool(which(str(cls.cmd)))

    def process(self, data: "Union[bytes, str]") -> "Union[bytes, str]":
        """Call the command as a subprocess and return it's output.

        Args:
            data: The data to pass to the subprocess.

        Returns:
            An ANSI string representing the input data.

        """
        if isinstance(data, str):
            data_bytes = data.encode()
        else:
            data_bytes = bytes(data)
        return self.call_subproc(data_bytes).decode()

    def call_subproc(self, data_bytes: "bytes") -> "bytes":
        """Call the command as a subprocess and return it's output as bytes.

        Args:
            data_bytes: The data to pass to the subprocess.

        Returns:
            The data printed to standard out by the subprocess.

        """
        # Convert all command arguments to strings
        cmd = list(map(str, [self.cmd, *self.args]))

        if self.use_tempfile:
            # If the command cannot read from stdin, create a temporary file to pass to
            # the command
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(data_bytes)
            tfile.close()
            cmd.append(tfile.name)

        # TODO render asynchronously
        # proc = await asyncio.create_subprocess_shell(
        # " ".join(cmd),
        # stdout=asyncio.subprocess.PIPE,
        # stdin=asyncio.subprocess.PIPE,
        # stderr=asyncio.subprocess.DEVNULL,
        # )
        # stdout, stderr = await proc.communicate(data)

        cmd = list(cmd)
        output_bytes = subprocess.check_output(cmd, input=data_bytes)  # noqa S603

        # TODO Log any stderr
        # print(stderr)

        # Clean up any temporary file
        if self.use_tempfile:
            tfile.close()
            os.unlink(tfile.name)

        return output_bytes


class PythonRenderMixin(DataRendererMixin):
    """Mixin for renderers which use external python libraries."""

    module: "str"

    @classmethod
    def validate(cls) -> "bool":
        """Checks the required python module is importable."""
        try:
            import_module(cls.module)
        except ModuleNotFoundError:
            return False
        else:
            return True


class RichRendererMixin(DataRendererMixin):
    """A mixin for processing `rich.console.RenderableType` objects."""

    console: "rich.console.Console"

    def load(self, data: "rich.console.RenderableType") -> "None":
        """Get a `rich.console.Console` instance for rendering."""
        self.console = rich.get_console()

    def process(self, data: "rich.console.RenderableType") -> "Union[bytes, str]":
        """Render a `rich.console.RenderableType` to ANSI text.

        Args:
            data: An object renderable by `rich.console`.

        Returns:
            An ANSI string representing the rendered input.

        """
        buffer = self.console.render(
            data,
            self.console.options.update(max_width=self.width),
        )
        rendered_lines = self.console._render_buffer(buffer)
        return rendered_lines


class RichRenderer(RichRendererMixin, DataRenderer):
    """A renderer for `rich.console.RenderableType` objects."""

    @classmethod
    def validate(cls) -> "bool":
        """Always return `True` as `rich` is a dependency of `euporie`."""
        return True


class HTMLRenderer(DataRenderer):
    """A grouping renderer for HTML."""


class html_w3m(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `w3m`."""

    cmd = "w3m"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = ["-T", "text/html", "-cols", f"{self.width}"]


class html_elinks(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `elinks`."""

    cmd = "elinks"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = [
            "-dump",
            "-dump-width",
            f"{self.width}",
            "-no-numbering",
            "-force-html",
            "-no-references",
        ]


class html_lynx(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `lynx`."""

    cmd = "lynx"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = ["-dump", "-stdin", f"-width={self.width}"]


class html_links(SubprocessRenderMixin, HTMLRenderer):
    """Renderers HTML using `lynx`."""

    cmd = "links"

    use_tempfile = True

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        self.args = ["-width", self.width, "-dump"]


class html_mtable_py(RichRendererMixin, PythonRenderMixin, HTMLRenderer):
    """Renders HTML tables using `mtable` by converting to markdown."""

    module = "mtable"

    def process(self, data: "rich.console.RenderableType") -> "Union[bytes, str]":
        """Converts HTML tables to markdown with `mtable`.

        The resulting markdown is rendered using rich.

        Args:
            data: An HTML string.

        Returns:
            An ANSI string representing the rendered input.

        """
        from mtable import MarkupTable  # type: ignore

        return super().process(
            rich.markdown.Markdown(
                "\n\n".join([table.to_md() for table in MarkupTable.from_html(data)])
            )
        )


class html_fallback_py(HTMLRenderer):
    """This uses `HTMLParser` from the standard library to strip html tags.

    This produces poor output, but does not require any python dependencies or
    external commands, thus it is the last resort for rendering HTML.
    """

    stripper = None

    @classmethod
    def validate(cls) -> "bool":
        """Always return True as `html.parser` is in the standard library."""
        return True

    def load(self, data: "str") -> "None":
        """Instantiate a class to strip HTML tags.

        This is assigned to the class on first load rather than a specific
        instance, so it can be reused.

        Args:
            data: An HTML string.

        """
        from html.parser import HTMLParser

        if self.stripper is None:

            class HTMLStripper(HTMLParser):
                """Very basic HTML parser which strips style and script tags."""

                def __init__(self):
                    super().__init__()
                    self.reset()
                    self.strict = False
                    self.convert_charrefs = True
                    self.text = io.StringIO()
                    self.skip = False
                    self.skip_tags = ("script", "style")

                def handle_starttag(
                    self, tag: "str", attrs: "list[tuple[str, Optional[str]]]"
                ) -> "None":
                    if tag in self.skip_tags:
                        self.skip = True

                def handle_endtag(self, tag: "str") -> "None":
                    if tag in self.skip_tags:
                        self.skip = False

                def handle_data(self, d: "str") -> "None":
                    if not self.skip:
                        self.text.write(d)

                def get_data(self) -> "str":
                    return self.text.getvalue()

            self.stripper = HTMLStripper()

    def process(self, data: "str") -> "Union[bytes, str]":
        """Strip tags from HTML data.

        Args:
            data: A string of HTML data.

        Returns:
            An ANSI string representing the rendered input.

        """
        import re
        from html.parser import HTMLParser

        assert isinstance(self.stripper, HTMLParser)
        self.stripper.feed(data)
        data = self.stripper.get_data()
        data = "\n".join([x.strip() for x in data.strip().split("\n")])
        data = re.sub("\n\n\n+", "\n\n", data)
        return data


class ImageMixin(DataRendererMixin):
    """Mixin for rendering images which calulates the size to render the image."""

    image: "Image"

    def __init__(
        self,
        **kwargs: "Any",
    ):
        """Initiate the image renderer.

        Args:
            **kwargs: Key-word arguments to pass to the renderer initiation method.

        """
        super().__init__(**kwargs)
        self.px = 0
        self.py = 0
        self.image: "Image"

    def load(
        self,
        data: "str",
    ) -> "None":
        """Determine the width and height of the output image before rendering.

        Images are downsized to fit in the available output width.

        Args:
            data: The original data to be rendered.

        """
        img_bytes = io.BytesIO(base64.b64decode(data))
        try:
            self.image = Image.open(img_bytes)
        except IOError:
            log.error("Could not load image.")
        else:
            # Get the original image size in pixels
            orig_px, orig_py = self.image.size
            # Get the pixel size of one terminal block
            app = cast("App", get_app())
            char_px, char_py = app.char_size_px
            # Scale image down if it is larger than available width
            pixels_per_col = orig_px / char_px
            # Only down-scale images
            scaling_factor = min(1, self.width / pixels_per_col)
            # Pixel & character values need to be integers
            self.px = ceil(orig_px * scaling_factor)
            self.py = ceil(orig_py * scaling_factor)

            self.width = ceil(self.px / char_px)
            self.height = ceil(self.py / char_py)
        assert self.image is not None


class ImageRenderer(ImageMixin, DataRenderer):
    """A grouping renderer for images."""


class SixelMixerRenderer(ImageRenderer):
    """Renderer class for mixing sixel and ANSI images.

    If the cell containing the output is flagged as partially obscured, falls back
    to ANSI image rendering so as no to break the display.
    """

    def __init__(self, *args: "Any", **kwargs: "Any"):
        """When initiating the render, load ansi and sixel image renderers.

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        """
        self.ansi_renderer = AnsiImageRenderer.select()
        self.sixel_renderer = SixelRenderer.select()

    @classmethod
    def validate(cls) -> "bool":
        """Determine if the terminal supports sixel graphics.

        Returns:
            True if the terminal supports the Sixel graphics protocol, otherwise False.

        """
        return bool(
            cast("App", get_app()).has_sixel_graphics
            and AnsiImageRenderer.select() is not None
            and SixelRenderer.select() is not None
        )

    def process(self, data: "str") -> "Union[bytes, str]":
        """Generate sixel / ANSI image ouput.

        Uses cursor movement commands to correctly place sixel images.

        Args:
            data: The base64 encoded image data.

        Returns:
            An ANSI string representing the rendered input.

        """
        assert self.sixel_renderer is not None
        assert self.ansi_renderer is not None

        output = ""
        # Add text representation
        cell = self.render_args.get("cell")
        if cell is not None and cell.obscured():
            output += self.ansi_renderer.render(
                data,
                width=self.width,
                height=self.height,
                render_args=self.render_args,
            )
        else:
            output += "\n".join([" " * self.width] * self.height)

        # data = super().process(data)
        # Save cursor position
        output += "\x1b[s"
        # Move cursor back to top left of image's space
        output += f"\x1b[{self.height-1}A\x1b[{self.width}D"
        # Add sixels
        output += self.sixel_renderer.render(
            data,
            width=self.width,
            height=self.height,
            render_args=self.render_args,
        )
        # Restore cursor position
        output += "\x1b[u"

        return output


class SixelRenderer(ImageMixin, DataRenderer):
    """Grouping class for sixel image renderers."""


class img_sixel_imagemagik(SubprocessRenderMixin, SixelRenderer):
    """Render images as sixel using ImageMagic."""

    cmd = "convert"

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
        app = cast("App", get_app())
        self.bg_color = app.bg_color or "#FFFFFF"
        self.args = [
            "-",
            "-geometry",
            f"{self.px}x{self.py}",
            "-background",
            self.bg_color,
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


class img_sixel_timg_py(PythonRenderMixin, SixelRenderer):
    """Render images as sixels using `timg`."""

    module = "timg"

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
            alpha = self.image.convert("RGBA").getchannel("A")
            bg = Image.new("RGBA", self.image.size, cast("App", get_app()).bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg
        self.image = self.image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
            "RGB", palette=Image.ADAPTIVE, colors=16
        )
        data = timg.SixelMethod(self.image).to_string()
        return data


class img_sixel_teimpy(PythonRenderMixin, SixelRenderer):
    """Render images as sixels using `teimpy`."""

    module = "teimpy"

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
            bg = Image.new("RGBA", self.image.size, cast("App", get_app()).bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg.convert("RGB")
        data = teimpy.get_drawer(teimpy.Mode.SIXEL).draw(np.asarray(self.image))
        return data


class img_kitty(ImageRenderer):
    """Renders an image using the kitty graphics protocol."""

    @classmethod
    def validate(cls) -> "bool":
        """Determine if the terminal supports the kitty graphics protocol."""
        return bool(cast("App", get_app()).has_kitty_graphics)

    def process(self, data: "str") -> "Union[bytes, str]":
        """Convert a image to kitty graphics escape sequences which display the image.

        Args:
            data: The base64 encoded image data.

        Returns:
            An ANSI escape sequence for displaying the image using the kitty graphics
                protocol.

        """
        output = ""

        # Create image id for kitty using Cantor pairing of cell id and output index
        a = self.render_args.get("cell_index", -1)
        b = self.render_args.get("output_index", -1)
        image_id = int(0.5 * (a + b) * (a + b + 1) + b)

        cell: "Optional[Cell]" = self.render_args.get("cell")
        if cell is not None and cell.obscured():
            output += AnsiImageRenderer.select().render(
                data, width=self.width, height=self.height
            )
        else:
            # Delete existing image in this space
            # output += f"\001\x1b_Ga=d,d=i,i={image_id}\x1b\\\002"
            # Fill image space
            output += "\n".join([" " * self.width] * self.height)
            # Save cursor position
            output += "\x1b[s"
            # Move back to start of image position
            output += f"\x1b[{self.height-1}A\x1b[{self.width}D"
            # Send the image
            params = {
                "a": "T",  # We are sending an image
                "q": 1,  # No backchat
                "f": "100",  # Sending a PNG image
                "t": "d",  # Transferring the image directly
                "i": image_id,
                # 'p': 1,
                "m": 1,  # Data will be chunked
                "c": self.width,
                "r": self.height,
                "z": -(2 ** 30) - 1,  # Put image under everything
            }
            # Remove newlines from base64 image data
            data = "".join(data.split("\n"))
            while data:
                chunk, data = data[:4096], data[4096:]
                params["m"] = 1 if data else 0
                param_str = ",".join(
                    [f"{key}={value}" for key, value in params.items()]
                )
                output += f"\001\x1b_G{param_str};{chunk}\x1b\\\002"
            # Restore cursor position
            output += "\x1b[u"
        return output


class AnsiImageRenderer(ImageRenderer):
    """Grouping class for ANSI image renderers."""


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
        app = cast("App", get_app())
        self.bg_color = app.bg_color or "#FFFFFF"
        self.args = [
            f"-g{self.width}x{self.width}",
            "--compress",
            "-b",
            self.bg_color,
            "-pq",
            "--threads=-1",
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

    module = "timg"

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

        self.image.thumbnail((self.width * 2, self.height * 2))
        # Set transparent colour to terminal background
        if self.image.mode in ("RGBA", "LA") or (
            self.image.mode == "P" and "transparency" in self.image.info
        ):
            alpha = self.image.convert("RGBA").getchannel("A")
            bg_color = cast("App", get_app()).bg_color
            bg = Image.new("RGBA", self.image.size, bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg
        self.image = self.image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
            "RGB", palette=Image.ADAPTIVE, colors=16
        )
        output = timg.Ansi24HblockMethod(self.image).to_string()
        return output


class img_ansi_img2unicode_py(Base64Mixin, PythonRenderMixin, AnsiImageRenderer):
    """Render an image as ANSI text using the `img2unicode` python package."""

    module = "img2unicode"

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
        output = b.TOP_LEFT + (b.HORIZONTAL * (w - 2)) + b.TOP_RIGHT + "\n"
        for _ in range((h - 3) // 2 + 1):
            output += b.VERTICAL + (" " * (w - 2)) + b.VERTICAL + "\n"
        output += b.VERTICAL + " "
        output += " " * ((self.width - 4 - t) // 2)
        output += self.msg
        output += " " * ((self.width - 4 - t) - (self.width - 4 - t) // 2)
        output += " " + b.VERTICAL + "\n"
        for _ in range((h - 3) - ((h - 3) // 2)):
            output += b.VERTICAL + (" " * (w - 2)) + b.VERTICAL + "\n"
        output += b.BOTTOM_LEFT + (b.HORIZONTAL * (w - 2)) + b.BOTTOM_RIGHT
        return output


class SVGRenderer(DataRenderer):
    """Grouping class for SVG renderers."""

    pass


class svg_librsvg(PythonRenderMixin, SVGRenderer):
    """Renders SVGs using `cairosvg`."""

    module = "cairosvg"

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
        return ImageRenderer.select().render(
            png_b64str, self.width, self.height, self.render_args
        )


class svg_imagemagik(SubprocessRenderMixin, SVGRenderer):
    """Renders SVGs using `imagemagik`."""

    cmd = "convert"

    def load(self, data: "str") -> "None":
        """Sets the command to use for rendering."""
        super().load(data)
        self.args = [
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
        return ImageRenderer.select().render(
            png_b64str, self.width, self.height, self.render_args
        )


class FallbackRenderer(DataRenderer):
    """Fallback renderer, used if nothing else works.

    This should never be needed.
    """

    @classmethod
    def validate(cls) -> "bool":
        """Always returns `True`.

        Returns:
            True.

        """
        return True

    def process(self, data: "str") -> "Union[bytes, str]":
        """Retruns text stating the data could not be renderered.

        Args:
            data: The data to be rendered.

        Returns:
            A string stating the output could not be rendered.

        """
        return "(Could not render output)"
