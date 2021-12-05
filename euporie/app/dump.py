# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import sys
from typing import cast

from prompt_toolkit import renderer
from prompt_toolkit.data_structures import Size
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.widgets import Box, HorizontalLine

from euporie.app.base import BaseApp
from euporie.config import config
from euporie.containers import PrintingContainer

log = logging.getLogger(__name__)


class DumpApp(BaseApp):
    def __init__(self, **kwargs):
        super().__init__(
            full_screen=False,
            notebook_kwargs=dict(
                interactive=False,
                autorun=config.run,
                scroll=False,
            ),
            **kwargs,
        )
        self.pre_run_callables.append(self.post_dump)
        self.rendered = False

    def load_container(self) -> "AnyContainer":
        """Returns a container with all opened tabs."""
        # Create a horizontal line that takes up the full width of the display
        hr = HorizontalLine()
        hr.window.width = self.output.get_size().columns

        # Add tabs, separated by horizontal lines
        contents: "list[Union[Callable, AnyContainer]]" = []
        for tab in self.tabs:
            # Wrap each tab in a box so it does not expand beyond its maximum width
            contents.append(Box(tab))
            contents.append(hr)
        # Remove the final horizontal line
        if self.tabs:
            contents.pop()

        return PrintingContainer(contents)

    def load_output(self):
        """"""
        if config.page and sys.stdout.isatty():
            # Use a temporary file as display output if we are going to page the output
            from tempfile import TemporaryFile

            self.output_file = TemporaryFile("w+")
        else:
            if config.page:
                log.warning("Cannot page output because standard output is not a TTY")
            # If we are not paging output, determine when to print it
            if config.dump_file is None or str(config.dump_file) in (
                "-",
                "/dev/stdout",
            ):
                self.output_file = sys.stdout
            elif str(config.dump_file) == "/dev/stderr":
                self.output_file = sys.stderr
            else:
                try:
                    self.output_file = open(config.dump_file, "w+")
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
                    self.output_file = sys.stdout

        self.output_file = cast("TextIO", self.output_file)
        # Ensure we do not recieve the "Output is not a terminal" message
        Vt100_Output._fds_not_a_terminal.add(self.output_file.fileno())
        # Set environment variable to disable character position requests
        os.environ["PROMPT_TOOLKIT_NO_CPR"] = "1"
        # Create a default output - this detectes the terminal type
        # Do not use stderr instead of stdout if stdout is not a tty
        output = create_output(self.output_file, always_prefer_tty=False)
        # Use the width and height of stderr (this gives us the terminal size even if
        # output is being piped to a non-tty)
        output.get_size = create_output(stdout=sys.stderr).get_size
        return output

    def _redraw(self, render_as_done: "bool" = False) -> "None":
        """Ensure the output is drawn once, and the cursor is left after the output."""
        if not self.rendered:
            super()._redraw(render_as_done=True)
            self.rendered = True

    def post_dump(self):
        """Close all files and exit the app."""
        log.debug("Gathering background tasks")
        asyncio.gather(*self.background_tasks)

        # Close all the files
        for tab in self.tabs:
            self.close_tab(tab)

        self.loop.call_soon(self.pre_exit)

    def pre_exit(self):
        """Close the app after dumping, optionally piping output to a pager."""
        # Display pager if needed
        if config.page:
            from pydoc import pager

            log.debug(self.output_file.fileno())
            self.output_file.seek(0)
            data = self.output_file.read()
            pager(data)

        self.exit()


def _patched_output_screen_diff(
    *args: "Any", **kwargs: "Any"
) -> "tuple[Point, Optional[str]]":

    # Remove ZWE from screen
    # from collections import defaultdict
    # args[2].zero_width_escapes = defaultdict(lambda: defaultdict(lambda: ""))

    # Tell the renderer we have one additional column. This is to prevent the use of
    # carriage returns and cursor movements to write the final character on lines,
    # which is something the prompt_toolkit does
    size = kwargs.pop("size")
    kwargs["size"] = Size(9999999, size.columns + 1)
    return _original_output_screen_diff(*args, **kwargs)


# Monkey patch the screen size
_original_output_screen_diff = renderer._output_screen_diff
renderer._output_screen_diff = _patched_output_screen_diff
