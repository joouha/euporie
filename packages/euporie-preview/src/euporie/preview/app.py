"""Concern dumping output."""

from __future__ import annotations

import io
import logging
import os
import sys
from functools import partial
from typing import TYPE_CHECKING, ClassVar, cast

from apptk.application.current import get_app
from apptk.io import PseudoTTY
from apptk.layout.containers import DynamicContainer, FloatContainer, Window
from apptk.output.defaults import create_output
from apptk.output.vt100 import Vt100_Output

from euporie.core import settings as core_settings
from euporie.core.app.app import BaseApp
from euporie.preview import settings as preview_settings
from euporie.preview.panes import PreviewNotebook

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, TextIO

    from apptk.application.application import _AppResult
    from apptk.layout.containers import Float
    from apptk.output import Output

    from euporie.core.config._setting import Setting
    from euporie.core.panes.base import Pane

log = logging.getLogger(__name__)


class PreviewApp(BaseApp):
    """Preview app.

    Preview notebook files in the terminal.

    Outputs a formatted notebook file. The formatted output will be written to
    the the output file path given by `output_file` (the standard output by
    default).

    """

    name = "preview"

    states: ClassVar[list[Setting]] = [
        *BaseApp.states,
    ]

    settings: ClassVar[list[Setting]] = [
        *BaseApp.settings,
        # Appearance
        core_settings.show_cell_borders,
        core_settings.max_notebook_width,
        core_settings.expand,
        # Preview-specific
        preview_settings.output_file,
        preview_settings.page,
        preview_settings.run,
        preview_settings.save,
        preview_settings.show_filenames,
        preview_settings.cell_start,
        preview_settings.cell_stop,
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Create an app for dumping a prompt-toolkit layout."""
        # Set default arguments
        kwargs.setdefault("title", "euporie-preview")
        kwargs.setdefault("leave_graphics", True)
        kwargs.setdefault("full_screen", False)
        kwargs.setdefault("max_render_postpone_time", 0)
        kwargs.setdefault("min_redraw_interval", 0)
        kwargs.setdefault("extend_renderer_height", True)
        kwargs.setdefault("enable_page_navigation_bindings", False)
        kwargs.setdefault("output", self.load_output())
        # Adjust options if we are paging output
        if self.config.page:
            kwargs.setdefault("set_title", False)
            kwargs.setdefault("extend_renderer_width", True)
        # Initialise the application
        super().__init__(**kwargs)
        # We want the app to close when rendering is complete
        # self.after_render += self.pre_exit
        # Do not load any key bindings
        self.bindings_to_load.append("euporie.preview.app:PreviewApp")
        # Select the first tab after files are opened
        self.pre_run_callables.append(partial(setattr, self, "tab_idx", 0))

    def get_file_tab(self, path: Path) -> type[Pane]:
        """Return the tab to use for a file path."""
        return PreviewNotebook

    def open_file(
        self,
        path: Path,
        read_only: bool = False,
        tab_class: type[Pane] | None = None,
    ) -> None:
        """Open a file synchronously, without showing a loading placeholder.

        The preview app renders directly to the terminal, so showing a
        transient "Loading…" placeholder pane would leave stray output. We
        therefore resolve the path and create the real tab immediately.

        Args:
            path: The file path of the file to open.
            read_only: If true, the file should be opened read-only.
            tab_class: The tab type to use, or ``None`` to determine it.
        """
        from apptk.path import parse_path

        ppath = parse_path(path, resolve=True)
        resolved_class = tab_class or self.get_file_tab(ppath)
        if resolved_class is None:
            log.error("Unable to display file %s", path)
            return
        tab = resolved_class(self, ppath)
        self.add_tab(tab)
        self.focused_element = tab
        self.tab_idx = len(self.panes) - 1

    def exit(
        self,
        result: _AppResult | None = None,
        exception: BaseException | type[BaseException] | None = None,
        style: str = "",
    ) -> None:
        """Optionally pipe the output to a pager on exit."""
        # Display pager if needed
        if self.config.page:
            from pydoc import pager

            output_file = getattr(self.output, "output_file")  # noqa: B009
            if output_file is not None:
                output_file.seek(0)
                data = output_file.read()
                pager(data)
        if exception is not None:
            super().exit(exception=exception, style=style)
        elif result is not None:
            super().exit(result=result, style=style)
        else:
            super().exit()

    def load_container(self) -> FloatContainer:
        """Return a container with all opened tabs."""
        return FloatContainer(
            DynamicContainer(lambda: self.pane or Window()),
            floats=cast("list[Float]", self.floats),
        )

    def cleanup_closed_tab(self, tab: Pane) -> None:
        """Exit if all tabs are closed."""
        super().cleanup_closed_tab(tab)
        if not self.panes:
            self._is_running = False
            self.exit()
        self.draw(render_as_done=True)

    @classmethod
    def load_output(cls) -> Output:
        """Load the output.

        Depending on the application configuration, will set the output to a file, to
        stdout, or to a temporary file so the output can be displayed in a pager.

        Returns:
            A container for notebook output

        """
        output_file: TextIO
        if cls.config.page:
            # Use a temporary file as display output if we are going to page the output
            from tempfile import TemporaryFile

            output_file = TemporaryFile("w+")  # noqa: SIM115
            # Make this file look like a tty so we get colorful output
            output_file = cast("TextIO", PseudoTTY(output_file, isatty=True))

        else:
            # If we are not paging output, determine where to print it
            if cls.config.output_file is None or str(cls.config.output_file) in (
                "-",
                "/dev/stdout",
            ):
                output_file = sys.stdout
            elif str(cls.config.output_file) == "/dev/stderr":
                output_file = sys.stderr
            else:
                try:
                    output_file = cls.config.output_file.open("w+")
                except (
                    FileNotFoundError,
                    PermissionError,
                    io.UnsupportedOperation,
                ) as error:
                    log.error(error)
                    log.error(
                        "Output file `%s` cannot be opened. "
                        "Standard output will be used.",
                        cls.config.output_file,
                    )
                    output_file = sys.stdout

            # Make the output look like a TTY if color-depth has been configured
            if not output_file.isatty() and cls.config.color_depth is not None:
                output_file = cast(
                    "TextIO",
                    PseudoTTY(
                        output_file,
                        isatty=True,
                    ),
                )

        # Ensure we do not receive the "Output is not a terminal" message
        Vt100_Output._fds_not_a_terminal.add(output_file.fileno())
        # Set environment variable to disable character position requests
        os.environ["PROMPT_TOOLKIT_NO_CPR"] = "1"
        # Create a default output - this detects the terminal type
        # Do not use stderr instead of stdout if stdout is not a tty
        output = create_output(cast("TextIO", output_file), always_prefer_tty=False)

        # Use the width and height of stderr (this gives us the terminal size even if
        # output is being piped to a non-tty)
        setattr(  # noqa B010
            output, "get_size", create_output(stdout=sys.stderr).get_size
        )
        # Attach the output file to the output in case we need to page it
        setattr(output, "output_file", output_file)  # noqa B010

        return output

    def _redraw(self, render_as_done: bool = False) -> None:
        """Ensure the output is always rendered as done."""
        # import time
        # time.sleep(0.1)
        super()._redraw(render_as_done=True)

    def _update_invalidate_events(self) -> None:
        """Do nothing, as we don't need invalidation events for the preview app."""


def get_preview_app() -> PreviewApp:
    """Get the current application."""
    return cast("PreviewApp", get_app())
