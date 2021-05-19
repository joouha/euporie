# -*- coding: utf-8 -*-
"""Contains renderer classes which convert rich content to displayable output."""
import base64
import io
import os
import subprocess  # noqa S404 - Security implications have been considered
import tempfile
from importlib import import_module
from math import ceil
from shutil import which
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, cast

import rich
from PIL import Image  # type: ignore
from prompt_toolkit.application import get_app

from euporie.box import Border

if TYPE_CHECKING:
    from os import PathLike

    from euporie.app import App
    from euporie.cell import Cell


class DataRenderer:
    """Base class for rendering output data."""

    if TYPE_CHECKING:
        process: "Callable"
        validate: "Callable"

    def __init__(self, **kwargs: "Any"):
        """Initiate the data renderer object."""
        self.width = 1
        self.height = 1
        for kwarg, value in kwargs.items():
            setattr(self, kwarg, value)
        self.load()

    def load(self) -> "None":
        """Function which performs setup tasks for the renderer.

        This is run after initiation and prior to each rendering.
        """
        pass

    # async def _render(self, mime, data, **kwargs):
    # TODO - make this asynchronous again
    def render(
        self,
        data: "str",
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

        """
        self.width = width
        self.height = height
        if render_args is None:
            render_args = {}
        self.render_args = render_args

        self.load()
        ansi_data = self.process(data)
        # data = await self.process(data)
        return ansi_data

    @classmethod
    def select(cls, *args: "Any", **kwargs: "Any") -> "DataRenderer":
        """Returns an instance of the first valid sub-class of renderer.

        Args:
            *args: Arguments to pass to the renderer when initiated.
            **kwargs: Key-word arguments to pass to the renderer when initiated.

        """
        sub_renderers = cls.__subclasses__()
        if sub_renderers:
            for Renderer in sub_renderers:
                renderer = Renderer(*args, **kwargs)
                if not hasattr(renderer, "validate"):
                    # It's just a grouping class
                    continue
                if renderer.validate():
                    return renderer
        else:
            renderer = cls(*args, **kwargs)
            if renderer.validate():
                return renderer
        return FallbackRenderer(*args, **kwargs)


class SubprocessRenderMixin:
    """A renderer mixin which processes the data by calling a sub-command."""

    # If True, the data will be written to a temporary file and the filename is passed
    # to the command. If False, the data is piped in as standard input
    use_tempfile = False

    if TYPE_CHECKING:
        cmd: "list[Union[str, int, PathLike[str]]]"

    def validate(self) -> "bool":
        """Determine if the executable to call exists on the users $PATH."""
        return bool(which(str(self.cmd[0])))

    def process(self, data: "Union[bytes, str]") -> "str":
        """Call the command as a subprocess and return it's output.

        Args:
            data: The data to pass to the subprocess.

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

        """
        # Convert all command arguments to strings
        cmd = list(map(str, self.cmd))

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


class PythonRenderMixin:
    """Mixin for renderers which use external python libraries."""

    if TYPE_CHECKING:
        module: str

    def validate(self) -> "bool":
        """Checks the required python module is importable."""
        try:
            import_module(self.module)
        except ModuleNotFoundError:
            return False
        else:
            return True


class RichRendererMixin(DataRenderer):
    """A mixin for processing `rich.console.RenderableType` objects."""

    def load(self) -> "None":
        """Get a `rich.console.Console` instance for rendering."""
        self.console = rich.get_console()

    def process(self, data: "rich.console.RenderableType") -> "str":
        """Render a `rich.console.RenderableType` to ANSI text.

        Args:
            data: An object renderable by `rich.console`.

        """
        buffer = self.console.render(
            data,
            self.console.options.update(max_width=self.width),
        )
        rendered_lines = self.console._render_buffer(buffer)
        return rendered_lines


class RichRenderer(RichRendererMixin):
    """A renderer for `rich.console.RenderableType` objects."""

    def validate(self) -> "bool":
        """Always return `True` as `rich` is a dependency of `euporie`."""
        return True


class HTMLRenderer(DataRenderer):
    """A grouping renderer for HTML."""


class html_w3m(HTMLRenderer, SubprocessRenderMixin):
    """Renderers HTML using `w3m`."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["w3m", "-T", "text/html", "-cols", f"{self.width}"]


class html_elinks(HTMLRenderer, SubprocessRenderMixin):
    """Renderers HTML using `elinks`."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = [
            "elinks",
            "-dump",
            "-dump-width",
            f"{self.width}",
            "-no-numbering",
            "-force-html",
            "-no-references",
        ]


class html_lynx(HTMLRenderer, SubprocessRenderMixin):
    """Renderers HTML using `lynx`."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["lynx", "-dump", "-stdin", f"-width={self.width}"]


class html_links(HTMLRenderer, SubprocessRenderMixin):
    """Renderers HTML using `lynx`."""

    use_tempfile = True

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["links", "-width", self.width, "-dump"]


class html_mtable_py(HTMLRenderer, RichRendererMixin, PythonRenderMixin):
    """Renders HTML tables using `mtable` by converting to markdown."""

    module = "mtable"

    def process(self, data: "rich.console.RenderableType") -> "str":
        """Converts HTML tables to markdown with `mtable`.

        The resulting markdown is rendered using rich.

        Args:
            data: An HTML string.

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

    def validate(self) -> "bool":
        """Always return True as `html.parser` is in the standard library."""
        return True

    def load(self) -> "None":
        """Instantiate a class to strip HTML tags.

        This is assigned to the class on first load rather than a specific
        instance, so it can be reused.
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

    def process(self, data: "str") -> "str":
        """Strip tags from HTML data.

        Args:
            data: A string of HTML data.

        """
        import re
        from html.parser import HTMLParser

        assert isinstance(self.stripper, HTMLParser)
        self.stripper.feed(data)
        data = self.stripper.get_data()
        data = "\n".join([x.strip() for x in data.strip().split("\n")])
        data = re.sub("\n\n\n+", "\n\n", data)
        return data


class ImageRenderer(DataRenderer):
    """A grouping renderer for images."""

    if TYPE_CHECKING:
        image: Image

    def __init__(
        self,
        *args: "Any",
        image: "Optional[Image]" = None,
        **kwargs: "Any",
    ):
        """Initiate the image renderer.

        Args:
            *args: Arguments to pass to the renderer initiation method.
            image: Optionally pass a loaded pillow image (to prevent re-loading).
            **kwargs: Key-word arguments to pass to the renderer initiation method.

        """
        self.image = image
        self.px = self.py = 0
        super().__init__(*args, **kwargs)

    def render(
        self,
        data: "str",
        width: "int",
        height: "int",
        render_args: "Optional[dict[str, Any]]" = None,
    ) -> "str":
        """Determine the width and height of the output an image before rendering.

        Images are downsized to fit in the available output width.

        Args:
            data: The original data to be rendered.
            width: The desired output width in columns.
            height: The desired output height in rows.
            render_args: A dictionary of arguments to be made availiable during
                processing.

        """
        img_bytes = io.BytesIO(base64.b64decode(data))
        try:
            self.image = Image.open(img_bytes)
        except IOError:
            pass
        else:
            # Get the original image size in pixels
            orig_px, orig_py = self.image.size
            # Get the pixel size of one terminal block
            app = cast("App", get_app())
            char_px, char_py = app.char_size_px
            # Scale image down if it is larger than available width
            pixels_per_col = orig_px / char_px
            # Only down-scale images
            scaling_factor = min(1, width / pixels_per_col)
            # Pixel & character values need to be integers
            self.px = ceil(orig_px * scaling_factor)
            self.py = ceil(orig_py * scaling_factor)

            width = ceil(self.px / char_px)
            height = ceil(self.py / char_py)

        return super().render(data, width=width, height=height, render_args=render_args)


class SixelMixerRenderer(ImageRenderer):
    """Renderer class for mixing sixel and ANSI images.

    If the cell containing the output is flagged as partially obscured, falls back
    to ANSI image rendering so as no to break the display.
    """

    def validate(self) -> "bool":
        """Determine if the terminal supports sixel graphics."""
        return bool(cast("App", get_app()).has_sixel_graphics)

    def process(self, data: "str") -> "str":
        """Generate sixel / ANSI image ouput.

        Uses cursor movement commands to correctly place sixel images.

        Args:
            data: The base64 encoded image data.

        """
        output = ""
        # Add text representation
        cell = self.render_args.get("cell")
        if cell is not None and cell.obscured():
            output += AnsiImageRenderer.select(image=self.image).render(
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
        # output += super().process(data)
        sixel = SixelRenderer.select(image=self.image).render(
            data,
            width=self.width,
            height=self.height,
            render_args=self.render_args,
        )
        output += sixel
        # Restore cursor position
        output += "\x1b[u"
        return output


class SixelRenderer(DataRenderer):
    """Grouping class for sixel image renderers."""

    def validate(self) -> "bool":
        """Ensure terminal has sixel graphics and the renderer is valid."""
        return bool(cast("App", get_app()).has_sixel_graphics) and super().validate()


class img_sixel_imagemagik(SixelRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render images as sixel using ImageMagic."""

    def load(self) -> "None":
        """Sets the command to use for rendering.

        Additionally sets the default image size and background colour if they have not
        yet been passed to the render function (i.e. during validation).
        """
        if not hasattr(self, "px"):
            self.px = self.py = 0
        app = cast("App", get_app())
        self.bg_color = app.bg_color or "#FFFFFF"
        self.cmd = [
            "convert",
            "-",
            "-geometry",
            f"{self.px}x{self.py}",
            "-background",
            self.bg_color,
            "-flatten",
            "sixel:-",
        ]

    def process(self, data: "Union[bytes, str]") -> "str":
        """Decode the base64 encoded image data before processing.

        Args:
            data: base64 encoded image data

        """
        data_bytes = base64.b64decode(data)
        output = super().process(data_bytes)
        return output


class img_sixel_timg_py(SixelRenderer, ImageRenderer, PythonRenderMixin):
    """Render images as sixels using `timg`."""

    module = "timg"

    def process(self, data: "str") -> "str":
        """Converts a `PIL.Image` to a sixel string using `timg`.

        It is necessary to set transparent parts of the image to the terminal
        background colour.

        Args:
            data: The base64 encoded image data.

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


class img_sixel_teimpy(SixelRenderer, ImageRenderer, PythonRenderMixin):
    """Render images as sixels using `teimpy`."""

    module = "teimpy"

    def process(self, data: "str") -> "str":
        """Converts a `PIL.Image` to a sixel string using `teimpy`.

        It is necessary to set transparent parts of the image to the terminal
        background colour.

        Args:
            data: The base64 encoded image data.

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

    def validate(self) -> "bool":
        """Determine if the terminal supports the kitty graphics protocol."""
        return bool(cast("App", get_app()).has_kitty_graphics)

    def load(self) -> "None":
        """Does nothing."""
        pass

    def process(self, data: "str") -> "str":
        """Convert a image to kitty graphics escape sequences which display the image.

        Args:
            data: The base64 encoded image data.

        """
        output = ""

        # Create image id for kitty using Cantor pairing of cell id and output index
        a = self.render_args.get("cell", -1).index
        b = self.render_args.get("output_index")
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

    def process(self, data: "Union[bytes, str]") -> "str":
        """Decode the base64 encoded image data.

        Args:
            data: The base64 encoded image data.

        """
        data_bytes = base64.b64decode(data)
        output = super().process(data_bytes)
        return output


class img_ansi_timg(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `timg` command."""

    def validate(self) -> "bool":
        """Ensures the binary used for rendering exists."""
        # There is a python package called timg which provided an executable
        # That's not the one we are aftere here, so check if it is installed
        try:
            import timg  # noqa F401
        except ModuleNotFoundError:
            return super().validate()
        else:
            return False

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        app = cast("App", get_app())
        self.bg_color = app.bg_color or "#FFFFFF"
        self.cmd = [
            "timg",
            f"-g{self.width}x{self.width}",
            "--compress",
            "-b",
            self.bg_color,
            "-pq",
            "--threads=-1",
            "-",
        ]


class img_ansi_catimg(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `catimg` command."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["catimg", "-w", self.width * 2, "-"]


class img_ansi_icat(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `icat` command."""

    use_tempfile = True

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["icat", "-w", self.width, "--mode", "24bit"]


class ansi_tiv(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `tiv` command."""

    use_tempfile = True

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["tiv", "-w", self.width, "-h", self.height]


class img_ansi_timg_py(AnsiImageRenderer, ImageRenderer, PythonRenderMixin):
    """Render an image as ANSI text using the `timg` python package."""

    module = "timg"

    def process(self, data: "Union[bytes, str]") -> "str":
        """Converts a `PIL.Image` to a ansi text string using `timg`.

        It is necessary to set transparent parts of the image to the terminal
        background colour.

        Args:
            data: The base64 encoded image data.

        """
        import timg

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


class img_ansi_img2unicode_py(AnsiImageRenderer, ImageRenderer, PythonRenderMixin):
    """Render an image as ANSI text using the `img2unicode` python package."""

    module = "img2unicode"

    def process(self, data: "Union[bytes, str]") -> "str":
        """Converts a `PIL.Image` to a sixel string using `img2unicode`.

        Args:
            data: The base64 encoded image data.

        """
        from img2unicode import FastQuadDualOptimizer, Renderer  # type: ignore

        output = io.StringIO()
        Renderer(
            FastQuadDualOptimizer(), max_w=self.width, max_h=self.height
        ).render_terminal(self.image, output)
        output.seek(0)
        return output.read()


class img_ansi_viu(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `viu` command."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["viu", "-w", self.width, "-s", "-"]


class img_ansi_jp2a(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `jp2a` command."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["jp2a", "--color", f"--height={self.height}", "-"]


class img_ansi_img2txt(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    """Render an image as ANSI text using the `img2txt` command."""

    use_tempfile = True

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = ["img2txt", "-W", self.width, "-H", self.height]


class img_ansi_placeholder(AnsiImageRenderer, ImageRenderer):
    """Render an image placeholder."""

    msg = "[Image]"

    def validate(self) -> "bool":
        """Always `True` as rendering an image placeholder is always possible."""
        # This is always an option
        return True

    def process(self, data: "Union[bytes, str]") -> "str":
        """Converts a `PIL.Image` to a sixel string using `img2unicode`.

        Args:
            data: The base64 encoded image data.

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


class svg_librsvg(SVGRenderer, PythonRenderMixin):
    """Renders SVGs using `cairosvg`."""

    module = "cairosvg"

    def process(self, data: "str") -> "str":
        """Converts SVG text data to a base64 encoded PNG image and renders that.

        Args:
            data: The SVG text data.

        """
        import cairosvg  # type: ignore

        data_bytes = cairosvg.surface.PNGSurface.convert(data, write_to=None)
        data = base64.b64encode(data_bytes).decode()
        return ImageRenderer.select().render(
            data, self.width, self.height, self.render_args
        )


class svg_imagemagik(SVGRenderer, SubprocessRenderMixin):
    """Renders SVGs using `imagemagik`."""

    def load(self) -> "None":
        """Sets the command to use for rendering."""
        self.cmd = [
            "convert",
            "-",
            "PNG:-",
        ]

    def process(self, data: "Union[bytes, str]") -> "str":
        """Converts SVG text data to a base64 encoded PNG image and renders that.

        Args:
            data: The SVG text data.

        """
        png_bytes = super().process(data)
        png_str = base64.b64encode(png_bytes).decode()
        return ImageRenderer.select().render(
            png_str, self.width, self.height, self.render_args
        )


class FallbackRenderer(DataRenderer):
    """Fallback renderer, used if nothing else works.

    This should never be needed.
    """

    def validate(self) -> "bool":
        """Always returns `True`."""
        return True

    def process(self, data: "str") -> "str":
        """Retruns text stating the data could not be renderered.

        Args:
            data: The data to be rendered.

        """
        return "(Could not render output)"
