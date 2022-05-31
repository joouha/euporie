"""Defines a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, NamedTuple

import nbformat
from prompt_toolkit.filters import Condition, has_focus, is_done, is_searching
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    HSplit,
    VSplit,
    Window,
    to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.processors import (
    BeforeInput,
    ConditionalProcessor,
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightMatchingBracketProcessor,
    HighlightSelectionProcessor,
)
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, SimpleLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType, MouseModifier
from prompt_toolkit.widgets import Frame, TextArea
from pygments.lexers import get_lexer_by_name

from euporie.app.current import get_edit_app as get_app
from euporie.border import Invisible, Thick, Thin
from euporie.config import config
from euporie.filters import multiple_cells_selected
from euporie.format import format_code
from euporie.margins import NumberedDiffMargin
from euporie.suggest import AppendLineAutoSuggestion, ConditionalAutoSuggestAsync
from euporie.widgets.cell_outputs import CellOutputArea

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition

    from euporie.tabs.notebook import EditNotebook, Notebook
    from euporie.widgets.page import ChildRenderInfo


log = logging.getLogger(__name__)


def get_cell_id(cell_json: "dict") -> "str":
    """Return the cell ID field defined in a cell JSON object.

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
        kwargs["completer"] = cell.nb.completer
        kwargs["complete_while_typing"] = cell.autocomplete & cell.is_code
        kwargs["auto_suggest"] = ConditionalAutoSuggestAsync(
            cell.nb.suggester, filter=cell.is_code & cell.autosuggest
        )
        kwargs["style"] = "class:cell.input.box"
        kwargs["accept_handler"] = self.cell.run_or_render
        kwargs["input_processors"] = [
            ConditionalProcessor(
                HighlightIncrementalSearchProcessor(),
                filter=is_searching,
            ),
            HighlightSelectionProcessor(),
            DisplayMultipleCursors(),
            HighlightMatchingBracketProcessor(),
        ]
        kwargs["search_field"] = get_app().search_bar

        super().__init__(*args, **kwargs)

        self.control.include_default_input_processors = False

        self.buffer.tempfile_suffix = self.cell.nb.lang_file_ext
        self.buffer.on_text_changed += self.on_text_changed
        self.buffer.on_cursor_position_changed += self.on_cursor_position_changed

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
                NumberedDiffMargin(),
                Condition(lambda: config.line_numbers),
            )
        ]
        self.window.cursorline = has_focus(self)

        self.has_focus = has_focus(self.buffer)

    def on_text_changed(self, buf: "Buffer") -> "None":
        """Update cell json when the input buffer has been edited."""
        self.cell._set_input(buf.text)
        self.cell.nb.dirty = True

    def on_cursor_position_changed(self, buf: "Buffer") -> "None":
        """Respond to cursor movements."""
        from euporie.tabs.notebook import EditNotebook

        # Update contextual help
        if config.autoinspect and self.cell.is_code():
            self.cell.inspect()
        elif self.cell.nb.pager_visible():
            self.cell.nb.hide_pager()

        # Tell the scrolling container to scroll the cursor into view on the next render
        assert isinstance(self.cell.nb, EditNotebook)
        self.cell.nb.page.scroll_to_cursor = True


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


class ClickToFocus(Container):
    """Selects a cell when clicked, passing through mouse events."""

    def __init__(
        self,
        cell: "Cell",
        body: "AnyContainer",
    ) -> "None":
        """Create a new instance of the widget.

        Args:
            cell: The cell to select on click
            body: The container to act on
        """
        self.cell = cell
        self.body = body

    def reset(self) -> "None":
        """Reset the wrapped container."""
        to_container(self.body).reset()

    def preferred_width(self, max_available_width: "int") -> "Dimension":
        """Return the wrapped container's preferred width."""
        return to_container(self.body).preferred_width(max_available_width)

    def preferred_height(
        self, width: "int", max_available_height: "int"
    ) -> "Dimension":
        """Return the wrapped container's preferred height."""
        return to_container(self.body).preferred_height(width, max_available_height)

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
    ) -> "None":
        """Draw the wrapped container with the additional style."""
        output = to_container(self.body).write_to_screen(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
            z_index,
        )

        mouse_handler_wrappers = {}

        def _wrap_mouse_handler(
            handler: "Callable",
        ) -> "Callable[[MouseEvent], object]":
            if handler not in mouse_handler_wrappers:

                def wrapped_mouse_handler(
                    mouse_event: "MouseEvent",
                ) -> "NotImplementedOrNone":

                    if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                        # Use a set intersection
                        if mouse_event.modifiers & {
                            MouseModifier.SHIFT,
                            MouseModifier.CONTROL,
                        }:
                            self.cell.select(extend=True)
                        else:
                            self.cell.select()
                        self.cell.focus()
                        get_app().invalidate()
                    return handler(mouse_event)

                mouse_handler_wrappers[handler] = wrapped_mouse_handler
            return mouse_handler_wrappers[handler]

        # Copy screen contents
        wp = write_position
        for y in range(wp.ypos, wp.ypos + wp.height):
            for x in range(wp.xpos, wp.xpos + wp.width):
                mouse_handlers.mouse_handlers[y][x] = _wrap_mouse_handler(
                    mouse_handlers.mouse_handlers[y][x]
                )

        return output

    def get_children(self) -> "List[Container]":
        """Return the list of child :class:`.Container` objects."""
        return [to_container(self.body)]


class Cell:
    """A notebook cell element.

    Contains a transparent clickable overlay, which is not displayed when the cell is
    focused.
    """

    def __init__(self, index: "int", json: "dict", notebook: "Notebook"):
        """Initiate the cell element.

        Args:
            index: The position of this cell in the notebook
            json: A reference to the cell's json object
            notebook: The notebook instance this cell belongs to

        """
        self.container: "Container" = Window()

        self.index = index
        self.json = json
        self.nb: "Notebook" = notebook
        self.rendered = True
        self.clear_outputs_on_output = False

        self.state = "idle"
        self.meta: "Optional[ChildRenderInfo]" = None

        self.show_input = Condition(
            lambda: bool(
                (self.json.get("cell_type") != "markdown")
                | ((self.json.get("cell_type") == "markdown") & ~self.rendered)
            )
        )
        self.show_output = Condition(
            lambda: (
                (self.json.get("cell_type") != "markdown") & bool(self.output_json)
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
        self._asking_input = False
        self.asking_input = Condition(lambda: self._asking_input)

        self.output_area = CellOutputArea(json=self.output_json, cell=self)

        # Generates the main container used to represent a notebook cell
        self.input_box = CellInputTextArea(self)

        ft = FormattedTextControl(
            self.border_char("TOP_LEFT"),
            focusable=True,
            show_cursor=False,
        )
        self.control = Window(
            ft, width=1, height=0, style=self.border_style, always_hide_cursor=True
        )

        fill = partial(Window, style=self.border_style)

        # Create textbox for standard input
        def _send_input(buf: "Buffer") -> "bool":
            return False

        self.stdin_box_accept_handler = _send_input
        self.stdin_box = CellStdinTextArea(
            multiline=False,
            accept_handler=lambda buf: self.stdin_box_accept_handler(buf),
            focus_on_click=True,
            prompt="> ",
        )

        # self.output_box = HSplit(
        # self.render_outputs(),
        # style="class:cell.output",
        # )

        top_border = VSplit(
            [
                self.control,
                ConditionalContainer(
                    content=fill(
                        char=self.border_char("TOP_MID"),
                        width=lambda: len(self.prompt),
                        height=1,
                    ),
                    filter=self.show_prompt,
                ),
                ConditionalContainer(
                    content=fill(width=1, height=1, char=self.border_char("TOP_SPLIT")),
                    filter=self.show_prompt,
                ),
                fill(char=self.border_char("TOP_MID"), height=1),
                fill(width=1, height=1, char=self.border_char("TOP_RIGHT")),
            ],
            height=1,
        )
        input_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=self.border_char("MID_LEFT")),
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
                        fill(width=1, char=self.border_char("MID_SPLIT")),
                        filter=self.show_prompt,
                    ),
                    self.input_box,
                    fill(width=1, char=self.border_char("MID_RIGHT")),
                ],
            ),
            filter=self.show_input,
        )
        middle_line = ConditionalContainer(
            content=VSplit(
                [
                    fill(width=1, height=1, char=self.border_char("SPLIT_LEFT")),
                    ConditionalContainer(
                        content=fill(
                            char=self.border_char("SPLIT_MID"),
                            width=lambda: len(self.prompt),
                        ),
                        filter=self.show_prompt,
                    ),
                    ConditionalContainer(
                        content=fill(
                            width=1, height=1, char=self.border_char("SPLIT_SPLIT")
                        ),
                        filter=self.show_prompt,
                    ),
                    fill(char=self.border_char("SPLIT_MID")),
                    fill(width=1, height=1, char=self.border_char("SPLIT_RIGHT")),
                ],
                height=1,
            ),
            filter=(self.show_input & self.show_output) | self.asking_input,
        )
        output_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=self.border_char("MID_LEFT")),
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
                        content=fill(width=1, char=self.border_char("MID_SPLIT")),
                        filter=self.show_prompt,
                    ),
                    ConditionalContainer(
                        fill(width=1, char=self.border_char("MID_MID")),
                        filter=~self.show_prompt,
                    ),
                    HSplit(
                        [
                            self.output_area,
                            ConditionalContainer(
                                Frame(self.stdin_box),
                                filter=self.asking_input,
                            ),
                        ]
                    ),
                    ConditionalContainer(
                        fill(width=1, char=self.border_char("MID_MID")),
                        filter=~self.show_prompt,
                    ),
                    fill(width=1, char=self.border_char("MID_RIGHT")),
                ],
            ),
            filter=self.show_output | self.asking_input,
        )
        bottom_border = VSplit(
            [
                fill(width=1, height=1, char=self.border_char("BOTTOM_LEFT")),
                ConditionalContainer(
                    content=fill(
                        char=self.border_char("BOTTOM_MID"),
                        width=lambda: len(self.prompt),
                    ),
                    filter=self.show_prompt,
                ),
                ConditionalContainer(
                    content=fill(
                        width=1, height=1, char=self.border_char("BOTTOM_SPLIT")
                    ),
                    filter=self.show_prompt,
                ),
                fill(char=self.border_char("BOTTOM_MID")),
                fill(width=1, height=1, char=self.border_char("BOTTOM_RIGHT")),
            ],
            height=1,
        )

        self.container = ClickToFocus(
            cell=self,
            body=HSplit(
                [top_border, input_row, middle_line, output_row, bottom_border],
            ),
        )

    def focus(self, position: "Optional[int]" = None) -> "None":
        """Focuses this cell."""
        pass

    @property
    def focused(self) -> "bool":
        """Determine if the cell currently has focus."""
        if self.container is not None:
            return get_app().layout.has_focus(self)
        else:
            return False

    @property
    def selected(self) -> "bool":
        """Determine if the cell currently is selected."""
        return False

    def select(
        self, extend: "bool" = False, position: "Optional[int]" = None
    ) -> "None":
        """Selects this cell or adds it to the selection.

        Args:
            extend: If true, the selection will be extended to include this cell
            position: An optional cursor position index to apply to the cell input

        """
        self.nb.select(self.index, extend=extend, position=position)

    def border_style(self) -> "str":
        """Determines the style of the cell borders, based on the cell state."""
        if self.selected:
            # Enter edit mode if the input has become focused via a mouse click
            if self.input_box.has_focus():
                self.nb.edit_mode = True
            # Exit edit mode if the stdin box has focus
            elif get_app().layout.has_focus(self.stdin_box):
                self.nb.edit_mode = False
            if self.nb.edit_mode:
                return "class:cell.border.edit"
            else:
                return "class:cell.border.selected"
        return "class:cell.border"

    def border_char(self, name: "str") -> "Callable[..., str]":
        """Returns a function which returns the cell border character to display."""

        def _inner() -> "str":
            grid = Invisible.grid
            if config.show_cell_borders or self.selected:
                if self.focused and multiple_cells_selected():
                    grid = Thick.outer
                else:
                    grid = Thin.outer
            return getattr(grid, name.upper())

        return _inner

    @property
    def cell_type(self) -> "str":
        """Determine the current cell type."""
        return self.json.get("cell_type", "code")

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
    def prompt(self) -> "str":
        """Determine what should be displayed in the prompt of the cell."""
        if self.state in ("busy", "queued"):
            prompt = "*"
        else:
            prompt = self.execution_count or " "
        if prompt:
            prompt = f"[{prompt}]"
        return prompt

    def _set_input(self, value: "str") -> "None":
        self.json["source"] = value

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
        cp = self.input_box.buffer.cursor_position
        self._set_input(value)
        self.input_box.text = self.json["source"]
        cp = max(0, min(cp, len(value)))
        self.input_box.buffer.cursor_position = cp

    @property
    def output_json(self) -> "List[Dict[str, Any]]":
        """Retrieve a list of cell outputs from the cell's JSON."""
        if self.cell_type == "markdown":
            return [
                {"data": {"text/x-markdown": self.input}, "output_type": "markdown"}
            ]
        else:
            return self.json.setdefault("outputs", [])

    def trigger_refresh(self, now: "bool" = True) -> "None":
        """Request that the cell to be re-rendered next time it is drawn."""
        if self.meta:
            self.meta.refresh = True
        if now:
            get_app().invalidate()

    def ran(self, content: "Dict" = None) -> "None":
        """Callback which runs when the cell has finished running."""
        self.state = "idle"
        self.trigger_refresh()

    def remove_output_graphic_floats(self) -> "None":
        """Unregisters the cell's output's graphic floats with the applications."""
        return
        for output in self.output_box.children:
            if graphic_float := output.graphic_float:
                graphic_float.content.content.hide()
                get_app().remove_float(graphic_float)

    def remove_outputs(self) -> "None":
        """Remove all outputs from the cell."""
        self.clear_outputs_on_output = False
        self.remove_output_graphic_floats()
        if "outputs" in self.json:
            del self.json["outputs"]

    def set_cell_type(
        self, cell_type: "Literal['markdown','code','raw']", clear: "bool" = False
    ) -> "None":
        """Convert the cell to a different cell type.

        Args:
            cell_type: The desired cell type.
            clear: If True, cell outputs will be cleared

        """
        if clear:
            self.remove_outputs()
        if cell_type == "code":
            self.json.setdefault("execution_count", None)
        if cell_type == "markdown" and "execution_count" in self.json:
            del self.json["execution_count"]
        # Record the new cell type
        self.json["cell_type"] = cell_type
        # Update the output-area
        self.output_area.json = self.output_json
        # Force the input box lexer to re-run
        self.input_box.control._fragment_cache.clear()

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

    def reformat(self) -> "None":
        """Reformats the cell's input."""
        self.input = format_code(self.input)
        self.trigger_refresh()

    def run_or_render(
        self,
        buffer: "Optional[Buffer]" = None,
        wait: "bool" = False,
    ) -> "bool":
        """Placeholder function for running the cell.

        Args:
            buffer: Unused parameter, required when accepting the contents of a cell's
                input buffer
            wait: Has no effect

        Returns:
            Always returns True

        """
        self.nb.exit_edit_mode()

        if self.cell_type == "markdown":
            self.output_area.json = self.output_json
            self.rendered = True

        elif self.cell_type == "code":
            if config.autoformat:
                self.reformat()
            self.state = "queued"
            self.trigger_refresh()
            self.nb.run_cell(self, wait=wait)

        return True

    def inspect(self) -> "None":
        """Get contextual help for the current cursor position."""
        pass

    def __pt_container__(self) -> "Container":
        """Returns the container which represents this cell."""
        return self.container

    def set_execution_count(self, n: "int") -> "None":
        """Set the execution count of the cell."""
        self.json["execution_count"] = n

    def add_output(self, output_json: "Dict[str, Any]") -> "None":
        """Add a new output to the cell."""
        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.remove_outputs()
        # Combine stream outputs with existing stream outputs
        for output in self.json.get("outputs", []):
            name = output.get("name")
            if name is not None and name == output_json.get("name"):
                output["text"] = output.get("text", "") + output_json.get("text", "")
                break
        else:
            self.json.setdefault("outputs", []).append(output_json)
        # Update the output area
        self.output_area.json = self.output_json
        self.trigger_refresh()

    def clear_output(self, wait: "bool" = False) -> "None":
        """Remove the cells output, optionally when new output is generated."""
        if wait:
            self.clear_outputs_on_output = True
        else:
            self.remove_outputs()

    def set_metadata(self, path: "Tuple[str, ...]", data: "Any") -> "None":
        """Sets a value in the metadata at an arbitrary path.

        Args:
            path: A tuple of path level names to create
            data: The value to add

        """
        level = self.json["metadata"]
        for i, key in enumerate(path):
            if i == len(path) - 1:
                level[key] = data
            else:
                level = level.setdefault(key, {})

    def set_status(self, status: "str") -> "None":
        """Set the execution status of the cell."""
        pass

    def get_input(
        self,
        prompt: "str" = "Please enter a value:",
        password: "bool" = False,
    ) -> "None":
        """Get input from the user for the given cell."""
        return None


PagerState = NamedTuple(
    "PagerState",
    [("code", str), ("cursor_pos", int), ("response", dict)],
)


class InteractiveCell(Cell):
    """An interactive notebook cell."""

    def __init__(self, index: "int", json: "dict", notebook: "EditNotebook") -> "None":
        """Initiate the interactive cell element.

        Args:
            index: The position of this cell in the notebook
            json: A reference to the cell's json object
            notebook: The notebook instance this cell belongs to

        """
        super().__init__(index, json, notebook)
        # Pytype need this re-defining...
        self.nb: "EditNotebook" = notebook
        self.stdin_event = asyncio.Event()
        self.inspect_future = None

    @property
    def selected(self) -> "bool":
        """Determine if the cell currently is selected."""
        if self.container is not None:
            return self.index in self.nb.page.selected_indices
        else:
            return False

    def focus(self, position: "Optional[int]" = None) -> "None":
        """Focuses the relevant control in this cell.

        Args:
            position: An optional cursor position index to apply to the input box

        """
        to_focus = None
        log.debug(self.nb.edit_mode)
        if self.nb.edit_mode:
            # Select just this cell when editing
            # self.nb.select(self.index)
            if self.asking_input():
                to_focus = self.stdin_box.window
            else:
                to_focus = self.input_box.window
                self.rendered = False
            if position is not None:
                self.input_box.buffer.cursor_position = position % (
                    len(self.input_box.buffer.text) or 1
                )
        else:
            to_focus = self.nb.cell.control

        # We force focus here, bypassing the layout's checks, as the control we want to
        # focus might be not be in the current layout yet.
        get_app().layout._stack.append(to_focus)
        # Scroll the currently selected slice into view
        self.nb.refresh(scroll=True)

    async def edit_in_editor(self) -> "None":
        """Edit the cell in $EDITOR."""
        self.nb.exit_edit_mode()
        await self.input_box.buffer.open_in_editor(
            validate_and_handle=config.run_after_external_edit
        )

    def split(self) -> "None":
        """Split the cell at the current cursor position."""
        self.nb.split_cell(self, self.input_box.buffer.cursor_position)
        self.input_box.buffer.cursor_position = 0

    def inspect(self) -> "None":
        """Get contextual help for the current cursor position."""
        code = self.input_box.text
        cursor_pos = self.input_box.buffer.cursor_position

        def _cb(response: "dict") -> "None":
            prev_state = self.nb.pager_state
            new_state = PagerState(
                code=code,
                cursor_pos=cursor_pos,
                response=response,
            )
            if prev_state != new_state:
                self.nb.pager_state = new_state
                get_app().invalidate()

        if self.nb.pager_visible() and self.nb.pager_state is not None:
            if (
                self.nb.pager_state.code == code
                and self.nb.pager_state.cursor_pos == cursor_pos
            ):
                self.nb.focus_pager()
                return

        self.nb.kernel.inspect(
            code=code,
            cursor_pos=cursor_pos,
            callback=_cb,
        )

    def get_input(
        self,
        prompt: "str" = "Please enter a value:",
        password: "bool" = False,
    ) -> "None":
        """Prompts the user for input and sends the result to the kernel."""
        # Set this first so the height of the cell includes the input box if it gets
        # rendered when we scroll to it
        self._asking_input = True
        # Remember what was focused before
        app = get_app()
        layout = app.layout
        focused = layout.current_control
        # Scroll the current cell into view - this causes the cell to be rendered if it
        # is not already on screen
        self.nb.page.selected_slice = slice(self.index, self.index + 1)
        # Set the prompt text for the BeforeInput pre-processor
        if self.stdin_box.control.input_processors is not None:
            prompt_processor = self.stdin_box.control.input_processors[2]
            if isinstance(prompt_processor, BeforeInput):
                prompt_processor.text = f"{prompt} "
        # Set the password status of the input box
        self.stdin_box.password = password

        def _send_input(buf: "Buffer") -> "bool":
            """Send the input to the kernel and hide the input box."""
            if self.nb.kernel.kc is not None:
                self.nb.kernel.kc.input(buf.text)
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

        self.stdin_box_accept_handler = _send_input

        # Try focusing the input box - we create an asynchronous task which will
        # probably run after the next render, when the stdin_box is recognised as being
        # in the layout. This doesn't always work (depending on timing), does usually.
        async def _focus_input() -> "None":
            # Focus the input box
            if self.stdin_box.window in layout.visible_windows:
                layout.focus(self.stdin_box)
            # Redraw the screen to show it as focused
            app.invalidate()

        try:
            layout.focus(self.stdin_box)
        finally:
            app.create_background_task(_focus_input())
            app.create_background_task(_focus_input())
