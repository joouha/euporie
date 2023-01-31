"""Defines a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import logging
import os
import weakref
from functools import partial
from typing import TYPE_CHECKING, cast

import nbformat
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, SimpleLexer
from pygments.lexers import get_lexer_by_name

from euporie.core.border import NoLine, ThickLine, ThinLine
from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.filters import multiple_cells_selected
from euporie.core.format import format_code
from euporie.core.utils import on_click
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput

if TYPE_CHECKING:
    from typing import Any, Callable, Literal, Optional

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text.base import OneStyleAndTextTuple

    from euporie.core.tabs.notebook import BaseNotebook


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


class Cell:
    """A kernel_tab cell element.

    Contains a transparent clickable overlay, which is not displayed when the cell is
    focused.
    """

    input_box: "KernelInput"

    def __init__(
        self, index: "int", json: "dict", kernel_tab: "BaseNotebook"
    ) -> "None":
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
                weak_self.input_box.inspect()
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
            accept_handler=lambda buffer: self.run_or_render() or True,
        )
        self.input_box.buffer.name = self.cell_type

        def border_char(name: "str") -> "Callable[..., str]":
            """Returns a function which returns the cell border character to display."""

            def _inner() -> "str":
                grid = NoLine.grid
                if get_app().config.show_cell_borders or weak_self.selected:
                    if weak_self.focused and multiple_cells_selected():
                        grid = ThickLine.outer
                    else:
                        grid = ThinLine.outer
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

        source_hidden = Condition(
            lambda: self.json["metadata"].get("jupyter", {}).get("source_hidden", False)
        )

        input_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=border_char("MID_LEFT")),
                    ConditionalContainer(
                        content=Window(
                            FormattedTextControl(
                                lambda: [
                                    (
                                        "",
                                        weak_self.prompt,
                                        on_click(self.toggle_input),
                                    ),
                                    ("", "\n ", lambda e: NotImplemented),
                                ]
                            ),
                            width=lambda: len(weak_self.prompt),
                            height=Dimension(preferred=1),
                            style="class:cell.input.prompt",
                        ),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(
                        fill(width=1, char=border_char("MID_SPLIT")),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(self.input_box, filter=~source_hidden),
                    ConditionalContainer(
                        Window(
                            FormattedTextControl(
                                [
                                    cast(
                                        "OneStyleAndTextTuple",
                                        (
                                            "class:cell,show,inputs",
                                            " … ",
                                            on_click(self.show_input),
                                        ),
                                    )
                                ]
                            )
                        ),
                        filter=source_hidden,
                    ),
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

        outputs_hidden = Condition(
            lambda: self.json["metadata"]
            .get("jupyter", {})
            .get("outputs_hidden", False)
            or self.json["metadata"].get("collapsed", False)
        )

        output_row = ConditionalContainer(
            VSplit(
                [
                    fill(width=1, char=border_char("MID_LEFT")),
                    ConditionalContainer(
                        content=Window(
                            FormattedTextControl(
                                lambda: [
                                    (
                                        "",
                                        weak_self.prompt,
                                        on_click(self.toggle_output),
                                    ),
                                    ("", "\n ", lambda e: NotImplemented),
                                ],
                            ),
                            width=lambda: len(weak_self.prompt),
                            height=Dimension(preferred=1),
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
                            ConditionalContainer(
                                self.output_area,
                                filter=~outputs_hidden,
                            ),
                            ConditionalContainer(
                                Window(
                                    FormattedTextControl(
                                        [
                                            cast(
                                                "OneStyleAndTextTuple",
                                                (
                                                    "class:cell,show,outputs",
                                                    " … ",
                                                    on_click(self.show_output),
                                                ),
                                            ),
                                        ]
                                    )
                                ),
                                filter=outputs_hidden,
                            ),
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

        self.container = HSplit(
            [
                top_border,
                input_row,
                middle_line,
                output_row,
                bottom_border,
            ],
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
                self.show_input()
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
        if scroll:
            self.kernel_tab.scroll_to(self.index)

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
        self.kernel_tab.refresh_cell(self)
        if now:
            get_app().invalidate()

    def ran(self, content: "dict|None" = None) -> "None":
        """Callback which runs when the cell has finished running."""
        self.state = "idle"
        self.refresh()

    def remove_outputs(self) -> "None":
        """Remove all outputs from the cell."""
        self.clear_outputs_on_output = False
        if "outputs" in self.json:
            self.json["outputs"].clear()
        if self.cell_type != "markdown":
            self.output_area.reset()
        # Ensure the cell output area is visible
        self.show_output()
        self.refresh()

    def set_cell_type(
        self, cell_type: "Literal['markdown','code','raw']", clear: "bool" = False
    ) -> "None":
        """Convert the cell to a different cell type.

        Args:
            cell_type: The desired cell type.
            clear: If True, cell outputs will be cleared

        """
        if clear and cell_type != "markdown":
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

    def show_input(self) -> "None":
        """Set the cell inputs to visible."""
        self.set_metadata(("jupyter", "source_hidden"), False)

    def hide_input(self) -> "None":
        """Set the cell inputs to visible."""
        # Exit edit mode
        self.kernel_tab.edit_mode = False
        # Un-focus the cell input
        self.focus()
        # Set the input to hidden
        self.set_metadata(("jupyter", "source_hidden"), True)

    def toggle_input(self) -> "None":
        """Toggle the visibility of the cell input."""
        if self.json["metadata"].get("jupyter", {}).get("source_hidden", False):
            self.show_input()
        else:
            self.hide_input()

    def show_output(self) -> "None":
        """Set the cell outputs to visible."""
        self.set_metadata(("jupyter", "outputs_hidden"), False)
        self.set_metadata(("collapsed",), False)

    def hide_output(self) -> "None":
        """Set the cell outputs to visible."""
        self.set_metadata(("jupyter", "outputs_hidden"), True)
        self.set_metadata(("collapsed",), True)

    def toggle_output(self) -> "None":
        """Toggle the visibility of the cell outputs."""
        if self.json["metadata"].get("jupyter", {}).get("outputs_hidden", False):
            self.show_output()
        else:
            self.hide_output()

    def set_metadata(self, path: "tuple[str, ...]", data: "Any") -> "None":
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
        buffer = self.input_box.buffer
        app = get_app()
        edit_in_fg = False

        # Save VISUAL environment variable
        visual = os.environ.get("VISUAL")

        if editor := app.config.external_editor:

            if "{left}" in editor:
                win = self.input_box.window

                if (info := win.render_info) is not None:
                    edit_in_fg = True

                    margin_left = sum(
                        [win._get_margin_width(m) for m in win.left_margins]
                    )
                    margin_right = sum(
                        [win._get_margin_width(m) for m in win.right_margins]
                    )
                    top = info._y_offset
                    left = info._x_offset - margin_left
                    width = info.window_width + margin_left + margin_right
                    height = min(app.output.get_size().rows, info.window_height)

                else:
                    left = top = 0
                    height, width = app.output.get_size()

                editor = editor.format(
                    top=top,
                    left=left,
                    width=width,
                    height=height,
                    bottom=top + height,
                    right=left + width,
                )

            # Override VISUAL environment variable
            os.environ["VISUAL"] = editor

        if edit_in_fg:
            # Create a tempfile
            if buffer.tempfile:
                filename, cleanup_func = buffer._editor_complex_tempfile()
            else:
                filename, cleanup_func = buffer._editor_simple_tempfile()
            try:
                # Edit the temp file
                success = buffer._open_file_in_editor(filename)
                # Read content again.
                if success:
                    with open(filename, "rb") as f:
                        text = f.read().decode("utf-8")
                        # Drop trailing newline
                        if text.endswith("\n"):
                            text = text[:-1]
                        buffer.document = Document(text=text, cursor_position=len(text))
                    # Run the cell if configured
                    if app.config.run_after_external_edit:
                        buffer.validate_and_handle()
            finally:
                # Clean up temp dir/file.
                cleanup_func()

        else:
            await buffer.open_in_editor(
                validate_and_handle=app.config.run_after_external_edit
            )

        # Restore VISUAL environment variable
        if visual is not None:
            os.environ["VISUAL"] = visual

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
        name="external_editor",
        flags=["--external-editor"],
        type_=str,
        help_="Set the external editor to use.",
        default=None,
        description="""
            A command to run when editing cells externally. The following strings in
            the command will be replaced with values which locate the cell being
            edited:

            * ``{top}``
            * ``{left}``
            * ``{bottom}``
            * ``{right}``
            * ``{width}``
            * ``{height}``

            This is useful if you run euporie inside a tmux session, and wish to launch
            your editor in a pop-up pane. This can be achieved by setting this parameter
            to something like the following:

            .. code-block::

               "tmux display-popup -x {left} -y {bottom} -w {width} -h {height} -B -E micro"

        """,
    )
