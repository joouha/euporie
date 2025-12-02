"""Define the global search toolbar and related search functions."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters.app import is_searching
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.layout.controls import BufferControl, SearchBufferControl
from prompt_toolkit.search import SearchDirection
from prompt_toolkit.selection import SelectionState
from prompt_toolkit.widgets import SearchToolbar as PtkSearchToolbar

from euporie.core.app.current import get_app
from euporie.core.bars import SEARCH_BAR_BUFFER
from euporie.core.commands import add_cmd
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)

if TYPE_CHECKING:
    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text.base import AnyFormattedText
    from prompt_toolkit.layout.controls import UIControl

log = logging.getLogger(__name__)


class SearchBar(PtkSearchToolbar):
    """Search mode.

    A search toolbar with custom style and text.
    """

    def __init__(
        self,
        search_buffer: Buffer | None = None,
        vi_mode: bool = False,
        text_if_not_searching: AnyFormattedText = "",
        forward_search_prompt: AnyFormattedText = " Find: ",
        backward_search_prompt: AnyFormattedText = " Find (up): ",
        ignore_case: FilterOrBool = False,
    ) -> None:
        """Create a new search bar instance."""
        if search_buffer is None:
            search_buffer = Buffer(name=SEARCH_BAR_BUFFER)
        super().__init__(
            search_buffer=search_buffer,
            vi_mode=vi_mode,
            text_if_not_searching=text_if_not_searching,
            forward_search_prompt=to_formatted_text(
                forward_search_prompt, "class:status-field"
            ),
            backward_search_prompt=to_formatted_text(
                backward_search_prompt, "class:status-field"
            ),
        )
        self.control.key_bindings = load_registered_bindings(
            "euporie.core.bars.search:SearchBar",
            config=get_app().config,
        )
        search_state = self.control.searcher_search_state
        search_state.ignore_case = Condition(
            lambda: self.search_buffer.text.islower() or search_state.text.islower()
        )

    register_bindings(
        {
            "euporie.core.app.app:BaseApp": {
                "find": ["c-f", "f3", "f7"],
                "find-next": "c-g",
                "find-previous": "c-p",
            },
            "euporie.core.bars.search:SearchBar": {
                "accept-search": "enter",
                "stop-search": "escape",
            },
        }
    )


def find_search_control() -> tuple[SearchBufferControl | None, BufferControl | None]:
    """Find the current search buffer and buffer control."""
    current_buffer_control: BufferControl | None = None
    search_buffer_control: SearchBufferControl | None = None

    app = get_app()
    layout = app.layout
    current_control = app.layout.current_control

    if isinstance(current_control, SearchBufferControl):
        search_buffer_control = current_control

    if search_buffer_control is None and app.search_bar is not None:
        search_buffer_control = app.search_bar.control

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
    """Find list of searchable controls and the index of the next control."""
    # If a tab provides a list of buffers to search, use that. Otherwise, trawl the
    # layout for buffer controls with this as its search control
    long_list: list[UIControl] = []
    if tab := get_app().tab:
        try:
            long_list = [window.content for window in tab.__pt_searchables__()]
        except NotImplementedError:
            long_list = list(get_app().layout.find_all_controls())
    next_control_index = 0
    searchable_controls: list[BufferControl] = []
    for control in long_list:
        # Find the index of the next searchable control so we can link the search
        # control to it if the currently focused control is not searchable. This is so
        # that the next searchable control can be focused when search is completed.
        if control == current_control:
            next_control_index = len(searchable_controls)
        # Only save the control if it is searchable
        if (
            isinstance(control, BufferControl)
            and control.search_buffer_control == search_buffer_control
        ):
            # Add it to our list
            searchable_controls.append(control)
    # Cut list based on current control index
    searchable_controls = (
        searchable_controls[next_control_index:]
        + searchable_controls[:next_control_index]
    )
    return searchable_controls


def start_global_search(
    buffer_control: BufferControl | None = None,
    direction: SearchDirection = SearchDirection.FORWARD,
) -> None:
    """Start a search through all searchable `buffer_controls` in the layout."""
    search_buffer_control, current_control = find_search_control()
    if search_buffer_control is None:
        return
    searchable_controls = find_searchable_controls(
        search_buffer_control, current_control
    )

    # Stop the search if we did not find any searchable controls
    if not searchable_controls:
        return

    # If the current control is searchable, link it
    app = get_app()
    layout = app.layout
    if current_control in searchable_controls:
        assert isinstance(current_control, BufferControl)
        layout.search_links[search_buffer_control] = current_control
    else:
        # otherwise use the next after the currently selected control
        layout.search_links[search_buffer_control] = searchable_controls[0]
    # Make sure to focus the search BufferControl
    layout.focus(search_buffer_control)
    # If we're in Vi mode, make sure to go into insert mode.
    app.vi_state.input_mode = InputMode.INSERT


@add_cmd(menu_title="Find")
def find() -> None:
    """Enter search mode."""
    start_global_search(direction=SearchDirection.FORWARD)


def find_prev_next(direction: SearchDirection) -> None:
    """Find the previous or next search match."""
    if is_searching():
        accept_search()

    search_buffer_control, current_control = find_search_control()
    if search_buffer_control is None:
        return
    searchable_controls = find_searchable_controls(
        search_buffer_control, current_control
    )

    if direction == SearchDirection.BACKWARD:
        searchable_controls = searchable_controls[:1] + searchable_controls[1:][::-1]

    # Search over all searchable buffers
    for i, control in enumerate(searchable_controls):
        # Update search_state.
        search_state = control.search_state
        search_state.direction = direction
        # Apply search to buffer
        buffer = control.buffer

        search_result: tuple[int, int] | None = None

        # If we are searching history, use the PTK buffer search implementation
        if buffer.enable_history_search():
            search_result = buffer._search(search_state)

        # Otherwise, only search the buffer's current "working line"
        else:
            document = buffer.document
            # If have move to the next buffer, set the cursor position for the start of
            # the search to the start or the end of the text, depending on if we are
            # searching forwards or backwards
            if i > 0:
                if direction == SearchDirection.FORWARD:
                    document = Document(document.text, 0)
                else:
                    document = Document(document.text, len(document.text))

            text = search_state.text
            ignore_case = search_state.ignore_case()

            if direction == SearchDirection.FORWARD:
                # Try find at the current input.
                new_index = document.find(
                    text,
                    # If we have moved to the next buffer, include the current position
                    # which will be the start of the document text
                    include_current_position=i > 0,
                    ignore_case=ignore_case,
                )
                if new_index is not None:
                    search_result = (
                        buffer.working_index,
                        document.cursor_position + new_index,
                    )
            else:
                # Try find at the current input.
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
            # Set SelectionState
            buffer.selection_state = SelectionState(
                buffer.cursor_position + len(search_state.text)
            )
            buffer.selection_state.enter_shift_mode()

            # Trigger a cursor position changed event on this buffer
            buffer._cursor_position_changed()

            break


@add_cmd()
def find_next() -> None:
    """Find the next search match."""
    find_prev_next(SearchDirection.FORWARD)


@add_cmd()
def find_previous() -> None:
    """Find the previous search match."""
    find_prev_next(SearchDirection.BACKWARD)


@add_cmd(
    filter=is_searching,
)
def stop_search() -> None:
    """Abort the search."""
    layout = get_app().layout
    buffer_control = layout.search_target_buffer_control
    if buffer_control is None:
        return
    search_buffer_control = buffer_control.search_buffer_control
    # Focus the previous control
    layout.focus(layout.previous_control)
    # Close the search toolbar
    if search_buffer_control is not None:
        del layout.search_links[search_buffer_control]
        # Reset content of search control.
        search_buffer_control.buffer.reset()
    # Redraw everything
    get_app().refresh()


@add_cmd(
    name="accept-search",
    filter=is_searching,
)
def accept_search() -> None:
    """Accept the search input."""
    layout = get_app().layout
    search_buffer_control = layout.current_control
    if not isinstance(search_buffer_control, BufferControl):
        log.debug("Current control not a buffer control")
        return
    for control in layout.find_all_controls():
        if (
            isinstance(control, BufferControl)
            and control.search_buffer_control == search_buffer_control
        ):
            search_state = control.search_state
            # Update search state.
            if search_buffer_control.buffer.text:
                search_state.text = search_buffer_control.buffer.text
            # Apply search.
            control.buffer.apply_search(
                search_state, include_current_position=True, count=1
            )

    # Set selection on target control
    buffer_control = layout.search_target_buffer_control
    if buffer_control and control.is_focusable():
        buffer = buffer_control.buffer
        buffer.selection_state = SelectionState(
            buffer.cursor_position + len(search_state.text)
        )
        buffer.selection_state.enter_shift_mode()

    # Add query to history of search line.
    search_buffer_control.buffer.append_to_history()
    # Stop the search
    stop_search()


@add_cmd()
def _replace_all(find_str: str, replace_str: str) -> None:
    """Find and replace text in all searchable buffers.

    Args:
        find_str: String pattern to find (will be converted to regex)
        replace_str: Replacement string
    """
    # Convert find string to regex pattern
    pattern = re.compile(find_str)

    # Get searchable controls
    search_buffer_control, current_control = find_search_control()
    if search_buffer_control is None:
        return
    searchable_controls = find_searchable_controls(
        search_buffer_control, current_control
    )

    # Apply replacements to each buffer
    for control in searchable_controls:
        if isinstance(control, BufferControl):
            buffer = control.buffer
            text = buffer.text
            new_text = pattern.sub(replace_str, text)
            if new_text != text:
                buffer.text = new_text
                buffer.on_text_changed()
