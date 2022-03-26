"""Concerns dumping output."""

import io
import logging
import os
import sys
from typing import TYPE_CHECKING, cast

from prompt_toolkit import renderer
from prompt_toolkit.data_structures import Size
from prompt_toolkit.layout.containers import FloatContainer
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.widgets import HorizontalLine

from euporie.app.base import EuporieApp
from euporie.config import config
from euporie.containers import PrintingContainer
from euporie.notebook import DumpKernelNotebook, DumpNotebook

if TYPE_CHECKING:
    from typing import Any, List, Optional, Sequence, TextIO, Tuple, Type

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.output import Output

    from euporie.notebook import Notebook

log = logging.getLogger(__name__)


class DumpApp(EuporieApp):
    """An application which dumps the layout to the output then exits."""

    notebook_class: "Type[Notebook]" = (
        DumpKernelNotebook if config.run else DumpNotebook
    )

    def __init__(self, **kwargs: "Any") -> "None":
        """Create an app for dumping a prompt-toolkit layout."""
        # Initialise the application
        super().__init__(full_screen=False, **kwargs)
        # We want the app to close when rendering is complete
        self.after_render += self.pre_exit

    def pre_exit(self, app: "Application") -> "None":
        """Close the app after dumping, optionally piping output to a pager."""
        self.exit()
        # Display pager if needed
        if config.page:
            from pydoc import pager

            self.output_file.seek(0)
            data = self.output_file.read()
            pager(data)

    def load_container(self) -> "FloatContainer":
        """Returns a container with all opened tabs."""
        return FloatContainer(
            content=PrintingContainer(self.load_tabs),
            floats=[],
        )

    def load_tabs(self) -> "Sequence[AnyContainer]":
        """Returns the currently opened tabs for the printing container."""
        # Create a horizontal line that takes up the full width of the display
        hr = HorizontalLine()
        hr.window.width = self.output.get_size().columns

        # Add tabs, separated by horizontal lines
        contents: "List[AnyContainer]" = []
        for tab in self.tabs:
            # Wrap each tab in a box so it does not expand beyond its maximum width
            contents.append(tab)
            contents.append(hr)
        # Remove the final horizontal line
        if self.tabs:
            contents.pop()
        return contents

    def load_output(self) -> "Output":
        """Loads the output.

        Depending on the application configuration, will set the output to a file, to
        stdout, or to a temporary file so the output can be displayed in a pager.

        Returns:
            A container for notebook output

        """
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

        # Ensure we do not receive the "Output is not a terminal" message
        Vt100_Output._fds_not_a_terminal.add(self.output_file.fileno())
        # Set environment variable to disable character position requests
        os.environ["PROMPT_TOOLKIT_NO_CPR"] = "1"
        # Create a default output - this detects the terminal type
        # Do not use stderr instead of stdout if stdout is not a tty
        output = create_output(
            cast("TextIO", self.output_file), always_prefer_tty=False
        )
        # Use the width and height of stderr (this gives us the terminal size even if
        # output is being piped to a non-tty)
        setattr(output, "get_size", create_output(stdout=sys.stderr).get_size)
        return output

    def _redraw(self, render_as_done: "bool" = False) -> "None":
        """Ensure the output is drawn once, and the cursor is left after the output."""
        if self.render_counter < 1:
            super()._redraw(render_as_done=True)


# Monkey patch the screen size
_original_output_screen_diff = renderer._output_screen_diff


def _patched_output_screen_diff(
    *args: "Any", **kwargs: "Any"
) -> "Tuple[Point, Optional[str]]":
    """Function used to monkey-patch the renderer to extend the application height."""
    # Remove ZWE from screen
    # from collections import defaultdict
    # args[2].zero_width_escapes = defaultdict(lambda: defaultdict(lambda: ""))

    # Tell the renderer we have one additional column. This is to prevent the use of
    # carriage returns and cursor movements to write the final character on lines,
    # which is something the prompt_toolkit does
    size = kwargs.pop("size")
    kwargs["size"] = Size(9999999, size.columns + 1)
    return _original_output_screen_diff(*args, **kwargs)


renderer._output_screen_diff = _patched_output_screen_diff
