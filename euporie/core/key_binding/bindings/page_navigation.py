"""Define page navigation key-bindings for buffers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import buffer_has_focus
from prompt_toolkit.key_binding.bindings.page_navigation import (
    load_emacs_page_navigation_bindings,
    load_vi_page_navigation_bindings,
)
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    merge_key_bindings,
)

from euporie.core.commands import add_cmd
from euporie.core.filters import micro_mode
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase, KeyPressEvent

    from euporie.core.config import Config

log = logging.getLogger(__name__)


class PageNavigation:
    """Key-bindings for page navigation."""

    # Register default bindings for micro edit mode
    register_bindings(
        {
            "euporie.core.key_binding.bindings.page_navigation:PageNavigation": {
                "scroll-page-up": "pageup",
                "scroll-page-down": "pagedown",
            },
        }
    )


def load_page_navigation_bindings(config: Config | None = None) -> KeyBindingsBase:
    """Load page navigation key-bindings for text entry."""
    return ConditionalKeyBindings(
        merge_key_bindings(
            [
                load_emacs_page_navigation_bindings(),
                load_vi_page_navigation_bindings(),
                ConditionalKeyBindings(
                    load_registered_bindings(
                        "euporie.core.key_binding.bindings.page_navigation:PageNavigation",
                        config=config,
                    ),
                    micro_mode,
                ),
            ]
        ),
        buffer_has_focus,
    )


# Commands


@add_cmd(filter=buffer_has_focus, hidden=True)
def scroll_page_down(event: KeyPressEvent) -> None:
    """Scroll page down (prefer the cursor at the top of the page, after scrolling)."""
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w and w.render_info:
        # Scroll down one page.
        line_index = b.document.cursor_position_row
        page = w.render_info.window_height

        if (
            (screen := get_app().renderer._last_screen)
            and (wp := screen.visible_windows_to_write_positions.get(w))
            and (bbox := getattr(wp, "bbox", None))
        ):
            page -= bbox.top + bbox.bottom

        line_index = max(line_index + page, w.vertical_scroll + 1)
        w.vertical_scroll = line_index

        b.cursor_position = b.document.translate_row_col_to_index(line_index, 0)
        b.cursor_position += b.document.get_start_of_line_position(
            after_whitespace=True
        )


@add_cmd(filter=buffer_has_focus, hidden=True)
def scroll_page_up(event: KeyPressEvent) -> None:
    """Scroll page up (prefer the cursor at the bottom of the page, after scrolling)."""
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w and w.render_info:
        line_index = b.document.cursor_position_row
        page = w.render_info.window_height

        if (
            (screen := get_app().renderer._last_screen)
            and (wp := screen.visible_windows_to_write_positions.get(w))
            and (bbox := getattr(wp, "bbox", None))
        ):
            page -= bbox.top + bbox.bottom

        # Put cursor at the first visible line. (But make sure that the cursor
        # moves at least one line up.)
        line_index = max(
            0,
            min(line_index - page, b.document.cursor_position_row - 1),
        )

        b.cursor_position = b.document.translate_row_col_to_index(line_index, 0)
        b.cursor_position += b.document.get_start_of_line_position(
            after_whitespace=True
        )

        # Set the scroll offset. We can safely set it to zero; the Window will
        # make sure that it scrolls at least until the cursor becomes visible.
        w.vertical_scroll = 0
