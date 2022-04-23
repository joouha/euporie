"""Defines commands related to searching."""
import logging
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import is_searching
from prompt_toolkit.layout.controls import BufferControl, SearchBufferControl
from prompt_toolkit.search import SearchDirection, start_search

from euporie.commands.registry import add
from euporie.filters import in_edit_mode

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.layout.controls import UIControl

log = logging.getLogger(__name__)


@add(
    name="find",
    menu_title="Find in cell",
    filter=in_edit_mode,
    group="edit-mode",
)
def find() -> "None":
    """Enter search mode."""
    start_search(direction=SearchDirection.FORWARD)


def find_prev_next(direction: "SearchDirection") -> "None":
    """Find the previous or next search match."""
    layout = get_app().layout
    control: "Optional[UIControl]" = layout.current_control
    if isinstance(control, SearchBufferControl):
        control = layout.search_target_buffer_control
    if not isinstance(control, BufferControl):
        return
    # Update search_state.
    search_state = control.search_state
    search_state.direction = direction
    # Apply search to current buffer.
    control.buffer.apply_search(search_state, include_current_position=False, count=1)


@add(group="app")
def find_next() -> "None":
    """Find the next search match."""
    find_prev_next(SearchDirection.FORWARD)


@add(group="edit-mode")
def find_previous() -> "None":
    """Find the previous search match."""
    find_prev_next(SearchDirection.BACKWARD)


# Search mode commands


@add(
    filter=is_searching,
    group="search-mode",
)
def stop_search() -> "None":
    """Abort the search."""
    layout = get_app().layout
    buffer_control = layout.search_target_buffer_control
    if buffer_control is None:
        return
    search_buffer_control = buffer_control.search_buffer_control
    # Focus the original buffer again.
    layout.focus(buffer_control)
    # Close the search toolbar
    if search_buffer_control is not None:
        del layout.search_links[search_buffer_control]
        # Reset content of search control.
        search_buffer_control.buffer.reset()


@add(
    name="accept-search",
    group="search-mode",
    filter=is_searching,
)
def accept_search() -> "None":
    """Accept the search input."""
    layout = get_app().layout
    search_control = layout.current_control
    target_buffer_control = layout.search_target_buffer_control
    if not isinstance(search_control, BufferControl):
        return
    if target_buffer_control is None:
        return
    search_state = target_buffer_control.search_state
    # Update search state.
    if search_control.buffer.text:
        search_state.text = search_control.buffer.text
    # Apply search.
    target_buffer_control.buffer.apply_search(
        search_state, include_current_position=True
    )
    # Add query to history of search line.
    search_control.buffer.append_to_history()
    # Stop the search
    stop_search()
