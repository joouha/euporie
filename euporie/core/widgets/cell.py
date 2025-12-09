"""Define a cell object with input are and rich outputs, and related objects."""

from __future__ import annotations

import asyncio
import logging
import os
import weakref
from functools import lru_cache, partial
from pathlib import Path
from typing import TYPE_CHECKING, cast
from weakref import WeakKeyDictionary

from prompt_toolkit.completion.base import (
    DynamicCompleter,
    _MergedCompleter,
)
from prompt_toolkit.document import Document
from prompt_toolkit.filters.app import is_searching
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.utils import Event

from euporie.core.app.current import get_app
from euporie.core.border import NoLine, ThickLine, ThinLine
from euporie.core.completion import DeduplicateCompleter, LspCompleter
from euporie.core.diagnostics import Report
from euporie.core.filters import multiple_cells_selected
from euporie.core.format import LspFormatter
from euporie.core.inspection import (
    FirstInspector,
    LspInspector,
)
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.lsp import LspCell
from euporie.core.utils import on_click
from euporie.core.widgets.cell_outputs import CellOutputArea
from euporie.core.widgets.inputs import KernelInput, StdInput

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Literal

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.completion.base import Completer
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples

    from euporie.core.border import GridStyle
    from euporie.core.format import Formatter
    from euporie.core.inspection import Inspector
    from euporie.core.lsp import LspClient
    from euporie.core.tabs.notebook import BaseNotebook


log = logging.getLogger(__name__)


def get_cell_id(cell_json: dict) -> str:
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
        from uuid import uuid4

        cell_json["id"] = cell_id = uuid4().hex[:8]
    return cell_id


@lru_cache(maxsize=32)
def _get_border_style(
    selected: bool, focused: bool, show_borders: bool, multi_selected: bool
) -> GridStyle:
    """Get the border style grid based on cell state."""
    if not (show_borders or selected):
        return NoLine.grid
    if focused and multi_selected:
        return ThickLine.outer
    return ThinLine.outer


class Cell:
    """A kernel_tab cell element.

    Contains a transparent clickable overlay, which is not displayed when the cell is
    focused.
    """

    def __init__(
        self, index: int, json: dict, kernel_tab: BaseNotebook, is_new: bool = False
    ) -> None:
        """Initiate the cell element.

        Args:
            index: The position of this cell in the kernel_tab
            json: A reference to the cell's json object
            kernel_tab: The kernel_tab instance this cell belongs to
            is_new: Flag a newly inserted cell

        """
        weak_self = weakref.proxy(self)
        self.index = index
        self.json = json
        self.kernel_tab: BaseNotebook = kernel_tab
        self.rendered = True
        self.clear_outputs_on_output = False
        self.state = "idle"
        self.is_new = is_new

        self.on_open = Event(self)
        self.on_change = Event(self)
        self.on_close = Event(self)

        self.inspectors: list[Inspector] = []
        self.inspector = FirstInspector(
            lambda: [*self.kernel_tab.inspectors, *self.inspectors]
        )
        self.completers: list[Completer] = []
        self.completer = DeduplicateCompleter(
            DynamicCompleter(
                lambda: _MergedCompleter(
                    [*self.kernel_tab.completers, *self.completers]
                )
            )
        )
        self.formatters: list[Formatter] = [*self.kernel_tab.formatters]
        self.reports: WeakKeyDictionary[LspClient, Report] = WeakKeyDictionary()

        # Conditions
        # Determine if the cell currently has focus
        focused = Condition(
            lambda: weak_self.kernel_tab.app.layout.has_focus(weak_self)
            if self.container is not None
            else False
        )
        # Determine if the cell currently is selected.
        in_edit_mode = Condition(lambda: self.kernel_tab.edit_mode)
        selected = Condition(
            lambda: self.index in self.kernel_tab.selected_indices
            if self.container is not None
            else False
        )
        is_markdown = Condition(lambda: weak_self.json.get("cell_type") == "markdown")
        is_rendered = Condition(lambda: weak_self.rendered)
        has_outputs = Condition(lambda: bool(weak_self.output_json))
        show_input = ~is_markdown | (
            is_markdown & (~is_rendered | (focused & in_edit_mode))
        )
        show_output = (~is_markdown & has_outputs) | (is_markdown & ~show_input)
        show_prompt = Condition(lambda: weak_self.cell_type == "code")
        self.is_code = Condition(lambda: weak_self.json.get("cell_type") == "code")

        self.output_area = CellOutputArea(json=self.output_json, parent=weak_self)

        def on_text_changed(buf: Buffer) -> None:
            """Update cell json when the input buffer has been edited."""
            weak_self._set_input(buf.text)
            weak_self.kernel_tab.dirty = True
            weak_self.on_change()
            # Re-render markdown cells when edited outside of edit mode
            if weak_self.cell_type == "markdown" and not weak_self.kernel_tab.edit_mode:
                weak_self.output_area.json = weak_self.output_json
                weak_self.refresh()

        def on_cursor_position_changed(buf: Buffer) -> None:
            """Respond to cursor movements."""
            # Tell the scrolling container to scroll the cursor into view on the next render
            weak_self.kernel_tab.page.scroll_to_cursor = True
            if not is_searching():
                if not selected():
                    weak_self.kernel_tab.select(self.index, scroll=True)
                if not weak_self.kernel_tab.in_edit_mode():
                    weak_self.kernel_tab.enter_edit_mode()

        # Now we generate the main container used to represent a kernel_tab cell

        source_hidden = Condition(
            lambda: weak_self.json.get("metadata", {})
            .get("jupyter", {})
            .get("source_hidden", False)
        )

        self.input_box = KernelInput(
            kernel_tab=self.kernel_tab,
            text=self.input,
            completer=self.completer,
            complete_while_typing=self.is_code,
            autosuggest_while_typing=self.is_code,
            wrap_lines=Condition(lambda: weak_self.json.get("cell_type") == "markdown"),
            on_text_changed=on_text_changed,
            on_cursor_position_changed=on_cursor_position_changed,
            language=partial(lambda cell: cell.language, weakref.proxy(self)),
            accept_handler=lambda buffer: weak_self.run_or_render() or True,
            # focusable=show_input & ~source_hidden,
            focusable=True,
            tempfile_suffix=self.suffix,
            inspector=self.inspector,
            diagnostics=self.report,
            formatters=self.formatters,
            # show_diagnostics=Condition(
            #     lambda: kernel_tab.app.layout.has_focus(self.input_box.buffer)
            # ),
            relative_line_numbers=self.kernel_tab.app.config.filters.relative_line_numbers,
        )
        self.input_box.buffer.name = self.cell_type

        def border_char(name: str) -> Callable[..., str]:
            """Return a function which returns the cell border character to display."""

            def _inner() -> str:
                if not weak_self:
                    return " "
                grid = _get_border_style(
                    selected(),
                    focused(),
                    weak_self.kernel_tab.app.config.show_cell_borders,
                    multiple_cells_selected(),
                )
                return getattr(grid, name.upper())

            return _inner

        self.control = Window(
            FormattedTextControl(
                border_char("TOP_LEFT"),
                focusable=True,
                show_cursor=False,
            ),
            width=1,
            height=0,
            style="class:border",
            always_hide_cursor=True,
        )

        fill = partial(Window, style="class:border")

        # Create textbox for standard input
        self.stdin_box = StdInput(weak_self.kernel_tab)

        input_row = ConditionalContainer(
            VSplit(
                [
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
                            width=lambda: len(weak_self.prompt) + 1,
                            height=Dimension(preferred=1),
                            style="class:input,prompt",
                        ),
                        filter=show_prompt,
                    ),
                    ConditionalContainer(self.input_box, filter=~source_hidden),
                    ConditionalContainer(
                        Window(
                            FormattedTextControl(
                                cast(
                                    "StyleAndTextTuples",
                                    [
                                        (
                                            "class:cell,show,inputs,border",
                                            "▏",
                                            on_click(self.show_input),
                                        ),
                                        (
                                            "class:cell,show,inputs",
                                            "…",
                                            on_click(self.show_input),
                                        ),
                                        (
                                            "class:cell,show,inputs,border",
                                            "▕",
                                            on_click(self.show_input),
                                        ),
                                    ],
                                )
                            )
                        ),
                        filter=source_hidden,
                    ),
                ],
            ),
            filter=show_input,
        )

        outputs_hidden = Condition(
            lambda: weak_self.json["metadata"]
            .get("jupyter", {})
            .get("outputs_hidden", False)
            or weak_self.json["metadata"].get("collapsed", False)
        )

        output_row = ConditionalContainer(
            VSplit(
                [
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
                            width=lambda: len(weak_self.prompt) + 1,
                            height=Dimension(preferred=1),
                            style="class:output,prompt",
                        ),
                        filter=show_prompt,
                    ),
                    HSplit(
                        [
                            ConditionalContainer(
                                self.output_area, filter=~outputs_hidden
                            ),
                            ConditionalContainer(
                                Window(
                                    FormattedTextControl(
                                        cast(
                                            "StyleAndTextTuples",
                                            [
                                                (
                                                    "class:cell,show,outputs,border",
                                                    "▏",
                                                    on_click(self.show_output),
                                                ),
                                                (
                                                    "class:cell,show,outputs",
                                                    "…",
                                                    on_click(self.show_output),
                                                ),
                                                (
                                                    "class:cell,show,outputs,border",
                                                    "▕",
                                                    on_click(self.show_output),
                                                ),
                                            ],
                                        )
                                    )
                                ),
                                filter=outputs_hidden,
                            ),
                            self.stdin_box,
                        ],
                    ),
                ],
                width=Dimension(min=1),
            ),
            filter=show_output | self.stdin_box.visible,
        )

        def _style() -> str:
            """Calculate the cell's style given its state."""
            style = "class:cell"
            if selected():
                if weak_self.kernel_tab.in_edit_mode():
                    style += ",edit"
                else:
                    style += ",cell.selection"
            return style

        self.container = HSplit(
            [
                VSplit(
                    [
                        self.control,
                        fill(char=border_char("TOP_MID"), height=1),
                        fill(width=1, height=1, char=border_char("TOP_RIGHT")),
                    ],
                    height=1,
                ),
                VSplit(
                    [
                        fill(width=1, char=border_char("MID_LEFT")),
                        HSplit(
                            [input_row, output_row],
                            padding=lambda: 1 if show_input() and show_output() else 0,
                        ),
                        fill(width=1, char=border_char("MID_RIGHT")),
                    ]
                ),
                VSplit(
                    [
                        fill(width=1, height=1, char=border_char("BOTTOM_LEFT")),
                        fill(char=border_char("BOTTOM_MID")),
                        fill(width=1, height=1, char=border_char("BOTTOM_RIGHT")),
                    ],
                    height=1,
                ),
            ],
            style=_style,
        )

        self.kernel_tab.app.create_background_task(self.load_lsps())

    async def load_lsps(self) -> None:
        """Add hooks to the notebook LSP client."""
        path = self.path
        weak_self = weakref.proxy(self)

        # Wait for all lsps to be initialized, and setup hooks as they become ready
        async def _await_load(lsp: LspClient) -> LspClient:
            await lsp.initialized.wait()
            return lsp

        for ready in asyncio.as_completed(
            [_await_load(lsp) for lsp in self.kernel_tab.lsps]
        ):
            lsp = await ready

            # Listen for LSP diagnostics
            lsp.on_diagnostics += weak_self.lsp_update_diagnostics

            open_handler = partial(lambda lsp, tab: self.lsp_open_handler(lsp), lsp)
            change_handler = partial(lambda lsp, tab: self.lsp_change_handler(lsp), lsp)
            close_handler = partial(lambda lsp, tab: self.lsp_close_handler(lsp), lsp)

            self.on_open += open_handler
            self.on_change += change_handler
            self.on_close += close_handler

            # Add completer
            completer = LspCompleter(lsp, path)
            self.completers.append(completer)

            # Add inspector
            inspector = LspInspector(lsp, path)
            self.inspectors.append(inspector)

            # Add formatter
            formatter = LspFormatter(lsp, path)
            self.formatters.append(formatter)

            def lsp_unload(lsp: LspClient) -> None:
                self.on_open -= open_handler  # noqa: B023
                self.on_change -= change_handler  # noqa: B023
                self.on_close -= close_handler  # noqa: B023
                if completer in weak_self.completers:  # noqa: B023
                    self.completers.remove(completer)  # noqa: B023
                if inspector in weak_self.inspectors:  # noqa: B023
                    self.inspectors.remove(inspector)  # noqa: B023
                if formatter in weak_self.formatters:  # noqa: B023
                    self.formatters.remove(formatter)  # noqa: B023

            lsp.on_exit += lsp_unload

            if self.is_new:
                self.on_open()

    @property
    def lsp_cell(self) -> LspCell:
        """Capture the cell's attributes for an LSP server."""
        return LspCell(
            id=self.id,
            idx=self.index,
            path=self.path,
            kind=self.cell_type,
            language=self.language,
            execution_count=self.execution_count,
            metadata=self.json["metadata"],
            text=self.input,
        )

    def lsp_open_handler(self, lsp: LspClient) -> None:
        """If the LSP does not support notebooks, open this cell as a text document."""
        if lsp.can_open_nb:
            lsp.change_nb_add(path=self.kernel_tab.path, cells=[self.lsp_cell])
        else:
            lsp.open_doc(
                path=self.path,
                language=self.language,
                text=self.input_box.buffer.text,
            )

    def lsp_change_handler(self, lsp: LspClient) -> None:
        """Tell the LSP server a cell has changed."""
        if lsp.can_change_nb:
            lsp.change_nb_edit(path=self.kernel_tab.path, cells=[self.lsp_cell])
        else:
            lsp.change_doc(
                path=self.path,
                language=self.language,
                text=self.input_box.buffer.text,
            )

    def lsp_close_handler(self, lsp: LspClient) -> None:
        """Notify the LSP of a deleted cell."""
        if lsp.can_change_nb:
            lsp.change_nb_delete(path=self.kernel_tab.path, cells=[self.lsp_cell])
        else:
            lsp.close_doc(self.path)

    def lsp_update_diagnostics(self, lsp: LspClient) -> None:
        """Process a new diagnostic report from the LSP."""
        if (diagnostics := lsp.reports.pop(self.path.as_uri(), None)) is not None:
            self.reports[lsp] = Report.from_lsp(self.input_box.text, diagnostics)
            self.refresh()

    def report(self) -> Report:
        """Return the current diagnostic reports."""
        return Report.from_reports(*self.reports.values())

    def focus(self, position: int | None = None, scroll: bool = False) -> None:
        """Focus the relevant control in this cell.

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
                    len(self.input_box.buffer.text) + 1
                )
        else:
            to_focus = self.kernel_tab.cell.control

        # We force focus here, bypassing the layout's checks, as the control we want to
        # focus might be not be in the current layout yet.
        self.kernel_tab.app.layout.current_window = to_focus

        # Scroll the currently selected slice into view
        if scroll:
            self.kernel_tab.scroll_to(self.index)

    @property
    def cell_type(self) -> str:
        """Determine the current cell type."""
        return self.json.get("cell_type", "code")

    def suffix(self) -> str:
        """Return the file suffix matching the current cell type."""
        cell_type = self.cell_type
        if cell_type == "markdown":
            return ".md"
        elif cell_type == "raw":
            return ""
        else:
            return self.kernel_tab.kernel_lang_file_ext

    @property
    def execution_count(self) -> int:
        """Retrieve the execution count from the cell's JSON."""
        return self.json.get("execution_count", 0)

    @execution_count.setter
    def execution_count(self, count: int) -> None:
        """Set the execution count in the cell's JSON.

        Args:
            count: The new execution count number.

        """
        self.json["execution_count"] = count

    @property
    def prompt(self) -> str:
        """Determine what should be displayed in the prompt of the cell."""
        if self.state in ("busy", "queued"):
            prompt = "*"
        else:
            prompt = str(self.execution_count or " ")
        if prompt:
            prompt = f"[{prompt}]"
        return prompt

    def _set_input(self, value: str) -> None:
        self.json["source"] = value

    @property
    def input(self) -> str:
        """Fetch the cell's contents from the cell's JSON."""
        return self.json.get("source", "")

    @input.setter
    def input(self, value: str) -> None:
        """Set the cell's contents in the cell's JSON.

        Args:
            value: The new cell contents text.

        """
        cp = self.input_box.buffer.cursor_position
        cp = max(0, min(cp, len(value)))
        self._set_input(value)
        self.input_box.buffer.document = Document(value, cp)

    @property
    def output_json(self) -> list[dict[str, Any]]:
        """Retrieve a list of cell outputs from the cell's JSON."""
        if self.cell_type == "markdown":
            return [
                {"data": {"text/x-markdown": self.input}, "output_type": "markdown"}
            ]
        else:
            return self.json.setdefault("outputs", [])

    def refresh(self, now: bool = True) -> None:
        """Request that the cell to be re-rendered next time it is drawn."""
        self.kernel_tab.refresh_cell(self)
        if now:
            self.kernel_tab.app.invalidate()

    def ran(self, content: dict | None = None) -> None:
        """Update the cell status and update display when the cell has finished."""
        self.state = "idle"
        self.refresh()

    def remove_outputs(self) -> None:
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
        self, cell_type: Literal["markdown", "code", "raw"], clear: bool = False
    ) -> None:
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
        # Trigger callbacks
        self.on_change()
        # Flag notebook as modified
        self.kernel_tab.dirty = True

    @property
    def path(self) -> Path:
        """Return a virtual path for this cell (used by LSP clients).

        Pylance appears to use URIs like:
        ``../folder.notebook.ipynb:pylance-notebook-cell:W0sZmlsZQ==.py``, which I've
        emulated here.
        """
        nb_path = self.kernel_tab.path
        return nb_path.parent / f"{nb_path.name}:cell:{self.id}{self.suffix}"

    @property
    def id(self) -> str:
        """Return the cell's ID as per the cell JSON."""
        return get_cell_id(self.json)

    @property
    def language(self) -> str:
        """Return the cell's code language."""
        if self.cell_type == "markdown":
            return "markdown"
        elif self.cell_type == "code":
            lang_info = self.kernel_tab.metadata.get("language_info", {})
            return lang_info.get("name", lang_info.get("pygments_lexer", "python"))
        else:
            return "raw"

    def run_or_render(
        self,
        buffer: Buffer | None = None,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
    ) -> bool:
        """Send the cell's source code the the kernel to run.

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
                self.input_box.reformat()
            self.state = "queued"
            self.refresh()
            self.kernel_tab.run_cell(self, wait=wait, callback=callback)

        return True

    def __pt_container__(self) -> Container:
        """Return the container which represents this cell."""
        return self.container

    def set_execution_count(self, n: int) -> None:
        """Set the execution count of the cell."""
        self.json["execution_count"] = n
        self.refresh()

    def add_output(self, output_json: dict[str, Any], own: bool) -> None:
        """Add a new output to the cell."""
        # Clear the output if we were previously asked to
        if self.clear_outputs_on_output:
            self.remove_outputs()
        self.json.setdefault("outputs", []).append(output_json)
        # Add the new output to the output area
        self.output_area.add_output(output_json)
        # Tell the page this cell has been updated
        self.refresh()

    def clear_output(self, wait: bool = False) -> None:
        """Remove the cells output, optionally when new output is generated."""
        if wait:
            self.clear_outputs_on_output = True
        else:
            self.remove_outputs()

    def show_input(self) -> None:
        """Set the cell inputs to visible."""
        self.set_metadata(("jupyter", "source_hidden"), False)

    def hide_input(self) -> None:
        """Set the cell inputs to visible."""
        # Exit edit mode
        self.kernel_tab.edit_mode = False
        # Un-focus the cell input
        self.focus()
        # Set the input to hidden
        self.set_metadata(("jupyter", "source_hidden"), True)

    def toggle_input(self) -> None:
        """Toggle the visibility of the cell input."""
        if self.json["metadata"].get("jupyter", {}).get("source_hidden", False):
            self.show_input()
        else:
            self.hide_input()

    def show_output(self) -> None:
        """Set the cell outputs to visible."""
        self.set_metadata(("jupyter", "outputs_hidden"), False)
        self.set_metadata(("collapsed",), False)

    def hide_output(self) -> None:
        """Set the cell outputs to visible."""
        self.set_metadata(("jupyter", "outputs_hidden"), True)
        self.set_metadata(("collapsed",), True)

    def toggle_output(self) -> None:
        """Toggle the visibility of the cell outputs."""
        if self.json["metadata"].get("jupyter", {}).get("outputs_hidden", False):
            self.show_output()
        else:
            self.hide_output()

    def set_metadata(self, path: tuple[str, ...], data: Any) -> None:
        """Set a value in the metadata at an arbitrary path.

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

    def set_status(self, status: str) -> None:
        """Set the execution status of the cell."""

    def get_input(
        self,
        prompt: str = "Please enter a value:",
        password: bool = False,
    ) -> None:
        """Scroll the cell requesting input into view and render it before asking for input."""
        self.kernel_tab.select(self.index)
        self.stdin_box.get_input(prompt, password)

    async def edit_in_editor(self) -> None:
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
                    text = Path(filename).read_text()
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

    def close(self) -> None:
        """Signal that the cell is no longer present in the notebook."""
        self.on_close()
