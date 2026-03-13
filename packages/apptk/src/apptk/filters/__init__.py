"""Filters for determining boolean state in the application.

Filters decide whether something is active or not (they decide about a boolean
state). This is used to enable/disable features, like key bindings, parts of
the layout and other stuff.

Filters can be chained using ``&`` and ``|`` operations, and inverted using the
``~`` operator, for instance::

    filter = has_focus("default") & ~has_selection
"""

from __future__ import annotations

from apptk.filters.app import display_has_focus, has_toolbar, scrollable
from apptk.filters.buffer import (
    at_end_of_buffer,
    buffer_is_code,
    buffer_is_empty,
    buffer_is_markdown,
    buffer_name_is,
    char_after_cursor,
    cursor_at_end_of_line,
    cursor_at_start_of_line,
    cursor_in_leading_ws,
    cursor_on_first_line,
    cursor_on_last_line,
    has_matching_bracket,
    has_suggestion,
    is_returnable,
)
from apptk.filters.environment import (
    command_exists,
    have_modules,
    in_mplex,
    in_screen,
    in_tmux,
)
from apptk.filters.modes import (
    exitable_mode,
    helix_insert_mode,
    helix_mode,
    helix_navigation_mode,
    helix_replace_mode,
    insert_mode,
    micro_insert_mode,
    micro_mode,
    micro_recording_macro,
    micro_replace_mode,
    navigation_mode,
    replace_mode,
)

__all__ = [
    "at_end_of_buffer",
    "buffer_is_code",
    "buffer_is_empty",
    "buffer_is_markdown",
    "buffer_name_is",
    "char_after_cursor",
    "command_exists",
    "cursor_at_end_of_line",
    "cursor_at_start_of_line",
    "cursor_in_leading_ws",
    "cursor_on_first_line",
    "cursor_on_last_line",
    "display_has_focus",
    "exitable_mode",
    "has_matching_bracket",
    "has_suggestion",
    "has_toolbar",
    "have_modules",
    "helix_insert_mode",
    "helix_mode",
    "helix_navigation_mode",
    "helix_replace_mode",
    "in_mplex",
    "in_screen",
    "in_tmux",
    "insert_mode",
    "is_returnable",
    "micro_insert_mode",
    "micro_mode",
    "micro_recording_macro",
    "micro_replace_mode",
    "navigation_mode",
    "replace_mode",
    "scrollable",
]
