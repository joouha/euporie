# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import asyncio
import io
import logging
import sys
from typing import IO, TYPE_CHECKING, Any, Callable, Optional, TextIO, Union, cast

from prompt_toolkit import renderer
from prompt_toolkit.application import Application
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.widgets import Box, HorizontalLine

from euporie.config import config

if TYPE_CHECKING:
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.output import Output

log = logging.getLogger(__name__)

_original_output_screen_diff = renderer._output_screen_diff


def _patched_output_screen_diff(
    *args: "Any", **kwargs: "Any"
) -> "tuple[Point, Optional[str]]":

    # Remove ZWE from screen
    # from collections import defaultdict
    # args[2].zero_width_escapes = defaultdict(lambda: defaultdict(lambda: ""))

    # Tell the renderer we have one additional column. This is to prevent the use of carriage
    # returns and cursor movements to write the final character on lines.
    size = kwargs.pop("size")
    kwargs["size"] = Size(99999, size.columns + 1)
    return _original_output_screen_diff(*args, **kwargs)


class DumpMixin:
    """Provides user interface."""

    # Properties from `App` referred to here
    pre_run: "list[Callable]"
    files: "list[AnyContainer]"
    close_file: "Callable"
    exit: "Callable"
    output: "Output"
    out_file: "IO[str]"

    drawn = False

    def _redraw(self, render_as_done: "bool" = False) -> "None":
        """Ensure the output is drawn once, and the cursor is left after the output."""
        if not self.drawn:
            cast("Application", super())._redraw(render_as_done=True)
            self.drawn = True

    def setup(self) -> "None":
        """Patch the renderer and output to print files longer than the screen."""
        # Patch the renderer to extend the output height
        renderer._output_screen_diff = _patched_output_screen_diff

        if config.page and sys.stdout.isatty():
            # Use a temporary file as display output if we are going to page the output
            from tempfile import TemporaryFile

            self.out_file = TemporaryFile("w+")

        else:
            if config.page:
                log.warning("Cannot page output because standard output is not a TTY")
            # If we are not paging output, determine when to print it
            if config.dump_file is None or str(config.dump_file) in (
                "-",
                "/dev/stdout",
            ):
                self.out_file = sys.stdout
            elif str(config.dump_file) == "/dev/stderr":
                self.out_file = sys.stderr
            else:
                try:
                    self.out_file = open(config.dump_file, "w+")
                except (
                    FileNotFoundError,
                    PermissionError,
                    io.UnsupportedOperation,
                ) as error:
                    log.error(error)
                    log.error(
                        f"Output file `{config.dump_file}` cannot be opened. "
                        "Standard output will be used."
                    )
                    self.out_file = sys.stdout

        # Ensure we do not recieve the "Output is not a terminal" message
        Vt100_Output._fds_not_a_terminal.add(self.out_file.fileno())
        # Do not use stderr instead of stdout if stdout is not a tty
        self.out_file = cast("TextIO", self.out_file)
        self.output = create_output(self.out_file, always_prefer_tty=False)

        # Use the width and height of stderr (this gives us the terminal size even if
        # output is being piped to a non-tty)
        # if hasattr(self.output, '_get_size'):
        setattr(self.output, "get_size", create_output(stdout=sys.stderr).get_size)

        # Disable character position requests when dumping output to stop extra output
        # This also speeds things up as we do not need to wait for the response
        # Ignore typing here as mypy does not understand __class__
        class DumpingOutput(self.output.__class__):  # type: ignore
            # Disable character position requests when dumping output
            responds_to_cpr = False

        # Patch the output to prevent CPR detection
        self.output.__class__ = DumpingOutput

        # Set pre-run commands
        self.pre_run.append(self.post_dump)

    def post_dump(self) -> "None":
        """Close all files and exit the app immediately when dumping files."""
        # Close all the file immediately
        for file in self.files:
            self.close_file(file)

        # Queue exiting the application
        asyncio.get_event_loop().call_soon(self.pre_exit)

    def pre_exit(self) -> "None":
        """Close the app after dumping file, optionally piping output to a pager."""
        # Display pager
        if config.page:
            from pydoc import pager

            self.out_file.seek(0)
            data = self.out_file.read()
            pager(data)

        if self.out_file is not sys.stdout:
            self.out_file.close()

        # Close the application
        self.exit()

    def layout_container(self) -> "AnyContainer":
        """Returns a container with all opened files."""
        from euporie.scroll import PrintingContainer

        # Create a horizontal line that takes up the full width of the display
        hr = HorizontalLine()
        hr.window.width = self.output.get_size().columns

        # Add files, separated by horizontal lines
        contents: "list[Union[Callable, AnyContainer]]" = []
        for file in self.files:
            # Wrap each file in a box so it does not expand beyond its maximum width
            contents.append(Box(file))
            contents.append(hr)
        # Remove the final horizontal line
        if self.files:
            contents.pop()
        return Box(PrintingContainer(contents))

    def cpr_not_supported_callback(self) -> "None":
        """Hide messages about cursor position requrests."""
        pass
