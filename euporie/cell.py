# -*- coding: utf-8 -*-
import asyncio
from functools import partial

import nbformat
from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.search import start_search
from prompt_toolkit.widgets import Label, SearchToolbar, TextArea
from pygments.lexers import get_lexer_by_name

from euporie.box import Border
from euporie.keys import KeyBindingsInfo
from euporie.output import Output


class ClickArea:
    """Any empty widget which focuses `target` when clicked.

    Designed to be used as an overlay for clickable widgets in a FloatContainer.
    """

    def __init__(self, target):
        self.target = target
        self.window = Window(
            FormattedTextControl(
                self._get_text_fragments,
                focusable=False,
            ),
            dont_extend_width=False,
            dont_extend_height=False,
        )

    def _get_text_fragments(self) -> StyleAndTextTuples:
        def handler(mouse_event: MouseEvent) -> None:
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                get_app().layout.focus(self.target)

        return [("class:cell-clickarea", "", handler)]

    def __pt_container__(self) -> Container:
        return self.window


class Cell:
    def __init__(self, index, json, notebook):
        self.index = index
        self.json = json
        self.nb = notebook
        self.rendered = True
        self.editing = False
        self._drawing_position = None

        self.state = "idle"

        ft = FormattedTextControl(
            Border.TOP_LEFT,
            focusable=True,
            show_cursor=False,
        )
        self.control = Window(ft, width=1, height=0, style=self.border_style)

        self.show_input = Condition(
            lambda: (
                (self.json.get("cell_type") != "markdown")
                | ((self.json.get("cell_type") == "markdown") & ~self.rendered)
            )
        )
        self.show_output = Condition(
            lambda: (
                (self.json.get("cell_type") != "markdown") & bool(self.outputs)
                | ((self.json.get("cell_type") == "markdown") & self.rendered)
            )
        )
        self.scroll_input = Condition(
            lambda: (self.json.get("cell_type") == "markdown") & ~self.rendered
        )
        self.wrap_input = Condition(lambda: self.json.get("cell_type") == "markdown")
        self.is_editing = Condition(lambda: self.editing)
        self.show_prompt = Condition(lambda: self.cell_type == "code")
        self.is_focused = Condition(lambda: self.focused)
        self.obscured = Condition(
            lambda: (
                self._drawing_position is None
                or (
                    self._drawing_position.top < 0
                    or self._drawing_position.parent_height
                    < self._drawing_position.top + self._drawing_position.height
                )
            )
        )
        self.show_input_line_numbers = Condition(
            lambda: self.nb.line_numbers and self.json.get("cell_type") == "code"
        )

        self.load()

    def load_key_bindings(self):
        kb = KeyBindingsInfo()

        @kb.add(
            "e", filter=~self.is_editing, group="Notebook", desc="Edit cell in $EDITOR"
        )
        async def edit_in_editor(event):
            self.editing = True
            await self.input_box.buffer.open_in_editor()
            exit_edit_mode(event)

        @kb.add(
            "enter",
            filter=~self.is_editing,
            group="Notebook",
            desc="Enter cell edit mode",
        )
        def enter_edit_mode(event):
            self.editing = True
            self.container.modal = True
            get_app().layout.focus(self.input_box)
            self.rendered = False

        @kb.add("escape", group="Notebook", desc="Exit cell edit mode")
        @kb.add(
            "escape", "escape", group="Notebook", desc="Exit cell edit mode quickly"
        )
        def exit_edit_mode(event):
            self.editing = False
            self.input = self.input_box.text
            self.nb.dirty = True
            self.container.modal = False
            # give focus back to selected cell (this might have changed!)
            get_app().layout.focus(self.nb.cell.control)

        @kb.add(
            "escape",
            "[",
            "1",
            "3",
            ";",
            "5",
            "u",
            key_str=("c-enter",),
            group="Notebook",
            desc="Run cell",
        )
        @kb.add("c-r", group="Notebook", desc="Run cell")
        @kb.add("c-f20")
        def run_or_render(event):
            exit_edit_mode(event)
            if self.cell_type == "markdown":
                self.output_box.children = self.rendered_outputs
                self.rendered = True
            elif self.cell_type == "code":
                self.state = "queued"
                self.run()

        @kb.add(
            "escape",
            "[",
            "1",
            "3",
            ";",
            "2",
            "u",
            key_str=("s-enter",),
            group="Notebook",
            desc="Run then select next cell",
        )
        @kb.add("f21")
        def run_then_next(event):
            # Insert a cell if we are at the last cell
            n_cells = len(self.nb.page.children)
            if self.nb.page.selected_index == (n_cells) - 1:
                offset = n_cells - self.nb.page.selected_index
                self.nb.add(offset)
            else:
                self.nb.page.selected_index += 1
            run_or_render(event)

        @kb.add("c-f", filter=self.is_editing, group="Edit Mode", desc="Find")
        def find(event):
            start_search(self.input_box.control)

        @kb.add("c-g", filter=self.is_editing, group="Edit Mode", desc="Find Next")
        def find_next(event):
            search_state = get_app().current_search_state
            cursor_position = self.input_box.buffer.get_search_position(
                search_state, include_current_position=False
            )
            self.input_box.buffer.cursor_position = cursor_position

        @kb.add("c-z", filter=self.is_editing, group="Edit Mode", desc="Undo")
        def undo(event):
            self.input_box.buffer.undo()

        return kb

    def run(self):
        self.clear_output()
        if self.nb.kc:
            # Execute input and wait for responses in kernel thread
            asyncio.run_coroutine_threadsafe(
                # self.nb.kc._async_execute_interactive(
                self._async_execute_interactive(
                    code=self.input,
                    allow_stdin=False,
                    output_hook=self.ran,
                ),
                self.nb.kernel_loop,
            )

    async def _async_execute_interactive(
        self, code, allow_stdin=False, output_hook=None
    ):
        from queue import Empty

        import zmq.asyncio

        if not self.nb.kc.iopub_channel.is_alive():
            raise RuntimeError("IOPub channel must be running to receive output")

        msg_id = self.nb.kc.execute(
            code,
            allow_stdin=False,
        )
        stdin_hook = self.nb.kc._stdin_hook_default

        timeout_ms = None

        poller = zmq.Poller()
        iopub_socket = self.nb.kc.iopub_channel.socket
        poller.register(iopub_socket, zmq.POLLIN)
        stdin_socket = None

        # wait for output and redisplay it
        while True:
            events = dict(poller.poll(timeout_ms))
            if not events:
                raise TimeoutError("Timeout waiting for output")
            if stdin_socket in events:
                req = self.nb.kc.stdin_channel.get_msg(timeout=0)
                stdin_hook(req)
                continue
            if iopub_socket not in events:
                continue

            msg = self.nb.kc.iopub_channel.get_msg(timeout=0)

            if msg["parent_header"].get("msg_id") != msg_id:
                # not from my request
                continue
            output_hook(msg)

            # stop on idle
            if (
                msg["header"]["msg_type"] == "status"
                and msg["content"]["execution_state"] == "idle"
            ):
                break

        # output is done, get the reply
        while True:
            try:
                reply = self.nb.kc.get_shell_msg(timeout=None)
            except Empty as e:
                raise TimeoutError("Timeout waiting for reply") from e
            if reply["parent_header"].get("msg_id") != msg_id:
                # not my reply, someone may have forgotten to retrieve theirs
                continue
            return reply

    def ran(self, msg):
        msg_type = msg.get("header", {}).get("msg_type")

        if msg_type == "status":
            self.state = msg.get("content", {}).get("execution_state")
            self.nb.kernel_status = self.state

        elif msg_type == "execute_input":
            self.json["execution_count"] = msg.get("content", {}).get("execution_count")

        elif msg_type in ("stream", "error", "display_data", "execute_result"):
            self.json["outputs"].append(nbformat.v4.output_from_msg(msg))

        # Update the outputs in the visible instance of this cell
        visible_cell = self.nb.get_cell_by_id(self.id)
        if visible_cell:
            visible_cell.output_box.children = visible_cell.rendered_outputs

        # Tell the app that the display needs updating
        get_app().invalidate()

    def set_cell_type(self, cell_type):
        if cell_type == "code":
            self.json.setdefault("execution_count", None)
        self.json["cell_type"] = cell_type
        self.load()

    def mouse_click(self):
        get_app().layout.focus(self.control)

    def load(self):

        fill = partial(Window, style=self.border_style)

        self.search_control = SearchToolbar()

        self.input_box = TextArea(
            text=self.input,
            # Does not accept conditions
            scrollbar=self.scroll_input(),
            wrap_lines=self.wrap_input,
            # Does not accept conditions
            line_numbers=self.show_input_line_numbers(),
            read_only=~self.is_editing,
            focusable=self.is_editing,
            lexer=DynamicLexer(
                lambda: PygmentsLexer(
                    get_lexer_by_name(self.language).__class__,
                    sync_from_start=False,
                )
                if self.cell_type != "raw"
                else None
            ),
            search_field=self.search_control,
            completer=self.nb.completer,
            complete_while_typing=False,
            style="class:cell-input",
        )
        self.input_box.window.cursorline = self.is_editing

        self.output_box = HSplit(
            self.rendered_outputs,
            style="class:cell-output",
        )

        top_border = VSplit(
            [
                self.control,
                ConditionalContainer(
                    content=fill(
                        char=Border.HORIZONTAL, width=len(self.prompt), height=1
                    ),
                    filter=self.show_prompt,
                ),
                ConditionalContainer(
                    content=fill(width=1, height=1, char=Border.SPLIT_TOP),
                    filter=self.show_prompt,
                ),
                fill(char=Border.HORIZONTAL, height=1),
                fill(width=1, height=1, char=Border.TOP_RIGHT),
            ],
            height=1,
        )
        input_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=Border.VERTICAL),
                    ConditionalContainer(
                        content=Label(
                            self.prompt,
                            width=len(self.prompt),
                            style="class:cell-input-prompt",
                        ),
                        filter=self.show_prompt,
                    ),
                    ConditionalContainer(
                        content=fill(width=1, char=Border.VERTICAL),
                        filter=self.show_prompt,
                    ),
                    HSplit([self.input_box, self.search_control]),
                    fill(width=1, char=Border.VERTICAL),
                ],
            ),
            filter=self.show_input,
        )
        middle_line = ConditionalContainer(
            content=VSplit(
                [
                    fill(width=1, height=1, char=Border.SPLIT_LEFT),
                    ConditionalContainer(
                        content=fill(char=Border.HORIZONTAL, width=len(self.prompt)),
                        filter=self.show_prompt,
                    ),
                    ConditionalContainer(
                        content=fill(width=1, height=1, char=Border.CROSS),
                        filter=self.show_prompt,
                    ),
                    fill(char=Border.HORIZONTAL),
                    fill(width=1, height=1, char=Border.SPLIT_RIGHT),
                ],
                height=1,
            ),
            filter=self.show_input & self.show_output,
        )
        output_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=Border.VERTICAL),
                    ConditionalContainer(
                        content=Label(
                            self.prompt,
                            width=len(self.prompt),
                            style="class:cell-output-prompt",
                        ),
                        filter=self.show_prompt,
                    ),
                    ConditionalContainer(
                        fill(width=1, char=" "), filter=~self.show_prompt
                    ),
                    ConditionalContainer(
                        content=fill(width=1, char=Border.VERTICAL),
                        filter=self.show_prompt,
                    ),
                    self.output_box,
                    ConditionalContainer(
                        fill(width=1, char=" "), filter=~self.show_prompt
                    ),
                    fill(width=1, char=Border.VERTICAL),
                ],
            ),
            filter=self.show_output,
        )
        bottom_border = VSplit(
            [
                fill(width=1, height=1, char=Border.BOTTOM_LEFT),
                ConditionalContainer(
                    content=fill(char=Border.HORIZONTAL, width=len(self.prompt)),
                    filter=self.show_prompt,
                ),
                ConditionalContainer(
                    content=fill(width=1, height=1, char=Border.SPLIT_BOTTOM),
                    filter=self.show_prompt,
                ),
                fill(char=Border.HORIZONTAL),
                fill(width=1, height=1, char=Border.BOTTOM_RIGHT),
            ],
            height=1,
        )

        self.container = FloatContainer(
            content=HSplit(
                [top_border, input_row, middle_line, output_row, bottom_border],
                key_bindings=self.load_key_bindings(),
            ),
            floats=[
                Float(
                    transparent=True,
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    content=ConditionalContainer(
                        ClickArea(self), filter=~self.is_focused
                    ),
                ),
            ],
        )

    def border_style(self):
        if self.focused:
            if self.editing:
                return "class:frame.border,cell-border-edit"
            else:
                return "class:frame.border,cell-border-selected"
        else:
            return "class:frame.border,cell-border"

    @property
    def id(self):
        return self.json.get("id")

    @property
    def language(self):
        if self.cell_type == "markdown":
            return "markdown"
        else:
            return self.nb.json.metadata.get("language_info", {}).get("name", "python")

    @property
    def focused(self):
        return get_app().layout.has_focus(self.container)

    @property
    def cell_type(self):
        return self.json.get("cell_type", "code")

    @property
    def prompt(self):
        if self.state in ("busy", "queued"):
            prompt = "*"
        else:
            prompt = self.json.get("execution_count", "")
        if prompt is None:
            prompt = " "
        if prompt:
            prompt = f"[{prompt}]"
        return prompt

    @property
    def input(self):
        return self.json.get("source", "")

    @input.setter
    def input(self, value):
        self.json["source"] = value

    def clear_output(self):
        self.json["outputs"] = []
        self.load()

    @property
    def outputs(self):
        if self.cell_type == "markdown":
            return [
                {"data": {"text/x-markdown": self.input}, "output_type": "markdown"}
            ]
        else:
            return self.json.get("outputs", [])

    @property
    def rendered_outputs(self):
        rendered_outputs = []
        for i, output_json in enumerate(self.outputs):
            rendered_outputs.append(Output(i, output_json, parent=self))
        return rendered_outputs

    def __pt_container__(self) -> "Container":
        return self.container
