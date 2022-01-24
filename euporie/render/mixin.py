"""Contains mixins for data renderers."""

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
from typing import TYPE_CHECKING

from PIL import Image  # type: ignore

from euporie.app import get_app

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any, Union

__all__ = [
    "DataRendererMixin",
    "Base64Mixin",
    "Base64Mixin",
    "SubprocessRenderMixin",
    "PythonRenderMixin",
]

log = logging.getLogger(__name__)


class DataRendererMixin(metaclass=ABCMeta):
    """Metaclass for DataRenderer Mixins."""

    width: "int"
    height: "int"

    @abstractmethod
    def process(self, data: "Any") -> "Union[str, bytes]":
        """Abstract function which processes cell output data.

        Args:
            data: Cell output data.

        Returns:
            An empty string.

        """
        return ""


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
        log.debug("Running external command `%s`", cmd)
        try:
            output_bytes = subprocess.check_output(cmd, input=data_bytes)  # noqa S603
        except FileNotFoundError:
            log.error("Could not run external command `%s`", cmd)
            output_bytes = b"[Error drawing output]"

        # TODO Log any stderr
        # print(stderr)

        # Clean up any temporary file
        if self.use_tempfile:
            tfile.close()
            os.unlink(tfile.name)

        return output_bytes


class PythonRenderMixin(DataRendererMixin):
    """Mixin for renderers which use external python libraries."""

    modules: "list[str]"

    @classmethod
    def validate(cls) -> "bool":
        """Checks the required python modules are importable."""
        for module in cls.modules:
            try:
                import_module(module)
            except ModuleNotFoundError:
                return False
        return True


class ImageMixin(DataRendererMixin):
    """Mixin for rendering images which calculates the size to render the image."""

    image: "Image"

    def __init__(
        self,
        *args: "Any",
        **kwargs: "Any",
    ) -> "None":
        """Initiate the image renderer.

        Args:
            *args: Arguments to pass to the renderer initiation method.
            **kwargs: Keyword arguments to pass to the renderer initiation method.

        """
        super().__init__(*args, **kwargs)
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
            app = get_app()
            char_px, char_py = app.term_info.cell_size_px
            # Scale image down if it is larger than available width
            pixels_per_col = orig_px / char_px
            # Only down-scale images
            self.scaling_factor = min(1, self.width / pixels_per_col)
            # Pixel & character values need to be integers
            self.px = ceil(orig_px * self.scaling_factor)
            self.py = ceil(orig_py * self.scaling_factor)

            self.width = ceil(self.px / char_px)
            self.height = ceil(self.py / char_py)
        assert self.image is not None
