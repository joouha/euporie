"""Contains the main class for a notebook file."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, cast

import nbformat
from prompt_toolkit.application.run_in_terminal import in_terminal
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

from euporie.core.commands import add_cmd, get_cmd
from euporie.core.config import add_setting
from euporie.core.filters import (
    at_end_of_buffer,
    buffer_is_code,
    buffer_is_empty,
    kernel_tab_has_focus,
)
from euporie.core.format import format_code
from euporie.core.kernel import MsgCallbacks
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.style import KERNEL_STATUS_REPR
from euporie.core.tabs.base import KernelTab
from euporie.core.validation import KernelValidator
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput
from euporie.core.widgets.page import PrintingContainer
from euporie.core.widgets.pager import PagerState

if TYPE_CHECKING:
    from typing import Any, Callable, Optional, Sequence

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import Float
    from upath import UPath

    from euporie.core.app import BaseApp

log = logging.getLogger(__name__)


class Console(KernelTab):
    """Interactive console.

    An interactive console which connects to a Jupyter kernel.

    """

    def __init__(
        self,
        app: "BaseApp",
        path: "Optional[UPath]" = None,
        use_kernel_history: "bool" = True,
    ) -> "None":
        """Create a new :py:class:`KernelNotebook` instance.

        Args:
            app: The euporie application the console tab belongs to
            path: A file path to open (not used currently)
            use_kernel_history: If :const:`True`, history will be loaded from the kernel
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
        )
        self.kernel_tab = self

        super().__init__(app=app, path=path, use_kernel_history=use_kernel_history)

        self.lang_info: "dict[str, Any]" = {}
        self.execution_count = 0
        self.clear_outputs_on_output = False

        self.json = nbformat.v4.new_notebook()
        self.json["metadata"] = self._metadata

        self.container = self.load_container()

        self.kernel.start(cb=self.kernel_started, wait=False)

        self.app.before_render += self.render_outputs

    async def load_history(self) -> "None":
        """Load kernel history."""
        await super().load_history()
        # Re-run history load for the input-box
        self.input_box.buffer._load_history_task = None
        self.input_box.buffer.load_history_if_not_yet_loaded()

    def close(self, cb: "Optional[Callable]" = None) -> "None":
        """Close the console tab."""
        # Ensure any output no longer appears interactive
        self.live_output.style = "class:disabled"
        # Unregister output renderer
        self.app.before_render -= self.render_outputs
        super().close(cb)

    def clear_output(self, wait: "bool" = False) -> "None":
        """Remove the last output, optionally when new output is generated."""
        if wait:
            self.clear_outputs_on_output = True
        else:
            self.live_output.reset()

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
        # Auto-reformat code
        if self.app.config.autoformat:
            self.reformat()
        # Get the code to run
        text = buffer.text
        # Disable existing output
        self.live_output.style = "class:disabled"
        # Re-render the app and move to below the current output
        self.app.draw()
        # Prevent displayed graphics on terminal being cleaned up (bit of a hack)
        self.app.graphics.clear()
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
        if self.app.config.mouse_support is None:
            self.app.need_mouse_support = False
        # Record the input as a cell in the json
        self.json["cells"].append(
            nbformat.v4.new_code_cell(source=text, execution_count=self.execution_count)
        )
        if (
            self.app.config.max_stored_outputs
            and len(self.json["cells"]) > self.app.config.max_stored_outputs
        ):
            del self.json["cells"][0]

    def new_output(self, output_json: "dict[str, Any]") -> "None":
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
            # Enable mouse support if we have a live output
            if self.app.config.mouse_support is None:
                self.app.need_mouse_support = True
        else:
            # Queue the output json
            self.output.add_output(output_json)
            # Invalidate the app so the output get printed
            self.app.invalidate()

    def render_outputs(self, app: "Application[Any]") -> "None":
        """Request that any unrendered outputs be rendered."""
        if self.output.json:
            self.app.create_background_task(self.async_render_outputs())

    async def async_render_outputs(self) -> "None":
        """Render any unrendered outputs above the application."""
        if self.output.json:
            # Run the output app in the terminal
            async with in_terminal():
                self.app.renderer.render(self.app, self.output_layout, is_done=True)
            # Remove the outputs so they do not get rendered again
            self.output.reset()

    def reset(self) -> "None":
        """Reset the state of the tab."""
        self.live_output.reset()
        if self.app.config.mouse_support is None:
            self.app.need_mouse_support = False

    def complete(self, content: "dict" = None) -> "None":
        """Re-render any changes."""
        self.app.invalidate()

    def prompt(
        self, text: "str", offset: "int" = 0, show_busy: "bool" = False
    ) -> "StyleAndTextTuples":
        """Determine what should be displayed in the prompt of the cell."""
        prompt = str(self.execution_count + offset)
        if show_busy and self.kernel.status in ("busy", "queued"):
            prompt = "*".center(len(prompt))
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

    def load_container(self) -> "HSplit":
        """Builds the main application layout."""
        # Output area

        self.output = CellOutputArea([], parent=self)

        @Condition
        def first_output() -> "bool":
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
            style="class:cell.output.prompt",
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

        def on_cursor_position_changed(buf: "Buffer") -> "None":
            """Respond to cursor movements."""
            # Update contextual help
            if self.app.config.autoinspect and buf.name == "code":
                self.inspect()
            elif (pager := self.app.pager) is not None and pager.visible():
                pager.hide()

        input_kb = KeyBindings()

        @Condition
        def empty() -> "bool":
            from euporie.console.app import get_app

            buffer = get_app().current_buffer
            text = buffer.text
            return not text.strip()

        @Condition
        def not_invalid() -> "bool":
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
        async def on_enter(event: "KeyPressEvent") -> "NotImplementedOrNone":
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
        def _newline(event: "KeyPressEvent") -> "None":
            """Force new line on Shift-Enter."""
            event.current_buffer.newline(copy_margin=not in_paste_mode())

        input_prompt = Window(
            FormattedTextControl(partial(self.prompt, "In ", offset=1)),
            dont_extend_width=True,
            style="class:cell.input.prompt",
            height=1,
        )

        self.input_box = KernelInput(
            kernel_tab=self,
            accept_handler=self.run,
            on_cursor_position_changed=on_cursor_position_changed,
            validator=KernelValidator(self.kernel),
            # validate_while_typing=False,
            enable_history_search=True,
            key_bindings=input_kb,
        )
        self.input_box.buffer.name = "code"

        self.app.focused_element = self.input_box.buffer

        self.stdin_box = StdInput(self)

        self.input_layout = HSplit(
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
            ],
            key_bindings=load_registered_bindings(
                "euporie.console.tabs.console.Console"
            ),
        )

        return self.input_layout

    def accept_stdin(self, buf: "Buffer") -> "bool":
        """Accept the user's input."""
        return True

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
        self.input_box.text = format_code(self.input_box.text, self.app.config)

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
            if prev_state != new_state:
                self.app.pager.state = new_state
                self.app.invalidate()

        assert self.kernel is not None
        self.kernel.inspect(
            code=code,
            cursor_pos=cursor_pos,
            callback=_cb,
        )

    def save(self, path: "UPath" = None) -> "None":
        """Save the console as a notebook."""
        from euporie.core.tabs.notebook import BaseNotebook

        BaseNotebook.save(cast("BaseNotebook", self), path)

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _accept_input() -> "None":
        """Accept the current console input."""
        from euporie.console.app import get_app

        buffer = get_app().current_buffer
        if buffer:
            buffer.validate_and_handle()

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus & ~has_selection & ~buffer_is_empty,
    )
    def _clear_input() -> "None":
        """Clear the console input."""
        from euporie.console.app import get_app

        buffer = get_app().current_buffer
        buffer.reset()

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus,
    )
    def _run_input() -> "None":
        """Run the console input."""
        from euporie.console.app import get_app

        console = get_app().tab
        assert isinstance(console, Console)
        console.run()

    @staticmethod
    @add_cmd(
        filter=buffer_is_code & buffer_has_focus & ~has_selection,
    )
    def _show_contextual_help() -> "None":
        """Displays contextual help."""
        from euporie.console.app import get_app

        console = get_app().tab
        assert isinstance(console, Console)
        console.inspect()

    @staticmethod
    @add_cmd(
        name="cc-interrupt-kernel",
        hidden=True,
        filter=buffer_is_code & buffer_is_empty,
    )
    @add_cmd(
        filter=kernel_tab_has_focus,
    )
    def _interrupt_kernel() -> "None":
        """Interrupt the notebook's kernel."""
        from euporie.console.app import get_app

        if isinstance(kt := get_app().tab, KernelTab):
            kt.interrupt_kernel()

    @staticmethod
    @add_cmd(
        filter=kernel_tab_has_focus,
    )
    def _restart_kernel() -> "None":
        """Restart the notebook's kernel."""
        from euporie.console.app import get_app

        if isinstance(kt := get_app().tab, KernelTab):
            kt.restart_kernel()

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

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.console.tabs.console.Console": {
                "cc-interrupt-kernel": "c-c",
                "show-contextual-help": "s-tab",
            },
            "euporie.console.app.ConsoleApp": {
                "clear-input": "c-c",
                "run-input": ["c-enter", "c-e"],
            },
        }
    )
