"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, cast

from prompt_toolkit.filters.app import (
    renderer_height_is_known,
)
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout

from euporie.core.commands import get_cmd
from euporie.core.format import LspFormatter
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.layout.print import PrintingContainer
from euporie.core.nbformat import new_code_cell, new_output
from euporie.core.tabs.console import BaseConsole
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import Container, Float

    from euporie.core.app.app import BaseApp
    from euporie.core.lsp import LspClient
    from euporie.core.nbformat import NotebookNode

log = logging.getLogger(__name__)


class Console(BaseConsole):
    """Interactive console.

    An interactive console which connects to a Jupyter kernel.

    """

    live_output: CellOutputArea
    input_box: KernelInput
    stdin_box: StdInput

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
        super().__init__(
            app=app,
            path=path,
            use_kernel_history=use_kernel_history,
            connection_file=app.config.connection_file,
        )

        self.render_queue: list[dict[str, Any]] = []
        self.last_rendered: NotebookNode | None = None

        self.container = self.load_container()

        self.app.before_render += self.render_outputs

    async def load_lsps(self) -> None:
        """Load the LSP clients."""
        await super().load_lsps()

        for lsp in self.lsps:
            advance_handler = partial(lambda lsp, tab: self.lsp_add_cell(lsp), lsp)
            self.on_advance += advance_handler

            formatter = LspFormatter(lsp, self.path_cell)
            self.formatters.append(formatter)

            # Remove hooks if the LSP exits
            def lsp_unload(lsp: LspClient) -> None:
                self.on_advance -= advance_handler  # noqa: B023
                if formatter in self.completers:  # noqa: B023
                    self.formatters.remove(formatter)  # noqa: B023

            lsp.on_exit += lsp_unload

    async def load_history(self) -> None:
        """Load kernel history."""
        await super().load_history()
        # Re-run history load for the input-box
        self.input_box.buffer._load_history_task = None
        self.input_box.buffer.load_history_if_not_yet_loaded()

    def close(self, cb: Callable | None = None) -> None:
        """Close the console tab."""
        # Ensure any output no longer appears interactive
        self.live_output.style = "class:disabled"
        # Unregister output renderer
        self.app.before_render -= self.render_outputs
        super().close(cb)

    def clear_output(self, wait: bool = False) -> None:
        """Remove the last output, optionally when new output is generated."""
        if wait:
            self.clear_outputs_on_output = True
        else:
            self.live_output.reset()

    def validate_input(self, code: str) -> bool:
        """Determine if the entered code is ready to run."""
        assert self.kernel is not None
        completeness_status = self.kernel.is_complete(code).get("status", "unknown")
        return not (
            not code.strip()
            or completeness_status == "incomplete"
            or (completeness_status == "unknown" and code[-2:] != "\n\n")
        )

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
        # Disable existing output
        # self.live_output.style = "class:disabled"
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

    def new_input(
        self, input_json: dict[str, Any], own: bool, force: bool = False
    ) -> None:
        """Create new cell inputs in response to kernel ``execute_input`` messages."""
        # Skip our own inputs when relayed from the kernel
        # We render them immediately when they are run to avoid delays in the UI
        if own and not force:
            return

        app = self.app
        if not own and not app.config.show_remote_inputs:
            return

        self.flush_live_output()

        # Record the input as a cell in the json
        cell_json = new_code_cell(
            source=input_json["code"],
            execution_count=input_json.get("execution_count", self.execution_count),
        )
        self.render_queue.append(cell_json)
        self.json["cells"].append(cell_json)
        if (
            app.config.max_stored_outputs
            and len(self.json["cells"]) > app.config.max_stored_outputs
        ):
            del self.json["cells"][0]

        # Invalidate the app so the new input gets printed
        app.invalidate()

    def new_output(self, output_json: dict[str, Any], own: bool) -> None:
        """Print the previous output and replace it with the new one."""
        if not own and not self.app.config.show_remote_outputs:
            return

        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.clear_outputs_on_output = False
            # Clear the screen
            get_cmd("clear-screen").run()

        # If there is no cell in the virtual notebook, add an empty cell
        if not self.json["cells"]:
            self.json["cells"].append(
                new_code_cell(execution_count=self.execution_count)
            )
        cell = self.json.cells[-1]

        # If there is no code cell in the render queue, add a dummy cell with no input
        if cell not in self.render_queue:
            # Add to end of previous cell in virtual notebook
            # cell["outputs"].append(output_json)
            # Create virtual cell
            cell = new_code_cell(id=cell.id, execution_count=self.execution_count)
            self.render_queue.append(cell)

        # Add widgets to the live output
        if output_json.get("output_type") == "stream":
            # Use live output to enable emulation of carriage returns
            text = output_json.get("text", "")
            tail = ""
            _text, _, _tail = text.rpartition("\n")
            if "\r" in _tail:  # or "\x1b[" in _tail:
                text, tail = _text, _tail
            if text:
                # Partially Flush live output streams
                cell["outputs"].extend(self.live_output.json)
                self.live_output.reset()
                output_json["text"] = text
                cell["outputs"].append(output_json)
            if tail:
                self.live_output.add_output(new_output(**{**output_json, "text": tail}))
        else:
            if "application/vnd.jupyter.widget-view+json" in output_json.get(
                "data", {}
            ):
                self.live_output.add_output(output_json)
            else:
                cell["outputs"].append(output_json)

        # Invalidate the app so the output get printed
        self.app.invalidate()

    def flush_live_output(self) -> None:
        """Flush any active live outputs to the terminal."""
        if self.live_output.json:
            self.render_queue.append(
                new_code_cell(
                    execution_count=None,
                    outputs=self.live_output.json[:],
                ),
            )
            self.live_output.reset()

    def render_outputs(self, app: Application[Any]) -> None:
        """Request that any unrendered outputs be rendered."""
        # Check for unrendered cells or new output

        # Clear the render queue so it does not get rendered again
        render_queue = list(self.render_queue)
        self.render_queue.clear()

        if render_queue:
            # Render the echo layout with any new cells / outputs
            app = self.app
            original_layout = self.app.layout
            new_layout = self.echo_layout(render_queue)
            app.layout = new_layout
            app.renderer.render(app, new_layout, is_done=True)
            app.layout = original_layout
            app.renderer.request_absolute_cursor_position()

    def reset(self) -> None:
        """Reset the state of the tab."""
        from euporie.core.bars.search import stop_search

        self.live_output.reset()
        stop_search()

    def lang_file_ext(self) -> str:
        """Return the file extension for scripts in the notebook's language."""
        return self.lang_info.get("file_extension", ".py")

        # Echo area

    def echo_layout(self, render_queue: list) -> Layout:
        """Generate a layout for displaying executed cells."""
        children: list[Container] = []
        height_known = renderer_height_is_known()
        rows_above_layout = self.app.renderer.rows_above_layout if height_known else 1
        json_cells = self.json.cells
        for i, cell in enumerate(render_queue):
            if cell.source:
                # Spacing between cells
                if ((json_cells and cell.id != json_cells[0].id) or i > 0) and (
                    (height_known and rows_above_layout > 0) or not height_known
                ):
                    children.append(Window(height=1, dont_extend_height=True))

                # Cell input
                children.append(
                    VSplit(
                        [
                            Window(
                                FormattedTextControl(
                                    partial(
                                        self.prompt,
                                        "In ",
                                        count=cell.execution_count,
                                    )
                                ),
                                dont_extend_width=True,
                                style="class:cell,input,prompt",
                                height=1,
                            ),
                            KernelInput(
                                text=cell.source,
                                kernel_tab=self,
                                language=lambda: self.language,
                                read_only=True,
                                relative_line_numbers=self.app.config.filters.relative_line_numbers,
                            ),
                        ],
                    ),
                )

            # Outputs
            if outputs := cell.outputs:
                # Add space before an output if last rendered cell did not have outputs
                # or we are rendering a new output
                if self.last_rendered is None or (
                    self.last_rendered is not None
                    and (
                        not self.last_rendered.outputs
                        or cell.execution_count != self.last_rendered.execution_count
                    )
                ):
                    children.append(
                        Window(
                            height=1,
                            dont_extend_height=True,
                        )
                    )

                def _flush(
                    buffer: list[dict[str, Any]], prompt: AnyFormattedText
                ) -> None:
                    if buffer:
                        children.append(
                            VSplit(
                                [
                                    Window(
                                        FormattedTextControl(prompt),
                                        dont_extend_width=True,
                                        dont_extend_height=True,
                                        style="class:cell,output,prompt",
                                        height=1,
                                    ),
                                    CellOutputArea(
                                        buffer, parent=self, style="class:disabled"
                                    ),
                                ]
                            ),
                        )
                        buffer.clear()

                buffer: list[dict[str, Any]] = []
                # ec = cell.execution_count
                prompt: AnyFormattedText = ""
                next_prompt: AnyFormattedText
                for output in outputs:
                    next_ec = output.get("execution_count")
                    next_prompt = self.prompt("Out", count=next_ec, show_busy=False)
                    if next_prompt != prompt:
                        _flush(buffer, prompt)
                        prompt = next_prompt
                    buffer.append(output)
                _flush(buffer, prompt)

            self.last_rendered = cell

        return Layout(
            FloatContainer(
                PrintingContainer(children),
                floats=cast("list[Float]", self.app.graphics),
            )
        )

    def load_container(self) -> HSplit:
        """Build the main application layout."""
        # Live output area

        self.live_output = CellOutputArea([], parent=self)

        live_output_row = ConditionalContainer(
            HSplit(
                [
                    Window(height=1, dont_extend_height=True),
                    VSplit(
                        [
                            Window(
                                FormattedTextControl(
                                    lambda: self.prompt(
                                        "Out",
                                        count=self.live_output.json[0].get(
                                            "execution_count",
                                        ),
                                    )
                                ),
                                dont_extend_width=True,
                                style="class:cell,output,prompt",
                                height=1,
                            ),
                            self.live_output,
                        ]
                    ),
                ]
            ),
            filter=Condition(lambda: bool(self.live_output.json)),
        )

        # Input area
        self.input_box = self._load_input_box()
        self.app.focused_element = self.input_box.buffer

        self.stdin_box = StdInput(self)
        input_row = [
            # Spacing
            ConditionalContainer(
                Window(height=1, dont_extend_height=True),
                filter=Condition(lambda: len(self.json["cells"]) > 0)
                & (
                    (
                        renderer_height_is_known
                        & Condition(lambda: self.app.renderer.rows_above_layout > 0)
                    )
                    | ~renderer_height_is_known
                ),
            ),
            # Input
            ConditionalContainer(
                VSplit(
                    [
                        Window(
                            FormattedTextControl(
                                lambda: self.prompt(
                                    "In ",
                                    self.execution_count,
                                    offset=1,
                                    show_busy=True,
                                )
                            ),
                            dont_extend_width=True,
                            style="class:cell,input,prompt",
                            height=1,
                        ),
                        self.input_box,
                    ],
                ),
                filter=~self.stdin_box.visible,
            ),
        ]

        return HSplit(
            [
                live_output_row,
                # StdIn
                self.stdin_box,
                ConditionalContainer(
                    Window(height=1, dont_extend_height=True),
                    filter=self.stdin_box.visible,
                ),
                *input_row,
            ],
            key_bindings=load_registered_bindings(
                "euporie.console.tabs.console:Console",
                config=self.app.config,
            ),
        )

    def set_next_input(self, text: str, replace: bool = False) -> None:
        """Set the text for the next prompt."""
        self.input_box.buffer.text = text

    def accept_stdin(self, buf: Buffer) -> bool:
        """Accept the user's input."""
        return True

    def refresh(self, now: bool = True) -> None:
        """Request the output is refreshed (refresh the whole app)."""
        self.app.invalidate()

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Save the console as a notebook."""
        from euporie.core.tabs.notebook import BaseNotebook

        if path is not None:
            BaseNotebook.save(cast("BaseNotebook", self), path)

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.console.tabs.console:Console": {
                "clear-input": ["c-c", "<sigint>"],
                "cc-interrupt-kernel": ["c-c", "<sigint>"],
                "run-input": ["c-enter", "c-e"],
                "end-of-file": "c-d",
                "clear-screen": "c-l",
            },
            "euporie.console.app:ConsoleApp": {},
        }
    )
