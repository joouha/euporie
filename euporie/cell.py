"""Defines a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING

import nbformat  # type: ignore
from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import Condition, has_focus, is_done
from prompt_toolkit.formatted_text import to_formatted_text
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
from prompt_toolkit.layout.margins import ConditionalMargin, NumberedMargin
from prompt_toolkit.layout.processors import ConditionalProcessor
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, SimpleLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from prompt_toolkit.widgets import Frame, Label, SearchToolbar, TextArea
from pygments.lexers import get_lexer_by_name  # type: ignore

from euporie.box import RoundBorder as Border
from euporie.config import config
from euporie.key_binding.bindings.commands import load_command_bindings
from euporie.output import Output
from euporie.suggest import AppendLineAutoSuggestion, ConditionalAutoSuggestAsync

if TYPE_CHECKING:
    from typing import Any, Callable, Literal, Optional, Union

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text.base import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.layout.layout import FocusableElement

    from euporie.notebook import Notebook, TuiNotebook

__all__ = [
    "get_cell_id",
    "Cell",
    "InteractiveCell",
    "ClickArea",
    "CellStdinTextArea",
    "CellInputTextArea",
]

log = logging.getLogger(__name__)


def get_cell_id(cell_json: "dict") -> "str":
    """Returns the cell ID field defined in a cell JSON object.

    If no cell ID is defined (as per ```:mod:`nbformat`<4.5``), then one is generated
    and added to the cell.

    Args:
        cell_json: The cell's JSON object as a python dictionary

    Returns:
        The ID string

    """
    cell_id = cell_json.get("id", "")
    # Assign a cell id if missing
    if not cell_id:
        cell_json["id"] = cell_id = nbformat.v4.new_code_cell().get("id")
    return cell_id


class Cell:
    """A notebook cell element.

    Contains a transparent clickable overlay, which is not displayed when the cell is focused.
    """

    container: "FloatContainer"

    def __init__(self, index: "int", json: "dict", notebook: "Notebook"):
        """Initiate the cell element.

        Args:
            index: The position of this cell in the notebook
            json: A refernce to the cell's json object
            notebook: The notebook instance this cell belongs to

        """
        self.container: "Container"

        self.index = index
        self.json = json
        self.nb: "Notebook" = notebook
        self.rendered = True

        self.state = "idle"

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
        self.autosuggest = Condition(lambda: config.autosuggest)
        self.wrap_input = Condition(lambda: self.json.get("cell_type") == "markdown")
        self.show_prompt = Condition(lambda: self.cell_type == "code")
        self.is_focused = Condition(lambda: self.focused)
        self.is_code = Condition(lambda: self.json.get("cell_type") == "code")
        self.show_input_line_numbers = Condition(
            lambda: config.line_numbers & self.is_code()
        )
        self.obscured = Condition(lambda: False)
        self._asking_input = False
        self.asking_input = Condition(lambda: self._asking_input)

        # Generates the main container used to represent a notebook cell

        self.search_control = SearchToolbar()
        self.input_box = CellInputTextArea(self)

        ft = FormattedTextControl(
            Border.TOP_LEFT,
            focusable=True,
            show_cursor=False,
        )
        self.control = Window(ft, width=1, height=0, style=self.border_style)

        fill = partial(Window, style=self.border_style)

        self.input_box = CellInputTextArea(self)

        # Create textbox for standard input
        self.stdin_prompt = Label(">", dont_extend_width=True, style="bold")
        self.stdin_box = CellStdinTextArea(
            multiline=False,
            # accept_handler=self.send_input,
            accept_handler=None,
            focus_on_click=True,
        )

        self.output_box = HSplit(
            self.render_outputs(),
            style="class:cell.output",
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
                            style="class:cell.input.prompt",
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
                            style="class:cell.output.prompt",
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
                    HSplit(
                        [
                            self.output_box,
                            ConditionalContainer(
                                Frame(
                                    VSplit(
                                        [
                                            self.stdin_prompt,
                                            Label(" ", dont_extend_width=True),
                                            self.stdin_box,
                                        ]
                                    ),
                                ),
                                filter=self.asking_input,
                            ),
                        ]
                    ),
                    ConditionalContainer(
                        fill(width=1, char=" "), filter=~self.show_prompt
                    ),
                    fill(width=1, char=Border.VERTICAL),
                ],
            ),
            filter=self.show_output | self.asking_input,
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
                key_bindings=load_command_bindings("cell"),
            ),
            floats=[
                Float(
                    transparent=True,
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    content=ConditionalContainer(
                        ClickArea(
                            self,
                            Border.TOP_LEFT,
                            style=self.border_style,
                        ),
                        filter=~self.is_focused,
                    ),
                ),
            ],
        )

    def on_output(self) -> "None":
        """Runs when a message for this cell is recieved from the kernel."""
        # Set the outputs
        self.output_box.children = self.render_outputs()
        # Tell the app that the display needs updating
        get_app().invalidate()

    def exit_edit_mode(self) -> "None":
        """Removes a cell from edit mode."""
        pass

    def ran(self, cell_json: "Optional[dict]" = None) -> "None":
        """Callback which runs when the cell has finished running."""
        self.state = "idle"

    def set_cell_type(
        self, cell_type: "Literal['markdown','code','raw']", clear: "bool" = False
    ) -> "None":
        """Convert the cell to a different cell type.

        Args:
            cell_type: The desired cell type.
            clear: If True, cell outputs will be cleared

        """
        if clear:
            self.clear_output()
        if cell_type == "code":
            self.json.setdefault("execution_count", None)
        if cell_type == "markdown" and "execution_count" in self.json:
            del self.json["execution_count"]
        self.json["cell_type"] = cell_type
        self.output_box.children = self.render_outputs()

    def border_style(self) -> "str":
        """Determines the style of the cell borders, based on the cell state."""
        if not config.dump:
            if self.focused:
                if has_focus(self.input_box.buffer)():
                    return "class:cell.border.edit"
                else:
                    return "class:cell.border.selected"
        if config.show_cell_borders:
            return "class:cell.border"
        else:
            return "class:cell.border.hidden"

    @property
    def id(self) -> "str":
        """Returns the cell's ID as per the cell JSON."""
        return get_cell_id(self.json)

    @property
    def language(self) -> "str":
        """Returns the cell's code language."""
        if self.cell_type == "markdown":
            return "markdown"
        elif self.cell_type == "code":
            lang_info = self.nb.json.metadata.get("language_info", {})
            return lang_info.get("name", lang_info.get("pygments_lexer", "python"))
        else:
            return "raw"

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
            prompt = self.execution_count or " "
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
        if "outputs" in self.json:
            del self.json["outputs"]

    @property
    def outputs(self) -> "list[dict[str, Any]]":
        """Retrieve a list of cell outputs from the cell's JSON."""
        if self.cell_type == "markdown":
            return [
                {"data": {"text/x-markdown": self.input}, "output_type": "markdown"}
            ]
        else:
            return self.json.setdefault("outputs", [])

    # @property
    def render_outputs(self) -> "list[Container]":
        """Generates a list of rendered outputs."""
        rendered_outputs: "list[Container]" = []
        for i, output_json in enumerate(self.outputs):
            rendered_outputs.append(to_container(Output(i, output_json, parent=self)))
        return rendered_outputs

    def run_or_render(
        self,
        buffer: "Optional[Buffer]" = None,
        advance: "bool" = False,
        insert: "bool" = False,
    ) -> "bool":
        """Placeholder function for running the cell.

        Args:
            buffer: Unused parameter, required when accepting the contents of a cell's
                input buffer
            advance: Has no affect
            insert: Has no affect

        Returns:
            Always returns True

        """
        return True

    def __pt_container__(self) -> "Container":
        """Returns the container which represents this cell."""
        return self.container


class InteractiveCell(Cell):
    """An interactive notebook cell."""

    def __init__(self, index: "int", json: "dict", notebook: "TuiNotebook") -> "None":
        """Initiate the interactive cell element.

        Args:
            index: The position of this cell in the notebook
            json: A refernce to the cell's json object
            notebook: The notebook instance this cell belongs to

        """
        super().__init__(index, json, notebook)
        # Pytype need this re-defining...
        self.nb: "TuiNotebook" = notebook
        self.obscured = Condition(lambda: self.nb.is_cell_obscured(self.index))
        self.stdin_event = asyncio.Event()

    async def edit_in_editor(self) -> "None":
        """Edit the cell in $EDITOR."""
        self.exit_edit_mode()
        await self.input_box.buffer.open_in_editor(
            validate_and_handle=config.run_after_external_edit
        )

    def enter_edit_mode(self) -> "None":
        """Set the cell to edit mode."""
        # self.container.modal = True
        get_app().layout.focus(self.input_box)
        self.rendered = False

    def exit_edit_mode(self) -> "None":
        """Removes a cell from edit mode."""
        # self.input = self.input_box.text
        # self.nb.dirty = True
        # Give focus back to selected cell (this might have changed e.g. if doing a run
        # then select the next cell)
        get_app().layout.focus(self.nb.cell.control)

    def run_or_render(
        self,
        buffer: "Optional[Buffer]" = None,
        advance: "bool" = False,
        insert: "bool" = False,
    ) -> "bool":
        """Run code cells, or render markdown cells, optionally advancing.

        Args:
            buffer: Unused parameter, required when accepting the contents of a cell's
                input buffer
            advance: If True, move to next cell. If True and at the last cell, create a
                new cell at the end of the notebook.
            insert: If True, add a new empty cell below the current cell and select it.

        Returns:
            Always return True

        """
        self.exit_edit_mode()

        n_cells = len(self.nb.json["cells"])

        # Insert a cell if we are at the last cell
        if insert or (advance and self.nb.page.selected_index == (n_cells) - 1):
            self.nb.add(self.index + 1)
        elif advance:
            self.nb.page.selected_index += 1

        if self.cell_type == "markdown":
            self.output_box.children = self.render_outputs()
            self.rendered = True

        elif self.cell_type == "code":
            self.state = "queued"
            self.nb.run_cell(self)

        return True

    def get_input(
        self,
        send: "Callable[[str], Any]",
        prompt: "str" = "Please enter a value:",
        password: "bool" = False,
    ) -> "None":
        """Prompts the user for input and sends the result to the kernel."""
        # Remeber what was focused before
        layout = get_app().layout
        focused = layout.current_control
        # Show and focus the input box
        self._asking_input = True
        layout.focus(self.stdin_box)
        self.stdin_prompt.text = prompt
        self.stdin_box.password = password

        def _send_input(buf: "Buffer") -> "bool":
            """Send the input to the kernel and hide the input box."""
            send(buf.text)
            # Cleanup
            self._asking_input = False
            get_app().layout.focus(self)
            self.stdin_box.text = ""
            if focused in layout.find_all_controls():
                try:
                    layout.focus(focused)
                except ValueError:
                    pass
            return True

        self.stdin_box.accept_handler = _send_input


class CellInputTextArea(TextArea):
    """A customized text area for the cell input."""

    def __init__(self, cell: "Cell", *args: "Any", **kwargs: "Any") -> "None":
        """Initiate the cell input box."""
        self.cell = cell

        kwargs["text"] = cell.input
        kwargs["focus_on_click"] = True
        kwargs["focusable"] = True
        kwargs["scrollbar"] = cell.scroll_input()
        kwargs["wrap_lines"] = cell.wrap_input
        kwargs["lexer"] = DynamicLexer(
            lambda: (
                PygmentsLexer(
                    get_lexer_by_name(cell.language).__class__,
                    sync_from_start=False,
                )
                if cell.cell_type != "raw"
                else SimpleLexer()
            )
        )
        kwargs["search_field"] = cell.search_control
        kwargs["completer"] = cell.nb.completer
        kwargs["complete_while_typing"] = cell.autocomplete & cell.is_code
        kwargs["auto_suggest"] = ConditionalAutoSuggestAsync(
            cell.nb.suggester, filter=cell.is_code & cell.autosuggest
        )
        kwargs["style"] = "class:cell.input"
        kwargs["accept_handler"] = self.cell.run_or_render

        super().__init__(*args, **kwargs)

        self.buffer.tempfile_suffix = self.cell.nb.lang_file_ext
        self.buffer.on_text_changed = Event(self.buffer, self.text_changed)

        # Replace the autosuggest processor
        # Skip type checking as PT should use "("Optional[Sequence[Processor]]"
        # instead of "Optional[List[Processor]]"
        # TODO make a PR for this
        self.control.input_processors[0] = ConditionalProcessor(  # type: ignore
            AppendLineAutoSuggestion(),
            has_focus(self.buffer) & ~is_done,
        )

        # Add configurable line numbers
        self.window.left_margins = [
            ConditionalMargin(
                NumberedMargin(),
                Condition(lambda: config.line_numbers),
            )
        ]
        self.window.cursorline = has_focus(self)

        # TODO - Check for non-shift-mode selection and change it to shift mode
        # buffer.on_cursor_position_changed -> Event

    def text_changed(self, buf: "Buffer") -> "None":
        """Update cell json when the input buffer has been edited."""
        self.cell.input = buf.text
        self.cell.nb.dirty = True


class CellStdinTextArea(TextArea):
    """A modal text area for user input."""

    def __init__(self, *args: "Any", **kwargs: "Any"):
        """Create a cell input text area."""
        self.password = False
        kwargs["password"] = Condition(lambda: self.password)
        super().__init__(*args, **kwargs)

    def is_modal(self) -> "bool":
        """Returns true, so the input is always modal."""
        return True


class ClickArea:
    """Any empty widget which focuses `target` when clicked.

    Designed to be used as an overlay for clickable widgets in a FloatContainer.
    """

    def __init__(
        self,
        target: "FocusableElement",
        text: "AnyFormattedText",
        style: "Union[str, Callable[[], str]]",
    ):
        """Initiate a click area overlay element, which focuses another element when clicked.

        Args:
            target: The element to focus on click.
            text: The formatted text to display in the click overlay
            style: The style to apply to the text

        """
        self.text = text
        self.target = target
        self.style = style
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

        ft = to_formatted_text(
            self.text,
            self.style() if callable(self.style) else self.style,
        )
        return [(style, text, handler) for style, text, *_ in ft]

    def __pt_container__(self) -> "Container":
        """Return the `ClickArea`'s window with a blank `FormattedTextControl`."""
        return self.window
