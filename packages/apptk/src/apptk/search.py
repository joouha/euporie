"""Global search operations for apptk.

Extends prompt_toolkit's search module with global search functions that
search across multiple buffer controls in the layout.

For single-buffer search, use the original prompt_toolkit functions
(``start_search``, ``stop_search``, ``accept_search``).

For cross-buffer search (e.g., searching across all cells in a notebook),
use the global variants (``start_global_search``, ``stop_global_search``,
``accept_global_search``, ``find_next_match``).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.commands import add_cmd
from apptk.document import Document
from apptk.filters.app import is_searching
from apptk.key_binding.vi_state import InputMode
from prompt_toolkit.search import (
    SearchDirection,
    accept_search,
    do_incremental_search,
    start_search,
    stop_search,
)

if TYPE_CHECKING:
    from apptk.layout.controls import BufferControl, SearchBufferControl, UIControl

__all__ = [
    "accept_global_search",
    "accept_search",
    "do_incremental_search",
    "find_next_match",
    "find_search_control",
    "find_searchable_controls",
    "replace_all",
    "start_global_search",
    "start_search",
    "stop_global_search",
    "stop_search",
]

log = logging.getLogger(__name__)


def find_search_control() -> tuple[SearchBufferControl | None, BufferControl | None]:
    """Find the current search buffer and buffer control.

    Returns:
        Tuple of (search_buffer_control, current_buffer_control).
    """
    from apptk.layout.controls import BufferControl, SearchBufferControl

    current_buffer_control: BufferControl | None = None
    search_buffer_control: SearchBufferControl | None = None

    app = get_app()
    layout = app.layout
    current_control = app.layout.current_control

    if isinstance(current_control, SearchBufferControl):
        search_buffer_control = current_control

    if search_buffer_control is None:
        search_bar = getattr(app, "search_bar", None)
        if search_bar is not None:
            search_buffer_control = search_bar.control

    if search_buffer_control is not None and current_buffer_control is None:
        current_buffer_control = layout.search_links.get(search_buffer_control)

    if current_buffer_control is None and isinstance(current_control, BufferControl):
        current_buffer_control = current_control

    if (
        search_buffer_control is None
        and current_buffer_control is not None
        and current_buffer_control.search_buffer_control is not None
    ):
        search_buffer_control = current_buffer_control.search_buffer_control

    return search_buffer_control, current_buffer_control


def find_searchable_controls(
    search_buffer_control: SearchBufferControl, current_control: BufferControl | None
) -> list[BufferControl]:
    """Find list of searchable controls ordered from the current control.

    If the current app's tab provides a ``__pt_searchables__`` method, use that.
    Otherwise, trawl the layout for buffer controls with the given search control.

    Args:
        search_buffer_control: The search buffer control to match against.
        current_control: The currently focused buffer control.

    Returns:
        List of searchable buffer controls, ordered starting from the current.
    """
    from apptk.layout.controls import BufferControl

    long_list: list[UIControl] = []
    # TODO - walk through layout instead
    app = get_app()
    tab = getattr(app, "tab", None)
    if tab is not None:
        try:
            long_list = [window.content for window in tab.__pt_searchables__()]
        except (NotImplementedError, AttributeError):
            long_list = list(app.layout.find_all_controls())
    else:
        long_list = list(app.layout.find_all_controls())

    next_control_index = 0
    searchable_controls: list[BufferControl] = []
    for control in long_list:
        if control == current_control:
            next_control_index = len(searchable_controls)
        if (
            isinstance(control, BufferControl)
            and control.search_buffer_control == search_buffer_control
        ):
            searchable_controls.append(control)

    searchable_controls = (
        searchable_controls[next_control_index:]
        + searchable_controls[:next_control_index]
    )
    return searchable_controls


def start_global_search(
    buffer_control: BufferControl | None = None,
    direction: SearchDirection = SearchDirection.FORWARD,
) -> None:
    """Start a search through all searchable buffer controls in the layout.

    Args:
        buffer_control: Optional specific buffer control to start from.
        direction: The search direction.
    """
    from apptk.layout.controls import BufferControl

    search_buffer_control, current_control = find_search_control()
    if search_buffer_control is None:
        return
    searchable_controls = find_searchable_controls(
        search_buffer_control, current_control
    )

    if not searchable_controls:
        return

    app = get_app()
    layout = app.layout
    if current_control in searchable_controls:
        assert isinstance(current_control, BufferControl)
        target = current_control
    else:
        target = searchable_controls[0]

    # Set the search direction on the target control's search state
    # so that highlight processors (SearchHighlightProcessor,
    # HighlightIncrementalSearchProcessor) can display matches.
    target.search_state.direction = direction

    layout.search_links[search_buffer_control] = target
    layout.focus(search_buffer_control)
    app.vi_state.input_mode = InputMode.INSERT
    app.helix_state.input_mode = InputMode.INSERT


def stop_global_search() -> None:
    """Abort the current global search and refocus the previous control."""
    app = get_app()
    layout = app.layout
    buffer_control = layout.search_target_buffer_control
    if buffer_control is None:
        return
    search_buffer_control = buffer_control.search_buffer_control

    # Focus the linked buffer control (which may have been updated to point
    # at the control containing the match) rather than ``previous_control``
    # which might not be the buffer where the match was found.
    layout.focus(buffer_control)

    if search_buffer_control is not None:
        del layout.search_links[search_buffer_control]
        search_buffer_control.buffer.reset()

    app.refresh()


def accept_global_search() -> None:
    """Accept the current search input and apply to all searchable buffers."""
    from apptk.layout.controls import BufferControl
    from apptk.selection import SelectionState

    app = get_app()
    layout = app.layout
    search_buffer_control = layout.current_control
    if not isinstance(search_buffer_control, BufferControl):
        log.debug("Current control not a buffer control")
        return

    search_state = None
    matched_control: BufferControl | None = None
    for control in layout.find_all_controls():
        if (
            isinstance(control, BufferControl)
            and control.search_buffer_control == search_buffer_control
        ):
            search_state = control.search_state
            if search_buffer_control.buffer.text:
                search_state.text = search_buffer_control.buffer.text
            old_cursor = control.buffer.cursor_position
            control.buffer.apply_search(
                search_state, include_current_position=True, count=1
            )
            if matched_control is None and control.buffer.cursor_position != old_cursor:
                matched_control = control

    # Use the control where a match was found, falling back to the search target
    target_control = matched_control or layout.search_target_buffer_control
    if target_control and search_state and target_control.is_focusable():
        buffer = target_control.buffer
        buffer.selection_state = SelectionState(
            buffer.cursor_position + len(search_state.text)
        )
        buffer.selection_state.enter_shift_mode()

    search_buffer_control.buffer.append_to_history()

    # Focus the matched control before stopping the search so that
    # stop_global_search refocuses the correct buffer
    if target_control is not None:
        layout.search_links[search_buffer_control] = target_control

    stop_global_search()


def find_next_match(direction: SearchDirection) -> None:
    """Find the previous or next search match across all searchable buffers.

    If currently searching, accepts the search first. Then navigates to the
    next match in the given direction, searching across multiple buffers.

    Args:
        direction: The direction to search.
    """
    from apptk.selection import SelectionState

    if is_searching():
        accept_global_search()

    search_buffer_control, current_control = find_search_control()
    if search_buffer_control is None:
        return
    searchable_controls = find_searchable_controls(
        search_buffer_control, current_control
    )

    if direction == SearchDirection.BACKWARD:
        searchable_controls = searchable_controls[:1] + searchable_controls[1:][::-1]

    for i, control in enumerate(searchable_controls):
        search_state = control.search_state
        search_state.direction = direction
        buffer = control.buffer

        search_result: tuple[int, int] | None = None

        if buffer.enable_history_search():
            search_result = buffer._search(search_state)
        else:
            document = buffer.document
            if i > 0:
                if direction == SearchDirection.FORWARD:
                    document = Document(document.text, 0)
                else:
                    document = Document(document.text, len(document.text))

            text = search_state.text
            ignore_case = search_state.ignore_case()

            if direction == SearchDirection.FORWARD:
                new_index = document.find(
                    text,
                    include_current_position=i > 0,
                    ignore_case=ignore_case,
                )
                if new_index is not None:
                    search_result = (
                        buffer.working_index,
                        document.cursor_position + new_index,
                    )
            else:
                new_index = document.find_backwards(text, ignore_case=ignore_case)
                if new_index is not None:
                    search_result = (
                        buffer.working_index,
                        document.cursor_position + new_index,
                    )

        if search_result is not None:
            working_index, cursor_position = search_result
            buffer.working_index = working_index
            buffer.cursor_position = cursor_position
            buffer.selection_state = SelectionState(
                buffer.cursor_position + len(search_state.text)
            )
            buffer.selection_state.enter_shift_mode()
            buffer._cursor_position_changed()
            break


# Register mode-independent search commands for use by SearchToolbar


@add_cmd(menu_title="Find")
def find() -> None:
    """Enter search mode."""
    start_global_search(direction=SearchDirection.FORWARD)


@add_cmd(name="accept-search", filter=is_searching, keys=["enter"])
def _accept_search_cmd() -> None:
    """Accept the search input."""
    accept_global_search()


@add_cmd(name="stop-search", filter=is_searching, keys=["escape"])
def _stop_search_cmd() -> None:
    """Abort the search."""
    stop_global_search()


@add_cmd(aliases=["replace-all"])
def replace_all(find_str: str, replace_str: str) -> None:
    """Find and replace text in all searchable buffers.

    Args:
        find_str: String pattern to find (will be converted to regex).
        replace_str: Replacement string.
    """
    from apptk.layout.controls import BufferControl

    find_str = str(find_str)
    replace_str = str(replace_str)

    pattern = re.compile(find_str)

    search_buffer_control, current_control = find_search_control()
    if search_buffer_control is None:
        return
    searchable_controls = find_searchable_controls(
        search_buffer_control, current_control
    )

    for control in searchable_controls:
        if isinstance(control, BufferControl):
            buffer = control.buffer
            text = buffer.text
            new_text = pattern.sub(replace_str, text)
            if new_text != text:
                buffer.text = new_text
                buffer.on_text_changed()
