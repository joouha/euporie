"""Contains the main class for a notebook file."""

from __future__ import annotations

import copy
import logging
from abc import ABCMeta, abstractmethod
from base64 import standard_b64decode
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING
from functools import partial

import nbformat
from prompt_toolkit.auto_suggest import DummyAutoSuggest
from prompt_toolkit.clipboard.base import ClipboardData
from prompt_toolkit.completion import DummyCompleter
from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
    FloatContainer,
)
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, SimpleLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType, MouseModifier
from prompt_toolkit.widgets import Frame, TextArea
from pygments.lexers import get_lexer_by_name
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.widgets import Box, Label
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.processors import (
    BeforeInput,
    ConditionalProcessor,
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightMatchingBracketProcessor,
    HighlightSelectionProcessor,
)

from euporie.margins import NumberedDiffMargin
from euporie.widgets.cell_outputs import CellOutputArea
from euporie.app.current import get_edit_app as get_app
from euporie.comm.registry import open_comm
from euporie.config import config
from euporie.filters import insert_mode, replace_mode
from euporie.key_binding.bindings.commands import load_command_bindings
from euporie.suggest import KernelAutoSuggest
from euporie.suggest import AppendLineAutoSuggestion, ConditionalAutoSuggestAsync
from euporie.tabs.base import Tab
from euporie.kernel import NotebookKernel, MsgCallbacks
from euporie.utils import parse_path
from euporie.widgets.cell import Cell, CellInputTextArea, InteractiveCell, get_cell_id
from euporie.widgets.decor import FocusedStyle, Line, Pattern
from euporie.widgets.inputs import Select
from euporie.widgets.page import PrintingContainer, ScrollbarControl, ScrollingContainer
from euporie.widgets.pager import Pager
from euporie.completion import KernelCompleter
from euporie.suggest import KernelAutoSuggest

if TYPE_CHECKING:
    from collections.abc import MutableSequence
    from os import PathLike
    from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Tuple, Type

    from prompt_toolkit.auto_suggest import AutoSuggest
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.app.base import EuporieApp
    from euporie.app.edit import EditApp
    from euporie.comm.base import Comm
    from euporie.kernel import NotebookKernel
    from euporie.widgets.cell import PagerState

log = logging.getLogger(__name__)


class Console(Tab):
    """A interactive console container class."""

    def __init__(
        self,
        app: "Optional[EuporieApp]" = None,
    ) -> "None":
        """Create a new :py:class:`KernelNotebook` instance.

        Args:
            app: The euporie application the console tab belongs to
        """
        super().__init__(app=app)

        self.nb = self
        self.kernel = None
        self.lang_info = {}
        self.comms: "Dict[str, Comm]" = {}  # The client-side comm states
        self.execution_count = 0

        self.load_kernel()
        # self.app.post_load_callables.append(self.load_kernel)

        self.container = self.load_container()

    def load_kernel(self) -> "None":
        """Load and start the kernel."""
        self.kernel = NotebookKernel(
            nb=self,
            threaded=True,
            default_callbacks=MsgCallbacks(
                # get_input=self.misc_callback,
                set_execution_count=partial(setattr, self, "execution_count"),
                add_output=self.new_output,
                # clear_output=self.misc_callback,
                # set_metadata=self.misc_callback,
                set_status=lambda status: self.app.invalidate(),
                set_kernel_info=self.set_kernel_info,
                done=self.complete,
            ),
        )
        self.completer = KernelCompleter(self.kernel)
        self.suggester = KernelAutoSuggest(self.kernel)
        self.kernel.start(cb=self.ready, wait=True)

    def ready(self, result: "None" = None) -> "None":
        """Called when the kernel is ready."""
        self.kernel.info()
        self.show_prompt = True
        self.app.invalidate()

    def accept(self, buffer: "Buffer") -> "None":
        """Accept the text in the input box."""
        text = buffer.text
        if text:
            # Re-render the app below the existing output
            self.app._redraw(render_as_done=True)
            self.app._request_absolute_cursor_position()
            # Run the previous entry
            self.kernel.run(text, wait=False)
            # Reset the input
            self.output.json = []
            buffer.reset(append_to_history=True)
            return True
        return False

    def new_output(self, output_json: "Dict[str, Any]") -> "None":
        """Print the previous output and replace it with the new one."""
        self.output.json = self.output.json + [output_json]
        self.app.layout.focus(self.input_box)
        self.app.invalidate()

    def complete(self, content: "Dict" = None) -> "None":
        """Re-show the prompt."""
        log.debug("complete")
        self.app.invalidate()
        pass

    def prompt(self, text: "str") -> "str":
        """Determine what should be displayed in the prompt of the cell."""
        if self.kernel and self.kernel._status == "busy":
            prompt = "*"
        else:
            prompt = str(self.execution_count + 1)
        ft = [
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

    def load_container(self) -> "FloatContainer":
        """Builds the main application layout."""
        self.output = CellOutputArea([], self)

        self.input_box = CellInputTextArea(
            # multiline=False,
            # scrollbar=scroll_input(),
            complete_while_typing=Condition(lambda: config.autocomplete),
            auto_suggest=ConditionalAutoSuggestAsync(
                self.suggester, filter=Condition(lambda: config.autosuggest)
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
            accept_handler=self.accept,
            input_processors=[
                # ConditionalProcessor(
                # HighlightIncrementalSearchProcessor(),
                # filter=is_searching,
                # ),
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
            # search_field=get_app().search_bar,
            # on_text_changed=on_text_changed,
            # on_cursor_position_changed=on_cursor_position_changed,
            # tempfile_suffix=notebook.lang_file_ext,
        )
        self.input_box.buffer.name = "code"
        self.app.focused_element = self.input_box.buffer

        input_prompt = Window(
            FormattedTextControl(partial(self.prompt, "In ")),
            dont_extend_width=True,
            style="class:cell.input.prompt",
        )
        output_prompt = Window(
            FormattedTextControl(partial(self.prompt, "Out")),
            dont_extend_width=True,
            style="class:cell.output.prompt",
        )

        return PrintingContainer(
            [
                ConditionalContainer(
                    HSplit(
                        [
                            VSplit([output_prompt, self.output]),
                        ],
                    ),
                    filter=Condition(lambda: int(bool(self.output.json))),
                ),
                ConditionalContainer(
                    Window(height=1),
                    filter=Condition(lambda: bool(self.execution_count)),
                ),
                # ConditionalContainer(
                VSplit(
                    [
                        input_prompt,
                        self.input_box,
                    ],
                ),
                Window(height=1),
            ],
        )

    def interrupt_kernel(self) -> "None":
        """Interrupt the current `Notebook`'s kernel."""
        assert self.kernel is not None
        self.kernel.interrupt()

    @property
    def kernel_name(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return "python3"
        return self.json.get("metadata", {}).get("kernelspec", {}).get("name")

    @property
    def kernel_display_name(self) -> "str":
        """Return the display name of the kernel defined in the notebook JSON."""
        return (
            self.json.get("metadata", {}).get("kernelspec", {}).get("display_name", "")
        )

    '''
    def reformat(self) -> "None":
        """Reformat all code cells in the notebooks."""
        for cell in self.rendered_cells():
            if cell.cell_type == "code":
                cell.reformat()
    '''

    def set_kernel_info(self, info: "dict") -> "None":
        """Receives and processes kernel metadata."""
        self.lang_info = info.get("language_info", {})

    def comm_open(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Register a new kernel Comm object in the notebook."""
        comm_id = str(content.get("comm_id"))
        self.comms[comm_id] = open_comm(nb=self, content=content, buffers=buffers)

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
