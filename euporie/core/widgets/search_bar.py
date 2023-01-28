"""Defines the global search toolbar and related search functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters.app import is_searching
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.layout.controls import BufferControl, SearchBufferControl
from prompt_toolkit.search import SearchDirection
from prompt_toolkit.widgets import SearchToolbar as PtkSearchToolbar

from euporie.core.commands import add_cmd
from euporie.core.current import get_app
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text.base import AnyFormattedText

log = logging.getLogger(__name__)


class SearchBar(PtkSearchToolbar):
    """Search mode.

    A search toolbar with custom style and text.
    """

    def __init__(
        self,
        search_buffer: "Optional[Buffer]" = None,
        vi_mode: "bool" = False,
        text_if_not_searching: "AnyFormattedText" = "",
        forward_search_prompt: "AnyFormattedText" = "I-search: ",
        backward_search_prompt: "AnyFormattedText" = "I-search backward: ",
        ignore_case: "FilterOrBool" = False,
    ) -> "None":
        """Create a new search bar instance."""
        super().__init__(
            text_if_not_searching="",
            forward_search_prompt=[
                ("class:search-toolbar.title", " Find: "),
                ("", " "),
            ],
            backward_search_prompt=[
                ("class:search-toolbar.title", " Find (up): "),
                ("", " "),
            ],
        )
        self.control.key_bindings = load_registered_bindings(
            "euporie.core.widgets.search_bar.SearchBar"
        )


def start_global_search(
    buffer_control: "Optional[BufferControl]" = None,
    direction: "SearchDirection" = SearchDirection.FORWARD,
) -> "None":
    """Start a search through all searchable `buffer_controls` in the layout."""
    app = get_app()
    layout = app.layout
    current_control = layout.current_control
    # Find the search buffer control
    if app.search_bar is not None:
        search_buffer_control = app.search_bar.control
    elif (
        isinstance(current_control, BufferControl)
        and current_control.search_buffer_control is not None
    ):
        search_buffer_control = current_control.search_buffer_control
    else:
        return
    # Find all searchable controls
    searchable_controls: "list[BufferControl]" = []
    next_control_index = 0
    for control in layout.find_all_controls():
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
            # Set its search direction
            control.search_state.direction = direction
            # Add it to our list
            searchable_controls.append(control)
    # Stop the search if we did not find any searchable controls
    if not searchable_controls:
        return

    # If the current control is searchable, link it
    if current_control in searchable_controls:
        assert isinstance(current_control, BufferControl)
        layout.search_links[search_buffer_control] = current_control
    else:
        # otherwise use the next after the currently selected control
        layout.search_links[search_buffer_control] = searchable_controls[
            next_control_index % len(searchable_controls)
        ]
    # Make sure to focus the search BufferControl
    layout.focus(search_buffer_control)
    # If we're in Vi mode, make sure to go into insert mode.
    app.vi_state.input_mode = InputMode.INSERT


@add_cmd(
    menu_title="Find",
    # filter=control_is_searchable,
)
def find() -> "None":
    """Enter search mode."""
    start_global_search(direction=SearchDirection.FORWARD)


def find_prev_next(direction: "SearchDirection") -> "None":
    """Find the previous or next search match."""
    app = get_app()
    layout = app.layout
    control = app.layout.current_control
    # Determine search buffer and searched buffer
    search_buffer_control = None
    if isinstance(control, SearchBufferControl):
        search_buffer_control = control
        control = layout.search_links[search_buffer_control]
    elif isinstance(control, BufferControl):
        if control.search_buffer_control is not None:
            search_buffer_control = control.search_buffer_control
    elif app.search_bar is not None:
        search_buffer_control = app.search_bar.control
    if isinstance(control, BufferControl) and search_buffer_control is not None:
        # Update search_state.
        search_state = control.search_state
        search_state.direction = direction
        # Apply search to buffer
        control.buffer.apply_search(
            search_state, include_current_position=False, count=1
        )
    # break


@add_cmd()
def find_next() -> "None":
    """Find the next search match."""
    find_prev_next(SearchDirection.FORWARD)


@add_cmd()
def find_previous() -> "None":
    """Find the previous search match."""
    find_prev_next(SearchDirection.BACKWARD)


@add_cmd(
    filter=is_searching,
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
    # Redraw everything
    get_app().refresh()


@add_cmd(
    name="accept-search",
    filter=is_searching,
)
def accept_search() -> "None":
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
            control.buffer.apply_search(search_state, include_current_position=True)
    # Add query to history of search line.
    search_buffer_control.buffer.append_to_history()
    # Stop the search
    stop_search()


register_bindings(
    {
        "euporie.core.app.BaseApp": {
            "find": ["c-f", "f3", "f7"],
            "find-next": "c-g",
            "find-previous": "c-p",
        },
        "euporie.core.widgets.search_bar.SearchBar": {
            "accept-search": "enter",
            "stop-search": "escape",
        },
    }
)
