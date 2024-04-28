"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, cast

import nbformat
from prompt_toolkit.buffer import Buffer, ValidationState
from prompt_toolkit.filters.app import (
    buffer_has_focus,
    has_completions,
    has_focus,
    has_selection,
    in_paste_mode,
    renderer_height_is_known,
)
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.commands import add_cmd, get_cmd
from euporie.core.config import add_setting
from euporie.core.diagnostics import Report
from euporie.core.filters import (
    at_end_of_buffer,
    buffer_is_code,
    buffer_is_empty,
    kernel_tab_has_focus,
)
from euporie.core.format import LspFormatter
from euporie.core.kernel import MsgCallbacks
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.layout.print import PrintingContainer
from euporie.core.lsp import LspCell
from euporie.core.style import KERNEL_STATUS_REPR
from euporie.core.tabs.base import KernelTab
from euporie.core.terminal import edit_in_editor
from euporie.core.validation import KernelValidator
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable, Sequence

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import Float

    from euporie.core.app import BaseApp
    from euporie.core.lsp import LspClient

log = logging.getLogger(__name__)


class Console(KernelTab):
    """Interactive console.

    An interactive console which connects to a Jupyter kernel.

    """

    bg_init = False

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
        # Kernel setup
        self._metadata = {}
        self.kernel_name = app.config.kernel_name
        self.allow_stdin = True
        self.default_callbacks = MsgCallbacks(
            get_input=lambda prompt, password: self.stdin_box.get_input(
                prompt, password
            ),
            set_execution_count=partial(setattr, self, "execution_count"),
            add_output=self.new_output,
            clear_output=self.clear_output,
            # set_metadata=self.misc_callback,
            set_status=lambda status: self.app.invalidate(),
            set_kernel_info=self.set_kernel_info,
            done=self.complete,
            dead=self.kernel_died,
            set_next_input=self.set_next_input,
            edit_magic=edit_in_editor,
        )
        self.kernel_tab = self

        # Set tab path as untitled, so LSP servers know the files do not exist on disk
        self._untitled_count += 1
        path = UPath(f"untitled:/console-{self._untitled_count}")

        super().__init__(
            app=app,
            path=path,
            use_kernel_history=use_kernel_history,
            connection_file=app.config.connection_file,
        )

        self.lang_info: dict[str, Any] = {}
        self.execution_count = 0
        self.clear_outputs_on_output = False

        self.json = nbformat.v4.new_notebook()
        self.json["metadata"] = self._metadata

        self.container = self.load_container()

        self.kernel.start(cb=self.kernel_started, wait=False)

        self.app.before_render += self.render_outputs

        self.on_advance = Event(self)

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

    def kernel_died(self) -> None:
        """Call when the kernel dies."""
        log.error("The kernel has died")

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
        completeness_status = self.kernel.is_complete(code, wait=True).get(
            "status", "unknown"
        )
        if (
            not code.strip()
            or completeness_status == "incomplete"
            or (completeness_status == "unknown" and code[-2:] != "\n\n")
        ):
            return False
        return True

    def run(self, buffer: Buffer | None = None) -> None:
        """Run the code in the input box."""
        if buffer is None:
            buffer = self.input_box.buffer
        app = self.app
        # Auto-reformat code
        if app.config.autoformat:
            self.input_box.reformat()
        # Get the code to run
        text = buffer.text
        # Remove any selections from input
        buffer.selection_state = None
        # Disable existing output
        self.live_output.style = "class:disabled"
        # Reset the diagnostics
        self.reports.clear()
        # Move cursor to the start of the input
        buffer.cursor_position = 0
        # Re-render the app and move to below the current output
        original_layout = app.layout
        app.layout = self.input_layout
        app.draw()
        app.layout = original_layout
        # Prevent displayed graphics on terminal being cleaned up (bit of a hack)
        app.graphics.clear()
        # Run the previous entry
        if self.kernel.status == "starting":
            self.kernel_queue.append(partial(self.kernel.run, text, wait=False))
        else:
            self.kernel.run(text, wait=False)
        # Increment this for display purposes until we get the response from the kernel
        self.execution_count += 1
        # Reset the input & output
        buffer.reset(append_to_history=True)
        # Remove any live outputs and disable mouse support
        self.live_output.reset()
        # Record the input as a cell in the json
        self.json["cells"].append(
            nbformat.v4.new_code_cell(source=text, execution_count=self.execution_count)
        )
        if (
            app.config.max_stored_outputs
            and len(self.json["cells"]) > app.config.max_stored_outputs
        ):
            del self.json["cells"][0]
        self.on_advance()

    def new_output(self, output_json: dict[str, Any]) -> None:
        """Print the previous output and replace it with the new one."""
        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.clear_outputs_on_output = False
            # Clear the screen
            get_cmd("clear-screen").run()

        # Add to record
        if self.json["cells"]:
            self.json["cells"][-1]["outputs"].append(output_json)

        # Set output
        if "application/vnd.jupyter.widget-view+json" in output_json.get("data", {}):
            # Use a live output to display widgets
            self.live_output.add_output(output_json)
        else:
            # Queue the output json
            self.output.add_output(output_json)
            # Invalidate the app so the output get printed
            self.app.invalidate()

    def render_outputs(self, app: Application[Any]) -> None:
        """Request that any unrendered outputs be rendered."""
        if self.output.json:
            app = self.app
            original_layout = self.app.layout
            app.layout = self.output_layout
            app.renderer.render(self.app, self.output_layout, is_done=True)
            app.renderer.request_absolute_cursor_position()
            app.layout = original_layout
            # Remove the outputs so they do not get rendered again
            self.output.reset()

    def reset(self) -> None:
        """Reset the state of the tab."""
        from euporie.core.widgets.search import stop_search

        self.live_output.reset()
        stop_search()

    def complete(self, content: dict | None = None) -> None:
        """Re-render any changes."""
        self.app.invalidate()

    def prompt(
        self, text: str, offset: int = 0, show_busy: bool = False
    ) -> StyleAndTextTuples:
        """Determine what should be displayed in the prompt of the cell."""
        prompt = str(self.execution_count + offset)
        if show_busy and self.kernel.status in ("busy", "queued"):
            prompt = "*".center(len(prompt))
        ft: StyleAndTextTuples = [
            ("", f"{text}["),
            ("class:count", prompt),
            ("", "]: "),
        ]
        return ft

    @property
    def language(self) -> str:
        """The language of the current kernel."""
        return self.lang_info.get(
            "name", self.lang_info.get("pygments_lexer", "python")
        )

    def lang_file_ext(self) -> str:
        """Return the file extension for scripts in the notebook's language."""
        return self.lang_info.get("file_extension", ".py")

    def load_container(self) -> HSplit:
        """Build the main application layout."""
        # Output area

        self.output = CellOutputArea([], parent=self)

        @Condition
        def first_output() -> bool:
            """Check if the current outputs contain the first output."""
            if self.output.json:
                for output in self.json["cells"][-1].get("outputs", []):
                    if output in self.live_output.json:
                        continue
                    return output == self.output.json[0]
            return False

        output_prompt = Window(
            FormattedTextControl(partial(self.prompt, "Out", show_busy=False)),
            dont_extend_width=True,
            style="class:cell,output,prompt",
            height=1,
        )
        output_margin = Window(
            char=" ", width=lambda: len(str(self.execution_count)) + 7
        )

        output_area = PrintingContainer(
            [
                ConditionalContainer(
                    Window(height=1, dont_extend_height=True), filter=first_output
                ),
                VSplit(
                    [
                        ConditionalContainer(output_prompt, filter=first_output),
                        ConditionalContainer(output_margin, filter=~first_output),
                        self.output,
                    ]
                ),
            ],
        )
        # We need to ensure the output layout also has the application's floats so that
        # graphics are displayed
        self.output_layout = Layout(
            FloatContainer(
                output_area,
                floats=cast("list[Float]", self.app.graphics),
            )
        )

        # Live output area

        self.live_output = CellOutputArea([], parent=self)

        # Input area

        input_kb = KeyBindings()

        @Condition
        def empty() -> bool:
            from euporie.console.app import get_app

            buffer = get_app().current_buffer
            text = buffer.text
            return not text.strip()

        @Condition
        def not_invalid() -> bool:
            from euporie.console.app import get_app

            buffer = get_app().current_buffer
            return buffer.validation_state != ValidationState.INVALID

        @input_kb.add(
            "enter",
            filter=has_focus("code")
            & ~empty
            & not_invalid
            & at_end_of_buffer
            & ~has_completions,
        )
        async def on_enter(event: KeyPressEvent) -> NotImplementedOrNone:
            """Accept input if the input is valid, otherwise insert a return."""
            buffer = event.current_buffer
            # Accept the buffer if there are 2 blank lines
            accept = buffer.text[-2:] == "\n\n"
            # Also accept if the input is valid
            if not accept:
                accept = buffer.validate(set_cursor=False)
            if accept:
                if buffer.accept_handler:
                    keep_text = buffer.accept_handler(buffer)
                else:
                    keep_text = False
                # buffer.append_to_history()
                if not keep_text:
                    buffer.reset()
                return NotImplemented

            # Process the input as a regular :kbd:`enter` key-press
            event.key_processor.feed(event.key_sequence[0], first=True)
            # Prevent the app getting invalidated
            return None

        @input_kb.add("s-enter")
        def _newline(event: KeyPressEvent) -> None:
            """Force new line on Shift-Enter."""
            event.current_buffer.newline(copy_margin=not in_paste_mode())

        input_prompt = Window(
            FormattedTextControl(partial(self.prompt, "In ", offset=1)),
            dont_extend_width=True,
            style="class:cell,input,prompt",
            height=1,
        )

        def _handler(buffer: Buffer) -> bool:
            self.run(buffer)
            return True

        self.input_box = self._current_input = KernelInput(
            kernel_tab=self,
            completer=self.completer,
            right_margins=[],
            name="code",
            formatters=self.formatters,
            language=lambda: self.language,
            inspector=self.inspector,
            on_text_changed=lambda buf: self.on_change(),
            diagnostics=self.report,
            accept_handler=_handler,
            validator=KernelValidator(self.kernel),
            enable_history_search=True,
            key_bindings=input_kb,
        )
        self.input_box.buffer.name = "code"

        self.app.focused_element = self.input_box.buffer

        self.stdin_box = StdInput(self)
        input_row = [
            # Spacing
            ConditionalContainer(
                Window(height=1, dont_extend_height=True),
                filter=Condition(lambda: self.execution_count > 0)
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
                        input_prompt,
                        self.input_box,
                    ],
                ),
                filter=~self.stdin_box.visible,
            ),
        ]

        self.input_layout = Layout(PrintingContainer(input_row))

        return HSplit(
            [
                ConditionalContainer(
                    HSplit(
                        [
                            Window(height=1, dont_extend_height=True),
                            VSplit([output_margin, self.live_output]),
                        ]
                    ),
                    filter=Condition(lambda: bool(self.live_output.json)),
                ),
                # StdIn
                self.stdin_box,
                ConditionalContainer(
                    Window(height=1, dont_extend_height=True),
                    filter=self.stdin_box.visible,
                ),
                *input_row,
            ],
            key_bindings=load_registered_bindings(
                "euporie.console.tabs.console.Console",
                config=self.app.config,
            ),
        )

    def set_next_input(self, text: str, replace: bool = False) -> None:
        """Set the text for the next prompt."""
        self.input_box.buffer.text = text

    def accept_stdin(self, buf: Buffer) -> bool:
        """Accept the user's input."""
        return True

    def interrupt_kernel(self) -> None:
        """Interrupt the current `Notebook`'s kernel."""
        assert self.kernel is not None
        self.kernel.interrupt()

    def set_kernel_info(self, info: dict) -> None:
        """Receive and processes kernel metadata."""
        self.lang_info = info.get("language_info", {})

    def refresh(self, now: bool = True) -> None:
        """Request the output is refreshed (refresh the whole app)."""
        self.app.invalidate()

    def __pt_status__(
        self,
    ) -> tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]:
        """Generate the formatted text for the statusbar."""
        assert self.kernel is not None
        return (
            [],
            [
                [
                    (
                        "",
                        self.kernel_display_name,
                        # , self._statusbar_kernel_handler)],
                    )
                ],
                KERNEL_STATUS_REPR.get(self.kernel.status, "."),
            ],
        )

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Save the console as a notebook."""
        from euporie.core.tabs.notebook import BaseNotebook

        if path is not None:
            BaseNotebook.save(cast("BaseNotebook", self), path)

    @property
    def path_nb(self) -> Path:
        """Return the virtual path of the console as a notebook."""
        return self.path.with_suffix(".ipynb")

    @property
    def path_cell(self) -> Path:
        """Return the virtual path of the console as a notebook cell."""
        return (self.path_nb / f"cell-{self.execution_count}").with_suffix(
            self.path_nb.suffix
        )

    @property
    def lsp_cell(self) -> LspCell:
        """Return a LSP cell representation of the current input."""
        return LspCell(
            id=str(self.execution_count),
            idx=self.execution_count,
            path=self.path_cell,
            kind="code",
            language=self.language,
            text=self.input_box.text,
            execution_count=self.execution_count,
            metadata={},
        )

    def lsp_open_handler(self, lsp: LspClient) -> None:
        """Tell the LSP we opened a file."""
        if lsp.can_open_nb:
            lsp.open_nb(
                path=self.path_nb, cells=[self.lsp_cell], metadata=self.metadata
            )
        else:
            lsp.open_doc(
                path=self.path,
                language=self.language,
                text=self.current_input.buffer.text,
            )

    def lsp_add_cell(self, lsp: LspClient) -> None:
        """Notify the LSP of a new cell."""
        lsp.change_nb_add(path=self.path_nb, cells=[self.lsp_cell])

    def lsp_change_handler(self, lsp: LspClient) -> None:
        """Tell the LSP server a file has changed."""
        if lsp.can_change_nb:
            lsp.change_nb_edit(path=self.path_nb, cells=[self.lsp_cell])
        else:
            # self.kernel_tab.kernel_lang_file_ext
            lsp.change_doc(
                path=self.path,
                language=self.language,
                text=self.input_box.buffer.text,
            )

    def lsp_before_save_handler(self, lsp: LspClient) -> None:
        """Tell the the LSP we are about to save a document."""
        # Do nothing for notebooks

    def lsp_after_save_handler(self, lsp: LspClient) -> None:
        """Tell the the LSP we saved a document."""

    def lsp_close_handler(self, lsp: LspClient) -> None:
        """Tell the LSP we opened a file."""
        if lsp.can_close_nb:
            lsp.close_nb(path=self.path_nb, cells=[])
        else:
            lsp.close_doc(self.path)

    def lsp_update_diagnostics(self, lsp: LspClient) -> None:
        """Process a new diagnostic report from the LSP."""
        diagnostics = [
            *lsp.reports.pop(self.path.as_uri(), []),
            # *lsp.reports.pop(self.path_nb.as_uri(), []),
            *lsp.reports.pop(self.path_cell.as_uri(), []),
        ]
        self.reports[lsp] = Report.from_lsp(self.input_box.text, diagnostics)
        self.app.invalidate()

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _accept_input() -> None:
        """Accept the current console input."""
        from euporie.console.app import get_app

        buffer = get_app().current_buffer
        if buffer:
            buffer.validate_and_handle()

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus & ~has_selection & ~buffer_is_empty,
    )
    def _clear_input() -> None:
        """Clear the console input."""
        from euporie.console.app import get_app

        buffer = get_app().current_buffer
        buffer.reset()

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus,
    )
    def _run_input() -> None:
        """Run the console input."""
        from euporie.console.app import get_app

        console = get_app().tab
        assert isinstance(console, Console)
        console.run()

    @staticmethod
    @add_cmd(
        name="cc-interrupt-kernel",
        hidden=True,
        filter=buffer_is_code & buffer_is_empty,
    )
    @add_cmd(filter=kernel_tab_has_focus)
    def _interrupt_kernel() -> None:
        """Interrupt the notebook's kernel."""
        from euporie.console.app import get_app

        if isinstance(kt := get_app().tab, KernelTab):
            kt.interrupt_kernel()

    @staticmethod
    @add_cmd(filter=kernel_tab_has_focus)
    def _restart_kernel() -> None:
        """Restart the notebook's kernel."""
        from euporie.console.app import get_app

        if isinstance(kt := get_app().tab, KernelTab):
            kt.restart_kernel()

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_is_empty,
        hidden=True,
        description="Signals the end of the input, causing the console to exit.",
    )
    def _end_of_file(event: KeyPressEvent) -> None:
        """Exit when Control-D has been pressed."""
        event.app.exit(exception=EOFError)

    @staticmethod
    @add_cmd()
    def _clear_screen() -> None:
        """Clear the screen and the previous output."""
        from euporie.console.app import get_app

        app = get_app()
        tab = app.tab
        app.renderer.clear()
        if isinstance(tab, Console):
            tab.reset()
            app.layout.focus(tab.input_box)

    # ################################### Settings ####################################

    add_setting(
        name="max_stored_outputs",
        flags=["--max-stored-outputs"],
        type_=int,
        help_="The number of inputs / outputs to store in an in-memory notebook",
        default=100,
        schema={
            "minimum": 0,
        },
        description="""
            Defines the maximum number of executed "cells" to store in case the console
            session is saved to a file or converted into a notebook.
        """,
    )

    add_setting(
        name="connection_file",
        flags=["--connection-file", "--kernel-connection-file"],
        type_=UPath,
        help_="Attempt to connect to an existing kernel using a JSON connection info file",
        default=None,
        description="""
            If the file does not exist, kernel connection information will be written
            to the file path provided.

            If the file exists, kernel connection info will be read from the file,
            allowing euporie to connect to existing kernels.
        """,
    )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.console.tabs.console.Console": {
                "clear-input": ["c-c", "<sigint>"],
                "cc-interrupt-kernel": ["c-c", "<sigint>"],
                "run-input": ["c-enter", "c-e"],
                "end-of-file": "c-d",
                "clear-screen": "c-l",
            },
            "euporie.console.app.ConsoleApp": {},
        }
    )
