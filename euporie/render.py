# -*- coding: utf-8 -*-
import base64
import io
import os
import subprocess
import tempfile
from importlib import import_module
from math import ceil
from shutil import which

import rich
from PIL import Image
from prompt_toolkit.application import get_app

from euporie.box import Border


class DataRenderer:
    def __init__(self, **kwargs):

        self.width = 1
        self.height = 1
        for kwarg, value in kwargs.items():
            setattr(self, kwarg, value)
        self.load()

    def load(self):
        pass

    # async def _render(self, mime, data, **kwargs):
    def render(self, data, width, height, render_args=None):

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
    def select(cls, *args, **kwargs):
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
            renderer = cls()
            if renderer.validate():
                return renderer


class SubprocessRenderMixin:
    use_tempfile = False
    to_string = True

    def validate(self):
        return which(self.cmd[0])

    def process(self, data):
        # async def process(self, data):

        cmd = list(map(str, self.cmd))

        if isinstance(data, str):
            data = data.encode()

        if self.use_tempfile:
            # If the command cannot read from stdin, create a temporary file to pass to
            # the command
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(data)
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
        output = subprocess.check_output(cmd, input=data)

        # TODO Log any stderr
        # print(stderr)

        # Clean up any temporary file
        if self.use_tempfile:
            tfile.close()
            os.unlink(tfile.name)

        if self.to_string:
            output = output.decode()

        return output


class PythonRenderMixin:
    def validate(self):
        try:
            import_module(self.module)  # noqa
        except ModuleNotFoundError:
            return False
        else:
            return True


class RichRendererMixin(DataRenderer):
    def load(self):
        self.console = rich.get_console()

    def process(self, data):
        buffer = self.console.render(
            data,
            self.console.options.update(max_width=self.width),
        )
        self.rendered_lines = self.console._render_buffer(buffer)
        return self.rendered_lines


class RichRenderer(RichRendererMixin):
    def validate(self):
        return True


class HTMLRenderer(DataRenderer):
    pass


class html_w3m(HTMLRenderer, SubprocessRenderMixin):
    def load(self):
        self.cmd = ["w3m", "-T", "text/html", "-cols", f"{self.width}"]


class html_elinks(HTMLRenderer, SubprocessRenderMixin):
    def load(self):
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
    def load(self):
        self.cmd = ["lynx", "-dump", "-stdin", f"-width={self.width}"]


class html_links(HTMLRenderer, SubprocessRenderMixin):
    use_tempfile = True

    def load(self):
        self.cmd = ["links", "-width", self.width, "-dump"]


class html_mtable_py(RichRendererMixin, HTMLRenderer, PythonRenderMixin):
    """Converts HTML tables to markdown, then renders markdown with rich."""

    module = "mtable"

    def process(self, data):
        from mtable import MarkupTable

        return super().process(
            rich.markdown.Markdown(
                "\n\n".join([table.to_md() for table in MarkupTable.from_html(data)])
            )
        )


class html_fallback_py(HTMLRenderer):
    """
    This uses stdlib to strip html tags.

    This is the last resort for rendering HTML.
    """

    stripper = None

    def validate(self):
        return True

    def load(self):
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

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style"):
                        self.skip = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style"):
                        self.skip = False

                def handle_data(self, d):
                    if not self.skip:
                        self.text.write(d)

                def get_data(self):
                    return self.text.getvalue()

            self.stripper = HTMLStripper()

    def process(self, data):
        import re

        self.stripper.feed(data)
        data = self.stripper.get_data()
        data = "\n".join([x.strip() for x in data.strip().split("\n")])
        data = re.sub("\n\n\n+", "\n\n", data)
        return data


class ImageRenderer(DataRenderer):
    def __init__(self, *args, image=None, **kwargs):
        self.image = image
        self.px = self.py = 0
        super().__init__(*args, **kwargs)

    def render(self, data, width=None, height=None, render_args=None):

        img_bytes = io.BytesIO(base64.b64decode(data))
        try:
            self.image = Image.open(img_bytes)
        except IOError:
            pass
        else:
            orig_px, orig_py = self.image.size

            # Scale image down if it is larger than available width
            app = get_app()
            if hasattr(app, "app"):
                char_px = app.app.char_px
                char_py = app.app.char_py
            else:
                char_px, char_py = get_app().char_size_px

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
    def validate(self):
        return get_app().has_sixel_graphics

    def process(self, data):
        """Add in cursor movement commands to correctly place sixels"""
        output = ""
        # Add text representation
        if self.render_args.get("cell").obscured():
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
    def validate(self):
        return get_app().has_sixel_graphics and super().validate()


class img_sixel_imagemagik(SixelRenderer, ImageRenderer, SubprocessRenderMixin):
    def load(self):
        if not hasattr(self, "px"):
            self.px = self.py = 0
            self.bg_color = "#FFFFFF"
        self.cmd = [
            "convert",
            "-",
            "-geometry",
            f"{self.px}x{self.py}",
            "-background",
            get_app().bg_color,
            "-flatten",
            "sixel:-",
        ]

    def process(self, data):
        data = base64.b64decode(data)
        data = super().process(data)
        return data


class img_sixel_timg_py(SixelRenderer, ImageRenderer, PythonRenderMixin):
    module = "timg"

    def process(self, data):
        import timg

        self.image.thumbnail((self.px, self.px))
        # Set transparent colour to terminal background
        if self.image.mode in ("RGBA", "LA") or (
            self.image.mode == "P" and "transparency" in self.image.info
        ):
            alpha = self.image.convert("RGBA").getchannel("A")
            bg = Image.new("RGBA", self.image.size, get_app().bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg
        self.image = self.image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
            "RGB", palette=Image.ADAPTIVE, colors=16
        )
        data = timg.SixelMethod(self.image).to_string()
        return data


class img_sixel_teimpy(SixelRenderer, ImageRenderer, PythonRenderMixin):
    module = "teimpy"

    def process(self, data):
        import numpy as np
        import teimpy

        # data = super().process(data)
        self.image.thumbnail((self.px, self.px))
        # Set transparent colour to terminal background
        if self.image.mode in ("RGBA", "LA") or (
            self.image.mode == "P" and "transparency" in self.image.info
        ):
            alpha = self.image.convert("RGBA").getchannel("A")
            bg = Image.new("RGBA", self.image.size, get_app().bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg.convert("RGB")
        data = teimpy.get_drawer(teimpy.Mode.SIXEL).draw(np.asarray(self.image))
        return data


class img_kitty(ImageRenderer):
    def validate(self):
        return get_app().has_kitty_graphics

    def load(self):
        pass

    def process(self, data):

        output = ""

        # Create image id for kitty using Cantor pairing of cell id and output index
        a = self.render_args.get("cell").index
        b = self.render_args.get("output_index")
        image_id = int(0.5 * (a + b) * (a + b + 1) + b)

        if self.render_args.get("cell").obscured():
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
    def process(self, data):
        data = base64.b64decode(data)
        # if hasattr(super(), 'process'):
        data = super().process(data)
        return data
        # return data


class img_ansi_timg(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    def validate(self):
        # There is a python package called timg which provided an executable
        # That's not the one we are aftere here, so check if it is installed
        try:
            import timg  # noqa F401
        except ModuleNotFoundError:
            return super().validate()
        else:
            return False

    def load(self):
        self.cmd = [
            "timg",
            f"-g{self.width}x{self.width}",
            "--compress",
            "-b",
            get_app().bg_color,
            "-pq",
            "--threads=-1",
            "-",
        ]


class img_ansi_catimg(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    def load(self):
        self.cmd = ["catimg", "-w", self.width * 2, "-"]


class img_ansi_icat(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    use_tempfile = True

    def load(self):
        self.cmd = ["icat", "-w", self.width, "--mode", "24bit"]


class ansi_tiv(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    use_tempfile = True

    def load(self):
        self.cmd = ["tiv", "-w", self.width, "-h", self.height]


class img_ansi_timg_py(AnsiImageRenderer, ImageRenderer, PythonRenderMixin):
    module = "timg"

    def process(self, data):
        import timg

        self.image.thumbnail((self.width * 2, self.height * 2))
        # Set transparent colour to terminal background
        if (
            bg_color := get_app().bg_color
            and self.image.mode in ("RGBA", "LA")
            or (self.image.mode == "P" and "transparency" in self.image.info)
        ):
            alpha = self.image.convert("RGBA").getchannel("A")
            bg = Image.new("RGBA", self.image.size, bg_color)
            bg.paste(self.image, mask=alpha)
            self.image = bg
        self.image = self.image.convert("P", palette=Image.ADAPTIVE, colors=16).convert(
            "RGB", palette=Image.ADAPTIVE, colors=16
        )
        data = timg.Ansi24HblockMethod(self.image).to_string()
        return data


class img_ansi_img2unicode_py(AnsiImageRenderer, ImageRenderer, PythonRenderMixin):
    module = "img2unicode"

    def process(self, data):
        from img2unicode import FastQuadDualOptimizer, Renderer

        output = io.StringIO()
        Renderer(
            FastQuadDualOptimizer(), max_w=self.width, max_h=self.height
        ).render_terminal(self.image, output)
        output.seek(0)
        return output.read()


class img_ansi_viu(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    def load(self):
        self.cmd = ["viu", "-w", self.width, "-s", "-"]


class img_ansi_jp2a(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    def load(self):
        self.cmd = ["jp2a", "--color", f"--height={self.height}", "-"]


class img_ansi_img2txt(AnsiImageRenderer, ImageRenderer, SubprocessRenderMixin):
    use_tempfile = True

    def load(self):
        self.cmd = ["img2txt", "-W", self.width, "-H", self.height]


class img_ansi_placeholder(AnsiImageRenderer, ImageRenderer):
    msg = "[Image]"

    def validate(self):
        # This is always an option
        return True

    def process(self, data):
        b = Border
        t = len(self.msg)
        w = max(self.width, t + 4)
        h = max(3, self.height)
        output = b.TOP_LEFT + (b.HORIZONTAL * (w - 2)) + b.TOP_RIGHT + "\n"
        for i in range((h - 3) // 2 + 1):
            output += b.VERTICAL + (" " * (w - 2)) + b.VERTICAL + "\n"
        output += b.VERTICAL + " "
        output += " " * ((self.width - 4 - t) // 2)
        output += self.msg
        output += " " * ((self.width - 4 - t) - (self.width - 4 - t) // 2)
        output += " " + b.VERTICAL + "\n"
        for i in range((h - 3) - ((h - 3) // 2)):
            output += b.VERTICAL + (" " * (w - 2)) + b.VERTICAL + "\n"
        output += b.BOTTOM_LEFT + (b.HORIZONTAL * (w - 2)) + b.BOTTOM_RIGHT
        return output


class SVGRenderer(DataRenderer):
    pass


class svg_librsvg(SVGRenderer, PythonRenderMixin):
    module = "cairosvg"

    def process(self, data):
        import cairosvg

        data = cairosvg.surface.PNGSurface.convert(data, write_to=None)
        data = base64.b64encode(data)
        return ImageRenderer.select().render(
            data, self.width, self.height, self.render_args
        )


class svg_imagemagik(SVGRenderer, SubprocessRenderMixin):
    to_string = False

    def load(self):
        self.cmd = [
            "convert",
            "-",
            "PNG:-",
        ]

    def process(self, data):
        data = super().process(data)
        data = base64.b64encode(data)
        return ImageRenderer.select().render(
            data, self.width, self.height, self.render_args
        )
