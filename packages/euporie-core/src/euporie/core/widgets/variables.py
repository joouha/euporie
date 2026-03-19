"""A widget for displaying kernel variables in a sidebar."""

from __future__ import annotations

import logging
import weakref
from functools import cached_property, lru_cache, partial
from typing import TYPE_CHECKING, Any

from apptk.application.current import get_app
from apptk.border import InsetGrid
from apptk.data_structures import DiInt, Point
from apptk.formatted_text.table import Cell, Row, Table
from apptk.formatted_text.utils import split_lines, to_formatted_text
from apptk.layout.containers import MarginContainer, VSplit, Window
from apptk.layout.controls import UIContent, UIControl
from apptk.layout.decor import FocusedStyle
from apptk.layout.dimension import Dimension
from apptk.layout.margins import ScrollbarMargin
from apptk.mouse_events import MouseButton, MouseEventType
from apptk.utils import Event
from apptk.widgets.base import Frame

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from apptk.formatted_text import StyleAndTextTuples
    from apptk.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from apptk.mouse_events import MouseEvent
    from apptk.utils import Event as EventType

    from euporie.core.kernel.base import BaseKernel

log = logging.getLogger(__name__)


class VariableControl(UIControl):
    """A control that displays kernel variables in a table.

    Maintains a per-kernel cache of variable data using weak references, so
    that switching between kernels preserves previously fetched variables.
    When a kernel fires ``on_execution_done``, the control issues a
    non-blocking ``inspect_variables`` call and fires an invalidation event
    when the response arrives.

    Args:
        get_kernel: A callable returning the current kernel instance.
    """

    def __init__(self, get_kernel: Callable[[], BaseKernel | None]) -> None:
        """Initialize the variable control.

        Args:
            get_kernel: A callable returning the current kernel instance.
        """
        self._get_kernel = get_kernel
        self._kernel: BaseKernel | None = None
        self._kernel_variables: weakref.WeakKeyDictionary[
            BaseKernel, list[dict[str, Any]]
        ] = weakref.WeakKeyDictionary()
        self._connected_kernels: weakref.WeakSet[BaseKernel] = weakref.WeakSet()
        self._selected_index: int = 0
        self._hovered_index: int | None = None
        self._lines: list[StyleAndTextTuples] = []
        self.window: Window | None = None
        self._invalidate_event: Event[object] = Event(self)
        self._build_variable_row = lru_cache(maxsize=256)(self._build_variable_row)

        self._table = Table(
            rows=[self._header_row],
            expand=True,
            padding=DiInt(0, 1, 0, 0),
            border_visibility=False,
            alternate_row_style="class:alt",
        )

    @cached_property
    def _header_row(self) -> Row:
        """Return the header row for the variable table."""
        return Row(
            cells=[
                Cell("Name", border_visibility=None, padding=DiInt(0, 1, 0, 1)),
                Cell("Type", border_visibility=None),
                Cell("Value", border_visibility=None),
            ],
            padding=DiInt(0, 1, 0, 0),
            style="class:header",
        )

    def _build_variable_row(
        self, name: str, var_type: str, value: str, selected: bool, hovered: bool
    ) -> Row:
        """Build a table row for a single variable.

        Args:
            name: The variable name.
            var_type: The variable type.
            value: The variable value.
            selected: Is the current row selected.
            hovered: Is the current row hovered.

        Returns:
            A :class:`Row` for the variable.
        """
        new_cell = partial(Cell, border_visibility=None)
        style = ""
        if hovered:
            style += "class:hovered "
        if selected:
            name = [("[SetCursorPosition]", ""), *to_formatted_text(name)]
            style += "class:selection "
        return Row(
            cells=[
                new_cell(
                    name, padding=DiInt(0, 0, 0, 1), style=f"{style} class:name bold"
                ),
                new_cell(var_type, style=f"{style} class:type italic"),
                new_cell(value, style=f"{style} class:value"),
            ],
            table=self._table,
            style="class:row",
        )

    def _update_table(self, variables: list[dict[str, Any]]) -> None:
        """Update the table's rows from a variable list.

        Reuses cached rows via the LRU cache on :meth:`_build_variable_row`.

        Args:
            variables: The list of variable dictionaries to display.
        """
        rows: list[Row] = [self._header_row]

        selected = self._selected_index
        hovered = self._hovered_index
        for i, var in enumerate(variables):
            name = var.get("name", "")
            var_type = var.get("type", "")
            value = var.get("value", "")
            rows.append(
                self._build_variable_row(
                    name, var_type, value, i == selected, i == hovered
                )
            )

        table = self._table
        table._cols.clear()
        table._rows = dict(enumerate(rows))
        table.sync_rows_to_cols()

    def _check_kernel(self) -> None:
        """Check for a change in the active kernel and update subscriptions.

        Subscribes to any newly encountered kernel's ``on_execution_done``
        event. Previous kernel subscriptions are kept alive (via the weak
        reference dictionary) so that results arriving from a background
        kernel are still stored.
        """
        kernel = self._get_kernel()
        if kernel is self._kernel:
            return

        self._kernel = kernel

        if kernel is not None and kernel not in self._connected_kernels:
            kernel.on_execution_done += self._request_variables
            self._connected_kernels.add(kernel)
            # Perform initial request for variables
            self._request_variables(kernel)

    def _request_variables(self, kernel: BaseKernel) -> None:
        """Issue a non-blocking variable inspection request to a kernel.

        The callback stores the result in the per-kernel cache and fires the
        invalidation event so the UI redraws.

        Args:
            kernel: The kernel to query.
        """

        def _on_variables(result: list[dict[str, Any]] | None) -> None:
            self._kernel_variables[kernel] = result or []
            self._invalidate_event()

        kernel.inspect_variables(callback=_on_variables, wait=False)

    @property
    def _variables(self) -> list[dict[str, Any]]:
        """Return the cached variables for the active kernel.

        Returns:
            The list of variable dictionaries, or an empty list.
        """
        if self._kernel is not None:
            return self._kernel_variables.get(self._kernel, [])
        return []

    def is_focusable(self) -> bool:
        """Return whether this control is focusable."""
        return True

    def preferred_width(self, max_available_width: int) -> int | None:
        """Return the preferred width for this control.

        Args:
            max_available_width: The maximum width available.

        Returns:
            ``None`` to use all available space.
        """
        return None

    def create_content(self, width: int, height: int) -> UIContent:
        """Create the UI content by rendering the table at the given width.

        Checks for kernel changes, then renders the variable table.

        Args:
            width: The available width in terminal columns.
            height: The available height in terminal rows.

        Returns:
            A :class:`UIContent` instance with the rendered table lines.
        """
        self._check_kernel()

        variables = self._variables

        # Clamp selected index
        if variables:
            self._selected_index = min(self._selected_index, len(variables) - 1)
        else:
            self._selected_index = 0

        self._update_table(variables)

        ft = self._table.render(Dimension(preferred=width, max=width))
        self._lines = lines = list(split_lines(ft))
        line_count = len(self._lines)

        def get_line(i: int) -> StyleAndTextTuples:
            if 0 <= i < line_count:
                return self._lines[i]
            return []

        # Get cursor position
        cursor_position: Point | None = None
        for y, line in enumerate(lines):
            for frag in line:
                if "[SetCursorPosition]" in frag[0]:
                    cursor_position = Point(0, y)

        return UIContent(
            get_line=get_line,
            line_count=line_count,
            cursor_position=cursor_position,
            show_cursor=True,
        )

    def _row_from_mouse(self, mouse_event: MouseEvent) -> int | None:
        """Map a mouse event's y position to a variable index.

        The first row of the table is the header, so row 0 in the content
        maps to variable index -1 (header). Variable indices start at 0 for
        the second rendered row.

        Args:
            mouse_event: The mouse event.

        Returns:
            The variable index, or ``None`` if outside the variable rows.
        """
        variables = self._variables
        if not variables:
            return None
        # Account for the header row (row 0 in the rendered table)
        row = mouse_event.position.y
        # The header occupies the first line(s); variable rows start after.
        # Since each row is one line in the table, row index 1 = variable 0.
        var_index = row - 1
        if 0 <= var_index < len(variables):
            return var_index
        return None

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events.

        Supports clicking to select, hovering to highlight, and scrolling.

        Args:
            mouse_event: The mouse event instance.
        """
        if (
            mouse_event.button == MouseButton.LEFT
            and mouse_event.event_type == MouseEventType.MOUSE_DOWN
        ):
            app = get_app()
            app.layout.current_control = self
            var_index = self._row_from_mouse(mouse_event)
            if var_index is not None:
                self._hovered_index = None
                self._selected_index = var_index
            return None

        elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            var_index = self._row_from_mouse(mouse_event)
            if var_index is not None and var_index != self._hovered_index:
                self._hovered_index = var_index
                return None
            return NotImplemented

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.move_cursor_up()
            return None

        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.move_cursor_down()
            return None

        return NotImplemented

    def move_cursor_down(self) -> None:
        """Move selection to the next variable."""
        variables = self._variables
        if variables:
            self._selected_index = min(self._selected_index + 1, len(variables) - 1)

    def move_cursor_up(self) -> None:
        """Move selection to the previous variable."""
        variables = self._variables
        if variables:
            self._selected_index = max(self._selected_index - 1, 0)

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Key bindings that are specific for this user control.

        Return a :class:`.KeyBindings` object if some key bindings are
        specified, or `None` otherwise.
        """

    def get_invalidate_events(self) -> Iterable[EventType[object]]:
        """Return a list of `Event` objects.

        The application collects all these events in order to bind redraw
        handlers to them. When the invalidation event fires (after variable
        data arrives from a kernel), the UI will redraw.
        """
        return [self._invalidate_event]


class VariableList:
    """A widget that displays the current kernel's variables.

    Wraps a :class:`VariableControl` in a :class:`Window` for layout
    integration.

    Args:
        kernel: A callable returning the current kernel instance.
    """

    def __init__(self, kernel: Callable[[], BaseKernel | None]) -> None:
        """Initialize the variable list widget.

        Args:
            kernel: A callable returning the current kernel instance.
        """
        self.control = VariableControl(get_kernel=kernel)
        window = Window(
            content=self.control, wrap_lines=False, style="class:input,list,face"
        )
        self.control.window = window
        self.container = Frame(
            VSplit(
                [
                    FocusedStyle(window),
                    MarginContainer(ScrollbarMargin(), target=window),
                ]
            ),
            border=InsetGrid,
        )

    def __pt_container__(self) -> Window:
        """Return the apptk container for this widget.

        Returns:
            The container for layout integration.
        """
        return self.container
