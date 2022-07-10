"""Contains the main class for a notebook file."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, cast

from prompt_toolkit.buffer import Buffer, ValidationState
from prompt_toolkit.filters import (
    Condition,
    buffer_has_focus,
    has_selection,
    is_searching,
)
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.processors import (
    ConditionalProcessor,
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightMatchingBracketProcessor,
    HighlightSelectionProcessor,
)
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer
from prompt_toolkit.validation import Validator
from pygments.lexers import get_lexer_by_name

from euporie.console.app import get_app
from euporie.core.comm.registry import open_comm
from euporie.core.commands import add_cmd
from euporie.core.completion import KernelCompleter
from euporie.core.config import config
from euporie.core.filters import buffer_is_code
from euporie.core.format import format_code
from euporie.core.history import KernelHistory
from euporie.core.kernel import MsgCallbacks, NotebookKernel
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.margins import NumberedDiffMargin
from euporie.core.style import KERNEL_STATUS_REPR
from euporie.core.suggest import ConditionalAutoSuggestAsync, KernelAutoSuggest
from euporie.core.tabs.base import Tab
from euporie.core.widgets.cell import CellInputTextArea
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.page import PrintingContainer  # ScrollingContainer
from euporie.core.widgets.pager import PagerState

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any, Dict, Optional, Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

    from euporie.core.app import EuporieApp
    from euporie.core.comm.base import Comm, CommContainer

log = logging.getLogger(__name__)


class Console(Tab):
    """A interactive console container class."""

    def __init__(
        self,
        app: "Optional[EuporieApp]" = None,
        path: "Optional[PathLike]" = None,
    ) -> "None":
        """Create a new :py:class:`KernelNotebook` instance.

        Args:
            app: The euporie application the console tab belongs to
            path: A file path to open (not used currently)
        """
        super().__init__(app=app)

        self.nb = cast("CommContainer", self)

        self.lang_info: "Dict[str, Any]" = {}
        self.execution_count = 0
        self.first_input = True
        self.clear_outputs_on_output = False

        self.kernel_name = "python3"
        self.kernel: "NotebookKernel" = NotebookKernel(
            nb=self,
            threaded=True,
            default_callbacks=MsgCallbacks(
                # get_input=self.misc_callback,
                set_execution_count=partial(setattr, self, "execution_count"),
                add_output=self.new_output,
                clear_output=self.clear_output,
                # set_metadata=self.misc_callback,
                set_status=lambda status: self.app.invalidate(),
                set_kernel_info=self.set_kernel_info,
                # done=self.complete,
            ),
        )
        self.comms: "Dict[str, Comm]" = {}  # The client-side comm states
        self.app.post_load_callables.append(
            partial(self.kernel.start, cb=self.ready, wait=True)
        )
        self.completer = KernelCompleter(self.kernel)
        self.suggester = KernelAutoSuggest(self.kernel)
        self.history = KernelHistory(self.kernel)

        self.container = self.load_container()

    def clear_output(self, wait: "bool" = False) -> "None":
        """Remove the last output, optionally when new output is generated."""
        if wait:
            self.clear_outputs_on_output = True
        else:
            self.output.reset()

    def ready(self, result: "None" = None) -> "None":
        """Called when the kernel is ready."""
        assert self.kernel is not None
        self.kernel.info()
        self.show_prompt = True
        self.app.invalidate()

    def validate_input(self, code: "str") -> "bool":
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
        else:
            return True

    def run(self, buffer: "Optional[Buffer]" = None) -> "None":
        """Run the code in the input box."""
        if buffer is None:
            buffer = self.input_box.buffer
        text = buffer.text
        # Auto-reformat code
        if config.autoformat:
            self.reformat()
        # Disable existing output
        self.output.style = "class:disabled"
        self.app.redraw()
        # Disable existing output
        # Run the previous entry
        assert self.kernel is not None
        self.kernel.run(text, wait=False)
        # Reset the input & output
        self.output.reset()
        buffer.reset(append_to_history=True)
        self.first_input = False

    def new_output(self, output_json: "Dict[str, Any]") -> "None":
        """Print the previous output and replace it with the new one."""
        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.clear_outputs_on_output = False
            self.output.reset()

        self.output.json = self.output.json + [output_json]
        self.app.layout.focus(self.input_box)
        self.app.invalidate()

    def complete(self, content: "Dict" = None) -> "None":
        """Re-show the prompt."""
        self.app.invalidate()

    def prompt(self, text: "str", offset: "int" = 0) -> "StyleAndTextTuples":
        """Determine what should be displayed in the prompt of the cell."""
        if offset and self.kernel and self.kernel._status == "busy":
            prompt = "*"
        else:
            prompt = str(self.execution_count + offset)
        ft: "StyleAndTextTuples" = [
            ("", f"{text}["),
            ("class:count", prompt),
            ("", "]: "),
        ]
        return ft

    @property
    def language(self) -> "str":
        """The language of the current kernel."""
        return self.lang_info.get(
            "name", self.lang_info.get("pygments_lexer", "python")
        )

    def lang_file_ext(self) -> "str":
        """Return the file extension for scripts in the notebook's language."""
        return self.lang_info.get("file_extension", ".py")

    def load_container(self) -> "PrintingContainer":
        """Builds the main application layout."""
        self.output = CellOutputArea([], parent=self)

        def on_cursor_position_changed(buf: "Buffer") -> "None":
            """Respond to cursor movements."""
            # Update contextual help
            if config.autoinspect and buf.name == "code":
                self.inspect()
            elif (pager := self.app.pager) is not None and pager.visible():
                pager.hide()

        input_kb = KeyBindings()

        @input_kb.add(
            "enter",
            filter=Condition(
                lambda: self.input_box.buffer.validation_state
                != ValidationState.INVALID
            ),
        )
        def on_enter(event: "KeyPressEvent") -> "None":
            """Accept input if the input is valid, otherwise insert a return."""
            buffer = event.current_buffer
            valid = buffer.validate(set_cursor=False)
            # When the validation succeeded, accept the input.
            if valid:
                if buffer.accept_handler:
                    keep_text = buffer.accept_handler(buffer)
                else:
                    keep_text = False
                buffer.append_to_history()
                if not keep_text:
                    buffer.reset()
            else:
                # Process the input as a regular :kbd:`enter` key-press
                event.key_processor.feed(event.key_sequence[0], first=True)

        self.input_box = CellInputTextArea(
            # multiline=False,
            # scrollbar=scroll_input(),
            complete_while_typing=Condition(lambda: config.autocomplete),
            auto_suggest=ConditionalAutoSuggestAsync(
                self.suggester,
                filter=Condition(lambda: config.autosuggest),
            ),
            wrap_lines=False,
            focus_on_click=True,
            focusable=True,
            lexer=DynamicLexer(
                lambda: PygmentsLexer(
                    get_lexer_by_name(self.language).__class__,
                    sync_from_start=False,
                )
            ),
            completer=self.completer,
            style="class:cell.input.box",
            accept_handler=self.run,
            input_processors=[
                ConditionalProcessor(
                    HighlightIncrementalSearchProcessor(),
                    filter=is_searching,
                ),
                HighlightSelectionProcessor(),
                DisplayMultipleCursors(),
                HighlightMatchingBracketProcessor(),
            ],
            left_margins=[
                ConditionalMargin(
                    NumberedDiffMargin(),
                    Condition(lambda: config.line_numbers),
                )
            ],
            search_field=self.app.search_bar,
            on_cursor_position_changed=on_cursor_position_changed,
            # tempfile_suffix=notebook.lang_file_ext,
            key_bindings=input_kb,
            validator=Validator.from_callable(self.validate_input),
            history=self.history,
        )
        self.input_box.buffer.name = "code"
        self.app.focused_element = self.input_box.buffer

        input_prompt = Window(
            FormattedTextControl(partial(self.prompt, "In ", 1)),
            dont_extend_width=True,
            style="class:cell.input.prompt",
        )
        output_prompt = Window(
            FormattedTextControl(partial(self.prompt, "Out")),
            dont_extend_width=True,
            style="class:cell.output.prompt",
        )

        have_previous_output = Condition(lambda: bool(self.output.json))

        return PrintingContainer(
            [
                ConditionalContainer(
                    HSplit(
                        [
                            VSplit([output_prompt, self.output]),
                            Window(height=1),
                        ],
                    ),
                    filter=have_previous_output,
                ),
                VSplit(
                    [
                        input_prompt,
                        self.input_box,
                    ],
                ),
                ConditionalContainer(Window(height=1), filter=self.app.redrawing),
            ],
            key_bindings=load_registered_bindings("tabs.console"),
        )

    def interrupt_kernel(self) -> "None":
        """Interrupt the current `Notebook`'s kernel."""
        assert self.kernel is not None
        self.kernel.interrupt()

    @property
    def kernel_display_name(self) -> "str":
        """Return the display name of the kernel defined in the notebook JSON."""
        if self.kernel and self.kernel.km.kernel_spec:
            return self.kernel.km.kernel_spec.display_name
        return self.kernel_name

    def set_kernel_info(self, info: "dict") -> "None":
        """Receives and processes kernel metadata."""
        self.lang_info = info.get("language_info", {})

    def comm_open(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Register a new kernel Comm object in the notebook."""
        comm_id = str(content.get("comm_id"))
        self.comms[comm_id] = open_comm(
            comm_container=self, content=content, buffers=buffers
        )

    def comm_msg(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Respond to a Comm message from the kernel."""
        comm_id = str(content.get("comm_id"))
        if comm := self.comms.get(comm_id):
            comm.process_data(content.get("data", {}), buffers)

    def comm_close(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Close a notebook Comm."""
        comm_id = content.get("comm_id")
        if comm_id in self.comms:
            del self.comms[comm_id]

    def refresh(self, now: "bool" = True) -> "None":
        """Request the output is refreshed (does nothing)."""
        pass

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Generates the formatted text for the statusbar."""
        assert self.kernel is not None
        return (
            [],
            [
                [
                    (
                        "",
                        self.kernel_display_name
                        # , self._statusbar_kernel_handeler)],
                    )
                ],
                KERNEL_STATUS_REPR.get(self.kernel.status, "."),
            ],
        )

    def reformat(self) -> "None":
        """Reformats the input."""
        self.input_box.text = format_code(self.input_box.text)

    def inspect(self) -> "None":
        """Get contextual help for the current cursor position in the current cell."""
        code = self.input_box.text
        cursor_pos = self.input_box.buffer.cursor_position

        assert self.app.pager is not None

        if self.app.pager.visible() and self.app.pager.state is not None:
            if (
                self.app.pager.state.code == code
                and self.app.pager.state.cursor_pos == cursor_pos
            ):
                self.app.pager.focus()
                return

        def _cb(response: "dict") -> "None":
            assert self.app.pager is not None
            prev_state = self.app.pager.state
            new_state = PagerState(
                code=code,
                cursor_pos=cursor_pos,
                response=response,
            )
            log.debug(response)
            if prev_state != new_state:
                self.app.pager.state = new_state
                self.app.invalidate()

        assert self.kernel is not None
        self.kernel.inspect(
            code=code,
            cursor_pos=cursor_pos,
            callback=_cb,
        )


@add_cmd()
def accept_input() -> "None":
    """Accept the current console input."""
    buffer = get_app().current_buffer
    if buffer:
        buffer.validate_and_handle()


@add_cmd(
    filter=~has_selection,
)
def clear_input() -> "None":
    """Clear the console input."""
    buffer = get_app().current_buffer
    if buffer.name == "code":
        buffer.text = ""


@add_cmd(
    filter=buffer_is_code & buffer_has_focus,
)
def run_input() -> "None":
    """Run the console input."""
    console = get_app().tab
    assert isinstance(console, Console)
    console.run()


@add_cmd(
    filter=buffer_is_code & buffer_has_focus & ~has_selection,
)
def show_contextual_help() -> "None":
    """Displays contextual help."""
    console = get_app().tab
    assert isinstance(console, Console)
    console.inspect()


register_bindings(
    {
        "tabs.console": {
            "run-input": ["c-enter", "s-enter", "c-e"],
            "clear-input": "c-c",
            "show-contextual-help": "s-tab",
        }
    }
)
