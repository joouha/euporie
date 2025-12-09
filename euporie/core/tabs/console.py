"""Contains the Console tab base class."""

from __future__ import annotations

import logging
from abc import abstractmethod
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.buffer import Buffer, ValidationState
from prompt_toolkit.filters.app import (
    has_completions,
    has_focus,
    in_paste_mode,
)
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.commands import get_cmd
from euporie.core.diagnostics import Report
from euporie.core.filters import (
    at_end_of_buffer,
)
from euporie.core.io import edit_in_editor
from euporie.core.kernel.base import MsgCallbacks
from euporie.core.lsp import LspCell
from euporie.core.nbformat import new_notebook
from euporie.core.style import KERNEL_STATUS_REPR
from euporie.core.tabs.kernel import KernelTab
from euporie.core.validation import KernelValidator
from euporie.core.widgets.inputs import KernelInput, StdInput

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.app.app import BaseApp
    from euporie.core.lsp import LspClient

log = logging.getLogger(__name__)


class BaseConsole(KernelTab):
    """Base class for Consoles.

    Provides common functionality for console implementations, including
    input validation, code execution, and kernel interaction.
    """

    execution_count: int
    input_box: KernelInput
    stdin_box: StdInput

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        use_kernel_history: bool = True,
        connection_file: Path | None = None,
    ) -> None:
        """Initialize the base console."""
        # Kernel setup
        self._metadata = {}
        self.kernel_name = app.config.kernel_name
        self.allow_stdin = True
        self.default_callbacks = MsgCallbacks(
            get_input=lambda prompt, password: self.stdin_box.get_input(
                prompt, password
            ),
            set_execution_count=partial(setattr, self, "execution_count"),
            add_input=self.new_input,
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
            connection_file=connection_file,
        )
        self.lang_info: dict[str, Any] = {}
        self.clear_outputs_on_output = False

        self.json = new_notebook()
        self.json["metadata"] = self._metadata
        self.on_advance = Event(self)
        self.execution_count = 0

    @property
    def title(self) -> str:
        """Return the tab title."""
        return self.path.name

    def _load_input_box(self) -> KernelInput:
        """Load the input box and it's associated key-bindings and handlers."""
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

        def _handler(buffer: Buffer) -> bool:
            self.run(buffer)
            return True

        input_box = self._current_input = KernelInput(
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
            validator=KernelValidator(lambda: self.kernel),
            enable_history_search=True,
            key_bindings=input_kb,
            dont_extend_height=True,
            relative_line_numbers=self.app.config.filters.relative_line_numbers,
        )
        input_box.buffer.name = "code"
        return input_box

    def complete(self, content: dict | None = None) -> None:
        """Re-render any changes."""
        self.app.invalidate()

    def post_init_kernel(self) -> None:
        """Start the kernel after if has been loaded."""
        super().post_init_kernel()

        # Start kernel
        if self.kernel._status == "stopped":
            self.kernel.start(cb=self.kernel_started, wait=False)

    def prompt(
        self,
        text: str,
        count: int | None = None,
        offset: int = 0,
        show_busy: bool = False,
    ) -> StyleAndTextTuples:
        """Determine what should be displayed in the prompt of the cell."""
        if count is None:
            return [("", " " * (len(text) + 4 + len(str(self.execution_count))))]
        prompt = str(count + offset)
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

    @abstractmethod
    def refresh(self, now: bool = True) -> None:
        """Request the output is refreshed (refresh the whole app)."""

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

    @abstractmethod
    def run(self, buffer: Buffer | None = None) -> None:
        """Run the code in the input box.

        Args:
            buffer: The buffer containing the code to run. If None, uses the
                current input buffer.
        """

    @abstractmethod
    def new_input(
        self, input_json: dict[str, Any], own: bool, force: bool = False
    ) -> None:
        """Create new cell inputs in response to kernel ``execute_input`` messages.

        Args:
            input_json: The input data from the kernel message.
            own: Whether this input originated from this console.
            force: Whether to force rendering even if it's our own input.
        """

    @abstractmethod
    def new_output(self, output_json: dict[str, Any], own: bool) -> None:
        """Handle new output from the kernel.

        Args:
            output_json: The output data from the kernel message.
            own: Whether this output originated from this console.
        """

    @abstractmethod
    def clear_output(self, wait: bool = False) -> None:
        """Remove the last output, optionally when new output is generated.

        Args:
            wait: If True, clear output when new output is generated.
        """

    @abstractmethod
    def set_next_input(self, text: str, replace: bool = False) -> None:
        """Set the text for the next prompt.

        Args:
            text: The text to set in the input.
            replace: Whether to replace existing text.
        """

    def interrupt_kernel(self) -> None:
        """Interrupt the current `Notebook`'s kernel."""
        assert self.kernel is not None
        self.kernel.interrupt()

    def set_kernel_info(self, info: dict) -> None:
        """Receive and process kernel metadata.

        Args:
            info: Kernel information dictionary.
        """
        self.lang_info = info.get("language_info", {})

    def validate_input(self, code: str) -> bool:
        """Determine if the entered code is ready to run.

        Args:
            code: The code to validate.

        Returns:
            True if the code is complete and ready to execute.
        """
        assert self.kernel is not None
        completeness_status = self.kernel.is_complete(code).get("status", "unknown")
        return not (
            not code.strip()
            or completeness_status == "incomplete"
            or (completeness_status == "unknown" and code[-2:] != "\n\n")
        )

    def lang_file_ext(self) -> str:
        """Return the file extension for scripts in the notebook's language.

        Returns:
            The file extension including the leading dot.
        """
        if hasattr(self, "lang_info"):
            return self.lang_info.get("file_extension", ".py")
        return ".py"

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

    def _statusbar_kernel_handler(self, event: MouseEvent) -> NotImplementedOrNone:
        """Event handler for kernel name field in statusbar."""
        if event.event_type == MouseEventType.MOUSE_UP:
            get_cmd("change-kernel").run()
            return None
        else:
            return NotImplemented

    def __pt_status__(
        self,
    ) -> tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]:
        """Generate the formatted text for the statusbar."""
        assert self.kernel is not None
        return (
            [],
            [
                [("", self.kernel_display_name, self._statusbar_kernel_handler)],
                KERNEL_STATUS_REPR.get(self.kernel.status, "."),
            ],
        )
