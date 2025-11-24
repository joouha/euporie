"""Decorative widgets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters import to_filter
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
)
from prompt_toolkit.widgets.base import Label

from euporie.core.app.current import get_app
from euporie.core.border import ThinLine
from euporie.core.data_structures import DiBool
from euporie.core.layout.containers import DummyContainer, HSplit, VSplit, Window
from euporie.core.layout.decor import DropShadow

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompt_toolkit.formatted_text.base import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.border import GridStyle

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class Border:
    """Draw a border around any container."""

    def __init__(
        self,
        body: AnyContainer,
        border: GridStyle | None = ThinLine.grid,
        style: str | Callable[[], str] = "class:border",
        show_borders: DiBool | None = None,
        title: AnyFormattedText | None = None,
    ) -> None:
        """Create a new border widget which wraps another container.

        Args:
            body: The container to surround with a border
            border: The grid style to use
            style: The style to apply to the border
            show_borders: Which of the four borders should be displayed
            title: Optional text to make a frame

        """
        self.body = body
        self.style = style

        if show_borders:
            show_borders = DiBool(*show_borders)
        else:
            show_borders = DiBool(True, True, True, True)
        border_top = to_filter(show_borders.top)
        border_right = to_filter(show_borders.right)
        border_bottom = to_filter(show_borders.bottom)
        border_left = to_filter(show_borders.left)

        self.container: AnyContainer
        if border is not None and any(show_borders):
            top_edge: AnyContainer = Window(
                char=border.TOP_MID, style=self.add_style("class:top")
            )
            if title:
                top_edge = VSplit(
                    [
                        top_edge,
                        Window(width=1, height=1),
                        Label(title, dont_extend_width=True),
                        Window(width=1, height=1),
                        top_edge,
                    ]
                )

            self.container = HSplit(
                [
                    ConditionalContainer(
                        VSplit(
                            [
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.TOP_LEFT,
                                        style=self.add_style("class:left,top"),
                                    ),
                                    filter=border_top & border_left,
                                ),
                                ConditionalContainer(
                                    top_edge,
                                    filter=border_top,
                                ),
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.TOP_RIGHT,
                                        style=self.add_style("class:right,top"),
                                    ),
                                    filter=border_top & border_right,
                                ),
                            ],
                            height=1,
                        ),
                        filter=border_top,
                    ),
                    VSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_LEFT,
                                    style=self.add_style("class:left"),
                                ),
                                filter=border_left,
                            ),
                            DynamicContainer(lambda: self.body),
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_RIGHT,
                                    style=self.add_style("class:right"),
                                ),
                                filter=border_right,
                            ),
                            # Padding is required to make sure that if the content is
                            # too small, the right frame border is still aligned.
                        ],
                        padding=0,
                    ),
                    ConditionalContainer(
                        VSplit(
                            [
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.BOTTOM_LEFT,
                                        style=self.add_style("class:left,bottom"),
                                    ),
                                    filter=border_bottom & border_left,
                                ),
                                ConditionalContainer(
                                    Window(
                                        char=border.BOTTOM_MID,
                                        style=self.add_style("class:bottom"),
                                    ),
                                    filter=border_bottom,
                                ),
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.BOTTOM_RIGHT,
                                        style=self.add_style("class:right,bottom"),
                                    ),
                                    filter=border_bottom & border_right,
                                ),
                            ],
                            # specifying height here will increase the rendering speed.
                            height=1,
                        ),
                        filter=border_bottom,
                    ),
                ],
            )
        else:
            self.container = body

    def add_style(self, extra: str) -> Callable[[], str]:
        """Return a function which adds a style string to the border style."""

        def _style() -> str:
            if callable(self.style):
                return f"{self.style()} {extra}"
            else:
                return f"{self.style} {extra}"

        return _style

    def __pt_container__(self) -> AnyContainer:
        """Return the border widget's container."""
        return self.container


class Shadow:
    """Draw a shadow underneath/behind this container.

    The container must be in a float.
    """

    def __init__(self, body: AnyContainer) -> None:
        """Initialize a new drop-shadow container.

        Args:
            body: Another container object.
        """
        filter_ = get_app().config.filters.show_shadows

        spacer = DummyContainer(width=1, height=1)
        shadow = VSplit(
            [
                HSplit([body, VSplit([spacer, DropShadow()])]),
                HSplit([spacer, DropShadow()]),
            ]
        )

        def get_contents() -> AnyContainer:
            if filter_():
                return shadow
            else:
                return body

        self.container = DynamicContainer(get_contents)

    def __pt_container__(self) -> AnyContainer:
        """Return the container's content."""
        return self.container
