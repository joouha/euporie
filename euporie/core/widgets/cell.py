"""Defines a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import logging
import weakref
from functools import partial
from typing import TYPE_CHECKING

import nbformat
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    HSplit,
    VSplit,
    Window,
    to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, SimpleLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType, MouseModifier
from pygments.lexers import get_lexer_by_name

from euporie.core.app import get_app
from euporie.core.border import Invisible, Thick, Thin
from euporie.core.config import add_setting
from euporie.core.filters import multiple_cells_selected
from euporie.core.format import format_code
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput

if TYPE_CHECKING:
    from typing import Any, Callable, Literal, Optional

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition

    from euporie.core.tabs.notebook import BaseNotebook
    from euporie.core.widgets.page import ChildRenderInfo


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
        self.done_mouse_down = False

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

                    if self.cell.kernel_tab.app.layout.has_focus(self.cell):
                        result = None
                        # If we just handled a mouse down event, the page may have
                        # scrolled, resulting in a change in cursor position on the
                        # next mouse-up event, causing a selection to be created.
                        # Here we check for this scenario and close the selection, and
                        # prevent the cursor position moving on mouse up
                        if (
                            self.done_mouse_down
                            and mouse_event.event_type == MouseEventType.MOUSE_UP
                            and self.cell.kernel_tab.edit_mode
                        ):
                            self.cell.kernel_tab.app.current_buffer.exit_selection()

                        else:
                            # Run the wrapped mouse handler
                            result = handler(mouse_event)

                        self.done_mouse_down = False
                        return result

                    elif mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                        # Use a set intersection
                        if mouse_event.modifiers & {
                            MouseModifier.SHIFT,
                            MouseModifier.CONTROL,
                        }:
                            self.cell.select(extend=True)
                        else:
                            self.cell.select()
                        self.cell.focus(scroll=True)
                        self.done_mouse_down = True
                        # Run the wrapped mouse handler
                        handler(mouse_event)
                        # Return None for the app is always invalidated
                        return None

                    return NotImplemented

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

    def get_children(self) -> "list[Container]":
        """Return the list of child :class:`.Container` objects."""
        return [to_container(self.body)]


class Cell:
    """A kernel_tab cell element.

    Contains a transparent clickable overlay, which is not displayed when the cell is
    focused.
    """

    input_box: "KernelInput"

    def __init__(self, index: "int", json: "dict", kernel_tab: "BaseNotebook"):
        """Initiate the cell element.

        Args:
            index: The position of this cell in the kernel_tab
            json: A reference to the cell's json object
            kernel_tab: The kernel_tab instance this cell belongs to

        """
        weak_self = weakref.proxy(self)
        self.index = index
        self.json = json
        self.kernel_tab: "BaseNotebook" = kernel_tab
        self.rendered = True
        self.clear_outputs_on_output = False

        self.state = "idle"
        self.meta: "Optional[ChildRenderInfo]" = None

        show_input = Condition(
            lambda: bool(
                (weak_self.json.get("cell_type") != "markdown")
                | (
                    (weak_self.json.get("cell_type") == "markdown")
                    & ~weak_self.rendered
                )
            )
        )
        show_output = Condition(
            lambda: (
                (weak_self.json.get("cell_type") != "markdown")
                & bool(weak_self.output_json)
                | ((weak_self.json.get("cell_type") == "markdown") & weak_self.rendered)
            )
        )
        # scroll_input = Condition(
        # lambda: bool(
        # (weak_self.json.get("cell_type") == "markdown") & ~weak_self.rendered
        # )
        # )
        show_prompt = Condition(lambda: weak_self.cell_type == "code")
        self.is_code = Condition(lambda: weak_self.json.get("cell_type") == "code")

        self.output_area = CellOutputArea(json=self.output_json, parent=weak_self)

        def on_text_changed(buf: "Buffer") -> "None":
            """Update cell json when the input buffer has been edited."""
            weak_self._set_input(buf.text)
            weak_self.kernel_tab.dirty = True

        def on_cursor_position_changed(buf: "Buffer") -> "None":
            """Respond to cursor movements."""
            # Update contextual help
            if weak_self.kernel_tab.app.config.autoinspect and weak_self.is_code():
                weak_self.kernel_tab.inspect()
            else:
                if pager := get_app().pager:
                    pager.hide()

            # Tell the scrolling container to scroll the cursor into view on the next render
            weak_self.kernel_tab.page.scroll_to_cursor = True

        # Noew we generate the main container used to represent a kernel_tab cell

        self.input_box = KernelInput(
            kernel_tab=self.kernel_tab,
            text=self.input,
            complete_while_typing=self.is_code,
            autosuggest_while_typing=self.is_code,
            wrap_lines=Condition(lambda: weak_self.json.get("cell_type") == "markdown"),
            on_text_changed=on_text_changed,
            on_cursor_position_changed=on_cursor_position_changed,
            lexer=DynamicLexer(
                partial(
                    lambda cell: (
                        PygmentsLexer(
                            get_lexer_by_name(cell.language).__class__,
                            sync_from_start=False,
                        )
                        if cell.cell_type != "raw"
                        else SimpleLexer()
                    ),
                    weakref.proxy(self),
                )
            ),
        )
        self.input_box.buffer.name = self.cell_type

        def border_char(name: "str") -> "Callable[..., str]":
            """Returns a function which returns the cell border character to display."""

            def _inner() -> "str":
                grid = Invisible.grid
                if get_app().config.show_cell_borders or weak_self.selected:
                    if weak_self.focused and multiple_cells_selected():
                        grid = Thick.outer
                    else:
                        grid = Thin.outer
                return getattr(grid, name.upper())

            return _inner

        def border_style() -> "str":
            """Determines the style of the cell borders, based on the cell state."""
            if weak_self.selected:
                if weak_self.kernel_tab.in_edit_mode():
                    return "class:cell.border.edit"
                else:
                    return "class:cell.border.selected"
            return "class:cell.border"

        self.control = Window(
            FormattedTextControl(
                border_char("TOP_LEFT"),
                focusable=True,
                show_cursor=False,
            ),
            width=1,
            height=0,
            style=border_style,
            always_hide_cursor=True,
        )

        fill = partial(Window, style=border_style)

        # Create textbox for standard input
        def _send_input(buf: "Buffer") -> "bool":
            return False

        self.stdin_box = StdInput(self.kernel_tab)

        top_border = VSplit(
            [
                self.control,
                ConditionalContainer(
                    content=fill(
                        char=border_char("TOP_MID"),
                        width=lambda: len(weak_self.prompt),
                        height=1,
                    ),
                    filter=show_prompt,
                ),
                ConditionalContainer(
                    content=fill(width=1, height=1, char=border_char("TOP_SPLIT")),
                    filter=show_prompt,
                ),
                fill(char=border_char("TOP_MID"), height=1),
                fill(width=1, height=1, char=border_char("TOP_RIGHT")),
            ],
            height=1,
        )
        input_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=border_char("MID_LEFT")),
                    ConditionalContainer(
                        content=Window(
                            FormattedTextControl(
                                lambda: weak_self.prompt,
                            ),
                            width=lambda: len(weak_self.prompt),
                            style="class:cell.input.prompt",
                        ),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(
                        fill(width=1, char=border_char("MID_SPLIT")),
                        filter=show_prompt,
                    ),
                    self.input_box,
                    fill(width=1, char=border_char("MID_RIGHT")),
                ],
            ),
            filter=show_input,
        )
        middle_line = ConditionalContainer(
            content=VSplit(
                [
                    fill(width=1, height=1, char=border_char("SPLIT_LEFT")),
                    ConditionalContainer(
                        content=fill(
                            char=border_char("SPLIT_MID"),
                            width=lambda: len(weak_self.prompt),
                        ),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(
                        content=fill(
                            width=1, height=1, char=border_char("SPLIT_SPLIT")
                        ),
                        filter=show_prompt,
                    ),
                    fill(char=border_char("SPLIT_MID")),
                    fill(width=1, height=1, char=border_char("SPLIT_RIGHT")),
                ],
                height=1,
            ),
            filter=(show_input & show_output) | self.stdin_box.visible,
        )
        output_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=border_char("MID_LEFT")),
                    ConditionalContainer(
                        content=Window(
                            FormattedTextControl(
                                lambda: weak_self.prompt,
                            ),
                            width=lambda: len(weak_self.prompt),
                            style="class:cell.output.prompt",
                        ),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(
                        content=fill(width=1, char=border_char("MID_SPLIT")),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(
                        fill(width=1, char=border_char("MID_MID")),
                        filter=~show_prompt,
                    ),
                    HSplit(
                        [
                            self.output_area,
                            self.stdin_box,
                        ]
                    ),
                    ConditionalContainer(
                        fill(width=1, char=border_char("MID_MID")),
                        filter=~show_prompt,
                    ),
                    fill(width=1, char=border_char("MID_RIGHT")),
                ],
            ),
            filter=show_output | self.stdin_box.visible,
        )
        bottom_border = VSplit(
            [
                fill(width=1, height=1, char=border_char("BOTTOM_LEFT")),
                ConditionalContainer(
                    content=fill(
                        char=border_char("BOTTOM_MID"),
                        width=lambda: len(weak_self.prompt),
                    ),
                    filter=show_prompt,
                ),
                ConditionalContainer(
                    content=fill(width=1, height=1, char=border_char("BOTTOM_SPLIT")),
                    filter=show_prompt,
                ),
                fill(char=border_char("BOTTOM_MID")),
                fill(width=1, height=1, char=border_char("BOTTOM_RIGHT")),
            ],
            height=1,
        )

        self.container = ClickToFocus(
            cell=weak_self,
            body=HSplit(
                [
                    top_border,
                    input_row,
                    middle_line,
                    output_row,
                    bottom_border,
                ],
            ),
        )

    def focus(self, position: "Optional[int]" = None, scroll: "bool" = False) -> "None":
        """Focuses the relevant control in this cell.

        Args:
            position: An optional cursor position index to apply to the input box
            scroll: Whether to scroll the page to make the selection visible

        """
        to_focus = None
        if self.kernel_tab.edit_mode:
            # Select just this cell when editing
            # self.kernel_tab.select(self.index)
            if self.stdin_box.visible():
                to_focus = self.stdin_box.window
            else:
                to_focus = self.input_box.window
                self.rendered = False
            if position is not None:
                self.input_box.buffer.cursor_position = position % (
                    len(self.input_box.buffer.text) or 1
                )
        else:
            to_focus = self.kernel_tab.cell.control

        # We force focus here, bypassing the layout's checks, as the control we want to
        # focus might be not be in the current layout yet.
        get_app().layout._stack.append(to_focus)
        # Scroll the currently selected slice into view
        self.kernel_tab.refresh(scroll=scroll)

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
        if self.container is not None:
            return self.index in self.kernel_tab.selected_indices
        else:
            return False

    def select(
        self,
        extend: "bool" = False,
        position: "Optional[int]" = None,
        scroll: "bool" = False,
    ) -> "None":
        """Selects this cell or adds it to the selection.

        Args:
            extend: If true, the selection will be extended to include this cell
            position: An optional cursor position index to apply to the cell input
            scroll: Whether to change the position of the selected cell

        """
        self.kernel_tab.select(
            self.index, extend=extend, position=position, scroll=scroll
        )

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
    def output_json(self) -> "list[dict[str, Any]]":
        """Retrieve a list of cell outputs from the cell's JSON."""
        if self.cell_type == "markdown":
            return [
                {"data": {"text/x-markdown": self.input}, "output_type": "markdown"}
            ]
        else:
            return self.json.setdefault("outputs", [])

    def refresh(self, now: "bool" = True) -> "None":
        """Request that the cell to be re-rendered next time it is drawn."""
        if self.meta:
            self.meta.refresh = True
        if now:
            get_app().invalidate()

    def ran(self, content: "dict" = None) -> "None":
        """Callback which runs when the cell has finished running."""
        self.state = "idle"
        self.refresh()

    def remove_outputs(self) -> "None":
        """Remove all outputs from the cell."""
        self.clear_outputs_on_output = False
        if "outputs" in self.json:
            self.json["outputs"].clear()
        self.output_area.reset()

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
        self.input_box.buffer.name = cell_type
        # Update the output-area
        # self.output_area.json = self.output_json
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
            lang_info = self.kernel_tab.json.metadata.get("language_info", {})
            return lang_info.get("name", lang_info.get("pygments_lexer", "python"))
        else:
            return "raw"

    def reformat(self) -> "None":
        """Reformats the cell's input."""
        config = get_app().config
        self.input = format_code(self.input, config)
        self.refresh()

    def run_or_render(
        self,
        buffer: "Optional[Buffer]" = None,
        wait: "bool" = False,
        callback: "Optional[Callable[..., None]]" = None,
    ) -> "bool":
        """Placeholder function for running the cell.

        Args:
            buffer: Unused parameter, required when accepting the contents of a cell's
                input buffer
            wait: Has no effect
            callback: Callable to run when the kernel has finished running the cell

        Returns:
            Always returns True

        """
        if self.cell_type == "markdown":
            self.output_area.json = self.output_json
            self.rendered = True

        elif self.cell_type == "code":
            if get_app().config.autoformat:
                self.reformat()
            self.state = "queued"
            self.refresh()
            self.kernel_tab.run_cell(self, wait=wait, callback=callback)

        return True

    def __pt_container__(self) -> "Container":
        """Returns the container which represents this cell."""
        return self.container

    def set_execution_count(self, n: "int") -> "None":
        """Set the execution count of the cell."""
        self.json["execution_count"] = n

    def add_output(self, output_json: "dict[str, Any]") -> "None":
        """Add a new output to the cell."""
        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.remove_outputs()
        self.json.setdefault("outputs", []).append(output_json)
        # Add the new output to the output area
        self.output_area.add_output(output_json)
        # Tell the page this cell has been updated
        self.refresh()

    def clear_output(self, wait: "bool" = False) -> "None":
        """Remove the cells output, optionally when new output is generated."""
        if wait:
            self.clear_outputs_on_output = True
        else:
            self.remove_outputs()

    def set_metadata(self, path: "tuple[str, ...]", data: "Any") -> "None":
        """Sets a value in the metadata at an arbitrary path.

        Args:
            path: A tuple of path level names to create
            data: The value to add

        """
        if self.kernel_tab.app.config.record_cell_timing:
            level = self.json["metadata"]
            for i, key in enumerate(path):
                if i == len(path) - 1:
                    level[key] = data
                else:
                    level = level.setdefault(key, {})

    def set_status(self, status: "str") -> "None":
        """Set the execution status of the cell."""
        # log.debug(status)
        pass

    def get_input(
        self,
        prompt: "str" = "Please enter a value:",
        password: "bool" = False,
    ) -> "None":
        """Scroll the cell requesting input into view and render it before asking for input."""
        self.kernel_tab.select(self.index)
        self.stdin_box.get_input(prompt, password)

    async def edit_in_editor(self) -> "None":
        """Edit the cell in $EDITOR."""
        await self.input_box.buffer.open_in_editor(
            validate_and_handle=get_app().config.run_after_external_edit
        )
        if (
            self.cell_type == "markdown"
            or self.kernel_tab.app.config.run_after_external_edit
        ):
            self.run_or_render()

    # ################################### Settings ####################################

    add_setting(
        name="show_cell_borders",
        title="cell borders",
        flags=["--show-cell-borders"],
        type_=bool,
        help_="Show or hide cell borders.",
        default=False,
        schema={
            "type": "boolean",
        },
        description="""
            Whether cell borders should be drawn for unselected cells.
        """,
    )

    add_setting(
        name="record_cell_timing",
        title="cell timing recording",
        flags=["--record-cell-timing"],
        type_=bool,
        help_="Should timing data be recorded in cell metadata.",
        default=False,
        schema={
            "type": "boolean",
        },
        description="""
            When set, execution timing data will be recorded in cell metadata.
        """,
    )
