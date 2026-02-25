"""Extended widget components for building full screen applications.

This module provides enhanced versions of prompt_toolkit widgets with additional
functionality such as custom border styles and selective border visibility.

All of these widgets implement the ``__pt_container__`` method, which makes
them usable in any situation where we are expecting a `prompt_toolkit`
container object.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.layout.dimension import Dimension
from prompt_toolkit.widgets.base import Frame as PtkFrame
from prompt_toolkit.widgets.base import Shadow as PtkShadow

from euporie.apptk.border import ThinGrid, ThinLine
from euporie.apptk.data_structures import DiStr
from euporie.apptk.filters import to_filter
from euporie.apptk.layout.containers import (
    ConditionalContainer,
    DummyContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
)
from euporie.apptk.layout.decor import DropShadow
from euporie.apptk.widgets.base import Label

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.filters.core import FilterOrBool
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.key_binding.key_bindings import KeyBindings
    from prompt_toolkit.layout.dimension import AnyDimension

    from euporie.apptk.border import GridStyle
    from euporie.apptk.layout.containers import AnyContainer
    from euporie.apptk.mouse_events import MouseEvent

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)

# Override prompt_toolkit's `Border` class with a backwards compatible grid instance
# from the new :py:mod:`apptk.border` system
Border = ThinGrid


class Frame(PtkFrame):
    """Draw a border around any container, optionally with a title text.

    Extends the prompt_toolkit Frame with support for custom border styles
    and selective border visibility.

    Args:
        body: Another container object.
        title: Text to be displayed in the top of the frame (can be formatted text).
        style: Style string to be applied to this widget.
        border_style: Style string to be applied to the border elements.
        width: Width of the frame.
        height: Height of the frame.
        key_bindings: Optional key bindings.
        modal: Whether the frame is modal.
        border: The grid style to use for the border.
        show_borders: Which of the four borders should be displayed (top, right, bottom, left).
    """

    def __init__(
        self,
        body: AnyContainer,
        title: AnyFormattedText = "",
        style: str | Callable[[], str] = "class:frame",
        width: AnyDimension = None,
        height: AnyDimension = None,
        key_bindings: KeyBindings | None = None,
        modal: bool = False,
        border: GridStyle | None = ThinLine.grid,
        border_style: str
        | Callable[[], str]
        | tuple[
            str | Callable[[], str],
            str | Callable[[], str],
            str | Callable[[], str],
            str | Callable[[], str],
        ]
        | None = None,
        show_borders: FilterOrBool
        | tuple[FilterOrBool, FilterOrBool, FilterOrBool, FilterOrBool]
        | None = None,
    ) -> None:
        """Initialize the Frame widget."""
        self.body = body
        self.title = title
        self.style = style

        # Handle show_borders parameter
        if show_borders is None:
            show_borders = True
        if not isinstance(show_borders, tuple):
            show_borders = (show_borders, show_borders, show_borders, show_borders)
        sb_top = to_filter(show_borders[0])
        sb_right = to_filter(show_borders[1])
        sb_bottom = to_filter(show_borders[2])
        sb_left = to_filter(show_borders[3])

        # Handle border style parameter
        if border_style is None:
            border_style = DiStr(
                "class:border,top",
                "class:border,right",
                "class:border,bottom",
                "class:border,left",
            )
        if not isinstance(border_style, tuple):
            border_style = (border_style, border_style, border_style, border_style)
        bs_top = border_style[0]
        bs_right = border_style[1]
        bs_bottom = border_style[2]
        bs_left = border_style[3]

        self.container: AnyContainer
        if border is not None and any(show_borders):
            top_edge: AnyContainer = Window(
                char=border.TOP_MID, style=self.add_styles(bs_top)
            )
            if title:
                top_edge = VSplit(
                    [
                        top_edge,
                        # Make title padding collapsible
                        Window(width=Dimension(max=1), height=1),
                        Label(lambda: title, dont_extend_width=True),
                        Window(width=Dimension(max=1), height=1),
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
                                        style=self.add_styles(bs_top, bs_left),
                                    ),
                                    filter=sb_top & sb_left,
                                ),
                                ConditionalContainer(top_edge, filter=sb_top),
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.TOP_RIGHT,
                                        style=self.add_styles(bs_top, bs_right),
                                    ),
                                    filter=sb_top & sb_right,
                                ),
                            ],
                            height=1,
                        ),
                        filter=sb_top,
                    ),
                    VSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_LEFT,
                                    style=self.add_styles(bs_left),
                                ),
                                filter=sb_left,
                            ),
                            DynamicContainer(lambda: self.body),
                            ConditionalContainer(
                                Window(
                                    width=1,
                                    char=border.MID_RIGHT,
                                    style=self.add_styles(bs_right),
                                ),
                                filter=sb_right,
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
                                        style=self.add_styles(bs_left, bs_bottom),
                                    ),
                                    filter=sb_bottom & sb_left,
                                ),
                                ConditionalContainer(
                                    Window(
                                        char=border.BOTTOM_MID,
                                        style=self.add_styles(bs_bottom),
                                    ),
                                    filter=sb_bottom,
                                ),
                                ConditionalContainer(
                                    Window(
                                        width=1,
                                        height=1,
                                        char=border.BOTTOM_RIGHT,
                                        style=self.add_styles(bs_right, bs_bottom),
                                    ),
                                    filter=sb_bottom & sb_right,
                                ),
                            ],
                            # specifying height here will increase the rendering speed.
                            height=1,
                        ),
                        filter=sb_bottom,
                    ),
                ],
                width=width,
                height=height,
                # style=style,
                key_bindings=key_bindings,
                modal=modal,
            )
        else:
            self.container = body

    def add_styles(self, *styles: str | Callable[[], str]) -> Callable[[], str]:
        """Return a function which adds a style string to the border style."""
        return lambda: " ".join(
            style() if callable(style) else style for style in [self.style, *styles]
        )


class Shadow(PtkShadow):
    """Draw a shadow underneath/behind this container.

    The container must be in a float.
    """

    def __init__(self, body: AnyContainer, filter: FilterOrBool = True) -> None:
        """Initialize a new drop-shadow container.

        Args:
            body: Another container object.
            filter: Determines if the shadow should be applied
        """
        filter = to_filter(filter)

        spacer = DummyContainer(width=1, height=1)
        shadow = VSplit(
            [
                HSplit([body, VSplit([spacer, DropShadow()])]),
                HSplit([spacer, DropShadow()]),
            ]
        )

        def get_contents() -> AnyContainer:
            if filter():
                return shadow
            else:
                return body

        self.container = DynamicContainer(get_contents)
