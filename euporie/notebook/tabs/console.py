"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Any

from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.border import InsetGrid
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.layout.decor import FocusedStyle
from euporie.core.layout.scroll import ScrollingContainer
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.nbformat import new_code_cell
from euporie.core.tabs.console import BaseConsole
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput
from euporie.core.widgets.layout import Border

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.layout.containers import Container

    from euporie.core.app.app import BaseApp

log = logging.getLogger(__name__)


class Console(BaseConsole):
    """Console tab implementation for the Notebook application."""

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        use_kernel_history: bool = True,
        connection_file: str = "",
    ) -> None:
        """Create a new :py:class:`Console` tab instance.

        Args:
            app: The euporie application the console tab belongs to
            path: A file path to open (not used currently)
            use_kernel_history: If :const:`True`, history will be loaded from the kernel
            connection_file: The connection file of an existing kernel
        """
        self.rendered_containers: list[Container] = []
        self.last_output_area: CellOutputArea | None = None
        super().__init__(
            app=app,
            path=path,
            use_kernel_history=use_kernel_history,
        )
        self.container = self.load_container()

    @property
    def selected_indices(self) -> list[int]:
        """Return a list of the currently selected cell indices."""
        return []

    def load_container(self) -> HSplit:
        """Build the main application layout."""
        self.input_box = self._load_input_box()
        self.stdin_box = StdInput(self)
        self.page = ScrollingContainer(lambda: self.rendered_containers)
        return HSplit(
            [
                VSplit(
                    [
                        Window(width=Dimension(max=1)),
                        self.page,
                        ConditionalContainer(
                            MarginContainer(ScrollbarMargin(), target=self.page),
                            filter=Condition(lambda: self.app.config.show_scroll_bar),
                        ),
                    ]
                ),
                FocusedStyle(self.stdin_box),
                FocusedStyle(
                    Border(
                        self.input_box,
                        border=InsetGrid,
                        style="class:input,text,border",
                    )
                ),
            ]
        )

    @property
    def _scroll_to_bottom(self) -> bool:
        """Check whether the console page should scroll to the bottom.

        Returns:
            True if scrolled to bottom, False otherwise.
        """
        if not self.page.render_info:
            return False
        return (
            # Scroll if already at bottom
            self.page.render_info.vertical_scroll + self.page.render_info.window_height
            == sum(self.page.known_sizes)
            # Scroll on new output
            or sum(self.page.known_sizes) < self.page.render_info.window_height
        )

    def new_input(
        self, input_json: dict[str, Any], own: bool, force: bool = False
    ) -> None:
        """Create new cell inputs in response to kernel ``execute_input`` messages.

        Args:
            input_json: The input data from the kernel message.
            own: Whether this input originated from this console.
            force: Whether to force rendering even if it's our own input.
        """
        # Skip our own inputs when relayed from the kernel
        # We render them immediately when they are run to avoid delays in the UI
        if own and not force:
            return

        app = self.app
        if not own and not app.config.show_remote_inputs:
            return

        # Record the input as a cell in the json
        cell_json = new_code_cell(
            source=input_json["code"],
            execution_count=input_json.get("execution_count", self.execution_count),
        )
        self.json["cells"].append(cell_json)

        # Create input container with prompt and KernelInput
        input_container = VSplit(
            [
                Window(
                    FormattedTextControl(
                        partial(
                            self.prompt,
                            "In ",
                            count=cell_json.execution_count,
                        )
                    ),
                    dont_extend_width=True,
                    style="class:cell,input,prompt",
                    height=1,
                ),
                KernelInput(
                    text=cell_json.source,
                    kernel_tab=self,
                    language=lambda: self.language,
                    read_only=True,
                    relative_line_numbers=self.app.config.filters.relative_line_numbers,
                ),
            ],
        )

        # Add spacing above the new input
        if self.rendered_containers:
            self.rendered_containers.append(Window(height=1, dont_extend_height=True))
        # Add the new input
        self.rendered_containers.append(input_container)

        # Reset last output area since we have a new input
        self.last_output_area = None

        # Update scrolling container to show new child
        self.page.refresh_children = True
        # Scroll to the new cell
        if self._scroll_to_bottom:
            self.page.scroll_to(len(self.rendered_containers) - 1, anchor="bottom")

    def new_output(self, output_json: dict[str, Any], own: bool) -> None:
        """Handle new output from the kernel.

        Args:
            output_json: The output data from the kernel message.
            own: Whether this output originated from this console.
        """
        if not own and not self.app.config.show_remote_outputs:
            return

        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.clear_outputs_on_output = False
            # Clear the screen
            self.rendered_containers.clear()
            self.last_output_area = None

        # If there is no cell in the virtual notebook, add an empty cell
        if not self.json["cells"]:
            self.json["cells"].append(
                new_code_cell(execution_count=self.execution_count)
            )
        cell = self.json.cells[-1]

        # If we don't have a last output area, create a new one
        if self.last_output_area is None:
            # Add spacing before output
            if self.rendered_containers:
                self.rendered_containers.append(
                    Window(height=1, dont_extend_height=True)
                )

            # Create new output area
            self.last_output_area = CellOutputArea([], parent=self)

            output_container = VSplit(
                [
                    Window(
                        FormattedTextControl(
                            partial(
                                self.prompt,
                                "Out",
                                count=cell.execution_count,
                            )
                        ),
                        dont_extend_width=True,
                        style="class:cell,output,prompt",
                        height=1,
                    ),
                    self.last_output_area,
                ]
            )
            self.rendered_containers.append(output_container)

        # Add output to the last output area
        cell["outputs"].append(output_json)
        self.last_output_area.add_output(output_json, own)

        # Update scrolling container to show new child
        self.page.refresh_children = True
        # Scroll to the last container if scrolled to bottom of screen
        if self._scroll_to_bottom:
            self.page.scroll_to(len(self.rendered_containers) - 1, anchor="bottom")

    def refresh_cell(self, cell: Any) -> None:
        """Trigger the refresh of a notebook cell."""

    def refresh(self, now: bool = True) -> None:
        """Refresh the console display."""
        self.page.reset()

    def clear_output(self, wait: bool = False) -> None:
        """Remove all cells from history.

        Args:
            wait: If True, clear output when new output is generated.
        """
        self.json["cells"].clear()
        self.rendered_containers.clear()
        self.last_output_area = None

    def run(self, buffer: Buffer | None = None) -> None:
        """Run the code in the input box."""
        if buffer is None:
            buffer = self.input_box.buffer
        app = self.app
        # Auto-reformat code
        if app.config.autoformat:
            self.input_box.reformat()
        # # Get the code to run
        text = buffer.text
        # # Remove any selections from input
        buffer.selection_state = None
        # Reset the diagnostics
        self.reports.clear()
        # Increment this for display purposes until we get the response from the kernel
        self.execution_count += 1
        # Move cursor to the start of the input
        buffer.cursor_position = 0
        # Render input
        self.new_input({"code": text}, own=True, force=True)
        # Run the previous entry
        if self.kernel.status == "starting":
            self.kernel_queue.append(partial(self.kernel.run, text, wait=False))
        else:
            self.kernel.run(text, wait=False)
        # Reset the input & output
        buffer.reset(append_to_history=True)
        self.on_advance()

    def set_next_input(self, text: str, replace: bool = False) -> None:
        """Set the text for the next prompt."""
        self.input_box.buffer.text = text
