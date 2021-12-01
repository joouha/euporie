# -*- coding: utf-8 -*-
"""Defines a cell object with input are and rich outputs, and related objects."""
from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Any, Literal

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Completion, indent, unindent
from prompt_toolkit.filters import (
    Condition,
    completion_is_selected,
    has_completions,
    has_selection,
)
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.key_binding.bindings.auto_suggest import load_auto_suggest_bindings
from prompt_toolkit.key_binding.bindings.named_commands import register
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.search import start_search
from prompt_toolkit.widgets import SearchToolbar, TextArea
from pygments.lexers import get_lexer_by_name  # type: ignore

from euporie.box import Border
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.output import Output

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.layout import FocusableElement

    from euporie.notebook import Notebook

log = logging.getLogger(__name__)


@Condition
def cursor_in_leading_ws() -> "bool":
    """Determine if the cursor of the current buffer is in leading whitespace."""
    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


class ClickArea:
    """Any empty widget which focuses `target` when clicked.

    Designed to be used as an overlay for clickable widgets in a FloatContainer.
    """

    def __init__(self, target: "FocusableElement"):
        """Initiate a click area overlay element, which focuses another element when clicked.

        Args:
            target: The element to focus on click.

        """
        self.target = target
        self.window = Window(
            FormattedTextControl(
                self._get_text_fragments,
                focusable=False,
            ),
            dont_extend_width=False,
            dont_extend_height=False,
        )

    def _get_text_fragments(self) -> "StyleAndTextTuples":
        def handler(mouse_event: MouseEvent) -> None:
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                get_app().layout.focus(self.target)

        return [
            # Use a zero width space to avoid moving shifting the remaining line
            # and set it to zero width with the [ZeroWidthEscape] style
            ("class:cell-clickarea [ZeroWidthEscape]", "​", handler),
        ]

    def __pt_container__(self) -> "Container":
        """Return the `ClickArea`'s window with a blank `FormattedTextControl`."""
        return self.window


class Cell:
    """A notebook cell element.

    Contains a transparent clickable overlay, which is not displayed when the cell is focused.
    """

    def __init__(self, index: "int", json: "dict", notebook: "Notebook"):
        """Initiate the cell element."""
        self.index = index
        self.json = json
        self.nb = notebook
        self.rendered = True
        self.editing = False

        self.state = "idle"

        ft = FormattedTextControl(
            Border.TOP_LEFT,
            focusable=True,
            show_cursor=False,
        )
        self.control = Window(ft, width=1, height=0, style=self.border_style)

        self.show_input = Condition(
            lambda: bool(
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
            lambda: bool((self.json.get("cell_type") == "markdown") & ~self.rendered)
        )
        self.autocomplete = Condition(lambda: config.autocomplete)
        self.wrap_input = Condition(lambda: self.json.get("cell_type") == "markdown")
        self.is_editing = Condition(lambda: self.editing)
        self.show_prompt = Condition(lambda: self.cell_type == "code")
        self.is_focused = Condition(lambda: self.focused)
        self.obscured = Condition(lambda: self.nb.is_cell_obscured(self.index))
        self.show_input_line_numbers = Condition(
            lambda: bool(self.nb.line_numbers and self.json.get("cell_type") == "code")
        )

        self.input_box: TextArea
        self.container: FloatContainer
        self.output_box: HSplit

        self.load()

    def load_key_bindings(self) -> "KeyBindingsBase":
        """Loads the key bindings related to cells."""
        kb = KeyBindingsInfo()

        @kb.add(
            "e", filter=~self.is_editing, group="Notebook", desc="Edit cell in $EDITOR"
        )
        async def edit_in_editor(event: "KeyPressEvent") -> "None":
            self.editing = True
            await self.input_box.buffer.open_in_editor()
            exit_edit_mode(event)
            if config.run_after_external_edit:
                self.run_or_render()

        @kb.add(
            "enter",
            filter=~self.is_editing,
            group="Notebook",
            desc="Enter cell edit mode",
        )
        def enter_edit_mode(event: "KeyPressEvent") -> "None":
            self.editing = True
            self.container.modal = True
            get_app().layout.focus(self.input_box)
            self.rendered = False

        @kb.add("escape", group="Notebook", desc="Exit cell edit mode")
        @kb.add(
            "escape", "escape", group="Notebook", desc="Exit cell edit mode quickly"
        )
        def exit_edit_mode(event: "KeyPressEvent") -> "None":
            self.exit_edit_mode()

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
        @kb.add("c-e", group="Notebook", desc="Run cell")
        @kb.add("c-f20")
        def run_or_render(event: "KeyPressEvent") -> "None":
            self.run_or_render(advance=False)

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
        @kb.add("c-r", group="Notebook", desc="Run then select next cell")
        @kb.add("f21")
        def run_then_next(event: "KeyPressEvent") -> "None":
            self.run_or_render(advance=True)

        @kb.add("c-f", filter=self.is_editing, group="Edit Mode", desc="Find")
        def find(event: "KeyPressEvent") -> "None":
            start_search(self.input_box.control)

        @kb.add("c-g", filter=self.is_editing, group="Edit Mode", desc="Find Next")
        def find_next(event: "KeyPressEvent") -> "None":
            search_state = get_app().current_search_state
            cursor_position = self.input_box.buffer.get_search_position(
                search_state, include_current_position=False
            )
            self.input_box.buffer.cursor_position = cursor_position

        @kb.add("c-z", filter=self.is_editing, group="Edit Mode", desc="Undo")
        def undo(event: "KeyPressEvent") -> "None":
            self.input_box.buffer.undo()

        @kb.add("c-d", filter=self.is_editing, group="Edit Mode", desc="Duplicate line")
        def duplicate_line(event: "KeyPressEvent") -> "None":
            buffer = event.current_buffer
            line = buffer.document.current_line
            eol = buffer.document.get_end_of_line_position()
            buffer.cursor_position += eol
            buffer.newline()
            buffer.insert_text(line)
            buffer.cursor_position -= eol

        def move(n: "int", exit_selection: "bool", event: "KeyPressEvent") -> "None":
            buff = event.current_buffer
            if exit_selection:
                buff.exit_selection()
            buff.cursor_position += n

        @kb.add("enter", filter=self.is_editing)
        def new_line(event: "KeyPressEvent") -> "None":
            buffer = event.current_buffer
            buffer.cut_selection()
            pre = buffer.document.text_before_cursor
            buffer.newline()
            if pre.rstrip()[-1:] in (":", "(", "["):
                dent_buffer(event)

        def dent_buffer(event: "KeyPressEvent", un: "bool" = False) -> "None":
            buffer = event.current_buffer
            selection_state = buffer.selection_state
            cursor_position = buffer.cursor_position
            lines = buffer.document.lines

            # Apply indentation to the selected range
            from_, to = map(
                lambda x: buffer.document.translate_index_to_position(x)[0],
                buffer.document.selection_range(),
            )
            dent = unindent if un else indent
            dent(buffer, from_, to + 1, count=event.arg)

            # If there is a selection, indent it and adjust the selection range
            if selection_state:
                change = 4 * (un * -2 + 1)
                # Count how many lines will be affected
                line_count = 0
                for i in range(from_, to + 1):
                    if not un or lines[i][:1] == " ":
                        line_count += 1
                backwards = cursor_position < selection_state.original_cursor_position
                if un and not line_count:
                    buffer.cursor_position = cursor_position
                else:
                    buffer.cursor_position = max(
                        0, cursor_position + change * (1 if backwards else line_count)
                    )
                    selection_state.original_cursor_position = max(
                        0,
                        selection_state.original_cursor_position
                        + change * (line_count if backwards else 1),
                    )

            # Maintain the selection state before indentation
            buffer.selection_state = selection_state

        @kb.add(
            "tab",
            filter=self.is_editing & (cursor_in_leading_ws | has_selection),
            group="Edit Mode",
            desc="Indent",
        )
        def indent_buffer(event: "KeyPressEvent") -> "None":
            dent_buffer(event)

        @kb.add(
            "s-tab",
            filter=self.is_editing & (cursor_in_leading_ws | has_selection),
            group="Edit Mode",
            desc="Unindent",
        )
        def unindent_buffer(event: "KeyPressEvent") -> "None":
            dent_buffer(event, un=True)

        @kb.add("escape", filter=has_completions, eager=True)
        def cancel_completion(event: "KeyPressEvent") -> "None":
            """Cancel a completion with the escape key."""
            event.current_buffer.cancel_completion()

        @kb.add("enter", filter=completion_is_selected)
        def apply_completion(event: "KeyPressEvent") -> "None":
            """Cancel a completion with the escape key."""
            complete_state = event.current_buffer.complete_state
            if complete_state:
                if isinstance(complete_state.current_completion, Completion):
                    event.current_buffer.apply_completion(
                        complete_state.current_completion
                    )

        @kb.add("c-c", filter=self.is_editing, group="Edit Mode", desc="Copy")
        def copy_selection(event: "KeyPressEvent") -> "None":
            data = event.current_buffer.copy_selection()
            get_app().clipboard.set_data(data)

        @kb.add(
            "c-x", filter=self.is_editing, eager=True, group="Edit Mode", desc="Cut"
        )
        def cut_selection(event: "KeyPressEvent") -> "None":
            data = event.current_buffer.cut_selection()
            get_app().clipboard.set_data(data)

        @kb.add("c-v", filter=self.is_editing, group="Edit Mode", desc="Paste")
        def paste_clipboard(event: "KeyPressEvent") -> "None":
            event.current_buffer.paste_clipboard_data(get_app().clipboard.get_data())

        return merge_key_bindings(
            [
                kb,
                ConditionalKeyBindings(load_auto_suggest_bindings(), self.is_editing),
            ]
        )

    def exit_edit_mode(self) -> None:
        """Removes a cell from edit mode."""
        self.editing = False
        self.input = self.input_box.text
        self.nb.dirty = True
        self.container.modal = False
        # give focus back to selected cell (this might have changed!)
        get_app().layout.focus(self.nb.cell.control)

    def run_or_render(self, advance: "bool" = False) -> None:
        """Run code cells, or render markdown cells, optionally advancing.

        Args:
            advance: If True, move to next cell. If True and at the last cell, create a
                new cell at the end of the notebook.

        """
        if advance:
            # Insert a cell if we are at the last cell
            n_cells = len(self.nb.page.children)
            if self.nb.page.selected_index == (n_cells) - 1:
                offset = n_cells - self.nb.page.selected_index
                self.nb.add(offset)
            else:
                self.nb.page.selected_index += 1

        self.exit_edit_mode()
        if self.cell_type == "markdown":
            self.output_box.children = self.rendered_outputs
            self.rendered = True
        elif self.cell_type == "code":
            self.state = "queued"
            # Clear output early
            self.clear_output()
            self.nb.run_cell(self.index, output_cb=self.on_output, cb=self.ran)

    def on_output(self) -> "None":
        """Runs when a message for this cell is recieved from the kernel."""
        # Update the outputs in the visible instance of this cell
        visible_cell = self.nb.get_cell_by_id(self.id)
        if visible_cell:
            visible_cell.output_box.children = visible_cell.rendered_outputs

        # Tell the app that the display needs updating
        get_app().invalidate()

        self.output_box.children = self.rendered_outputs

    def ran(self) -> "None":
        """Callback which runs when the cell has finished running."""
        # Update the outputs in the visible instance of this cell
        self.state = "idle"

    def set_cell_type(self, cell_type: "Literal['markdown','code','raw']") -> "None":
        """Convert the cell to a different cell type.

        Args:
            cell_type: The desired cell type.

        """
        if cell_type == "code":
            self.json.setdefault("execution_count", None)
        self.json["cell_type"] = cell_type
        # self.load()

    def load(self) -> "None":
        """Generates the main container used to represent a notebook cell."""
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
            complete_while_typing=self.autocomplete,
            auto_suggest=self.nb.suggester,
            style="class:cell-input",
        )
        self.input_box.window.cursorline = self.is_editing
        self.input_box.buffer.tempfile_suffix = ".py"

        self.output_box = HSplit(
            self.rendered_outputs,
            style="class:cell-output",
        )

        top_border = VSplit(
            [
                self.control,
                ConditionalContainer(
                    content=fill(
                        char=Border.HORIZONTAL, width=lambda: len(self.prompt), height=1
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
                        content=Window(
                            FormattedTextControl(
                                lambda: self.prompt,
                            ),
                            width=lambda: len(self.prompt),
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
                        content=fill(
                            char=Border.HORIZONTAL, width=lambda: len(self.prompt)
                        ),
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
                        content=Window(
                            FormattedTextControl(
                                lambda: self.prompt,
                            ),
                            width=lambda: len(self.prompt),
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
                    content=fill(
                        char=Border.HORIZONTAL, width=lambda: len(self.prompt)
                    ),
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

    def border_style(self) -> "str":
        """Determines the style of the cell borders, based on the cell state."""
        if self.focused:
            if self.editing:
                return "class:frame.border,cell-border-edit"
            else:
                return "class:frame.border,cell-border-selected"
        else:
            return "class:frame.border,cell-border"

    @property
    def id(self) -> "str":
        """Returns the cell's ID as per the cell JSON."""
        return self.json.get("id", "")

    @property
    def language(self) -> "str":
        """Returns the cell's code language."""
        if self.cell_type == "markdown":
            return "markdown"
        else:
            return self.nb.json.metadata.get("language_info", {}).get("name", "python")

    @property
    def focused(self) -> "bool":
        """Determine if the cell currently has focus."""
        return get_app().layout.has_focus(self.container)

    @property
    def cell_type(self) -> "str":
        """Determine the currrent cell type."""
        return self.json.get("cell_type", "code")

    @property
    def prompt(self) -> "str":
        """Determine what should be displayed in the prompt of the cell."""
        if self.state in ("busy", "queued"):
            prompt = "*"
        else:
            prompt = self.execution_count
        if prompt is None:
            prompt = " "
        if prompt:
            prompt = f"[{prompt}]"
        return prompt

    @property
    def execution_count(self) -> "str":
        """Retrieve the execution count from the cell's JSON."""
        return self.json.get("execution_count", " ")

    @execution_count.setter
    def execution_count(self, count: int) -> "None":
        """Set the execution count in the cell's JSON.

        Args:
            count: The new execution count number.

        """
        self.json["execution_count"] = count

    @property
    def input(self) -> "str":
        """Fetch the cell's contents from the cell's JSON."""
        return self.json.get("source", "")

    @input.setter
    def input(self, value: "str") -> "None":
        """Set the cell's contents in the cell's JSON.

        Args:
            value: The new cell contents text.

        """
        self.json["source"] = value

    def clear_output(self) -> "None":
        """Remove all outputs from the cell."""
        self.json["outputs"] = []
        # self.load()

    @property
    def outputs(self) -> "list[dict[str, Any]]":
        """Retrieve a list of cell outputs from the cell's JSON."""
        if self.cell_type == "markdown":
            return [
                {"data": {"text/x-markdown": self.input}, "output_type": "markdown"}
            ]
        else:
            return self.json.get("outputs", [])

    @property
    def rendered_outputs(self) -> "list[Container]":
        """Generates a list of rendered outputs."""
        rendered_outputs: "list[Container]" = []
        for i, output_json in enumerate(self.outputs):
            rendered_outputs.append(to_container(Output(i, output_json, parent=self)))
        return rendered_outputs

    def __pt_container__(self) -> "Container":
        """Returns the container which represents this cell."""
        return self.container


# The following allow you to move or down a line in a buffer by pressing left or right
# when at the start or end of a line
@register("backward-char")
def backward_char(event: "KeyPressEvent") -> "None":
    """Move back a character, or up a line."""
    event.current_buffer.cursor_position -= event.arg


@register("forward-char")
def forward_char(event: "KeyPressEvent") -> "None":
    """Move forward a character, or down a line."""
    event.current_buffer.cursor_position += event.arg
