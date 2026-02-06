"""Define an application menu."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app
from euporie.apptk.formatted_text.base import to_formatted_text
from euporie.apptk.layout.dimension import Dimension
from euporie.apptk.layout.menus import (
    CompletionsMenuControl as PtkCompletionsMenuControl,
)

from euporie.apptk.border import OuterHalfGrid
from euporie.apptk.data_structures import Point
from euporie.apptk.filters import (
    has_completions,
    is_done,
    to_filter,
)
from euporie.apptk.formatted_text.utils import (
    fragment_list_width,
)
from euporie.apptk.layout.containers import (
    ConditionalContainer,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
)
from euporie.apptk.layout.controls import UIContent
from euporie.apptk.mouse_events import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.formatted_text.base import (
        StyleAndTextTuples,
    )

    from euporie.apptk.filters import FilterOrBool
    from euporie.apptk.key_binding.key_bindings import NotImplementedOrNone


log = logging.getLogger(__name__)


class CompletionsMenuControl(PtkCompletionsMenuControl):
    """A custom completions menu control."""

    def create_content(self, width: int, height: int) -> UIContent:
        """Create a UIContent object for this control."""
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            completions = complete_state.completions
            index = complete_state.complete_index  # Can be None!

            # Calculate width of completions menu.
            menu_width = self._get_menu_width(width, complete_state)
            menu_meta_width = self._get_menu_meta_width(
                width - menu_width, complete_state
            )
            total_width = menu_width + menu_meta_width

            grid = OuterHalfGrid

            def get_line(i: int) -> StyleAndTextTuples:
                c = completions[i]
                selected_item = i == index
                output: StyleAndTextTuples = []

                style = "class:menu"
                if selected_item:
                    style += ",selection"

                output.append((f"{style},border", grid.MID_LEFT))
                if selected_item:
                    output.append(("[SetCursorPosition]", ""))
                # Construct the menu item contents
                padding = " " * (
                    total_width
                    - fragment_list_width(c.display)
                    - fragment_list_width(c.display_meta)
                    - 2
                )
                output.extend(
                    to_formatted_text(
                        [
                            *c.display,
                            ("", padding),
                            *to_formatted_text(
                                c.display_meta, style=f"{style} {c.style}"
                            ),
                        ],
                        style=style,
                    )
                )
                output.append((f"{style},border", grid.MID_RIGHT))

                # Apply mouse handler
                return [
                    (fragment[0], fragment[1], self.mouse_handler)
                    for fragment in output
                ]

            return UIContent(
                get_line=get_line,
                cursor_position=Point(x=0, y=index or 0),
                line_count=len(completions),
            )

        return UIContent()

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events: clicking and scrolling."""
        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            # Set completion
            complete_state = get_app().current_buffer.complete_state
            if complete_state:
                complete_state.complete_index = mouse_event.position.y
                return None

        return super().mouse_handler(mouse_event)


class CompletionsMenu(ConditionalContainer):
    """A custom completions menu."""

    def __init__(
        self,
        max_height: int | None = 16,
        scroll_offset: int | Callable[[], int] = 1,
        extra_filter: FilterOrBool = True,
    ) -> None:
        """Create a completions menu with borders."""
        extra_filter = to_filter(extra_filter)
        grid = OuterHalfGrid
        super().__init__(
            content=HSplit(
                [
                    VSplit(
                        [
                            Window(char=grid.TOP_LEFT, width=1, height=1),
                            Window(char=grid.TOP_MID, height=1),
                            Window(char=grid.TOP_RIGHT, width=1, height=1),
                        ],
                        style="class:border",
                    ),
                    Window(
                        content=CompletionsMenuControl(),
                        width=Dimension(min=8),
                        height=Dimension(min=1, max=max_height),
                        scroll_offsets=ScrollOffsets(
                            top=scroll_offset, bottom=scroll_offset
                        ),
                        dont_extend_width=True,
                    ),
                    VSplit(
                        [
                            Window(char=grid.BOTTOM_LEFT, width=1, height=1),
                            Window(char=grid.BOTTOM_MID, height=1),
                            Window(char=grid.BOTTOM_RIGHT, width=1, height=1),
                        ],
                        style="class:border",
                    ),
                ],
                style="class:menu",
            ),
            # Show when there are completions but not at the point we are
            # returning the input.
            filter=has_completions & ~is_done & extra_filter,
        )
