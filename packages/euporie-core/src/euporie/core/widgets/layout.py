"""Define widget for defining layouts."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, cast

from apptk.application.current import get_app
from apptk.border import OutsetGrid
from apptk.cache import SimpleCache
from apptk.data_structures import DiBool
from apptk.filters import Condition, to_filter
from apptk.formatted_text.base import to_formatted_text
from apptk.key_binding.key_bindings import KeyBindings
from apptk.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
    to_container,
)
from apptk.layout.controls import (
    FormattedTextControl,
)
from apptk.layout.decor import Fill
from apptk.layout.dimension import Dimension as D
from apptk.layout.dimension import to_dimension
from apptk.mouse_events import MouseEventType
from apptk.utils import Event
from apptk.widgets.base import Frame
from apptk.widgets.panel import Panel
from apptk.widgets.tab_bar import TabBarControl

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

    from apptk.border import GridStyle
    from apptk.filters import FilterOrBool
    from apptk.formatted_text.base import (
        AnyFormattedText,
        StyleAndTextTuples,
    )
    from apptk.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from apptk.key_binding.key_processor import KeyPressEvent
    from apptk.layout.containers import AnyContainer, Container, _Split
    from apptk.layout.dimension import AnyDimension
    from apptk.mouse_events import MouseEvent

log = logging.getLogger(__name__)


class Box:
    """Add padding around a container.

    This also makes sure that the parent can provide more space than required by
    the child. This is very useful when wrapping a small element with a fixed
    size into a ``VSplit`` or ``HSplit`` object. The ``HSplit`` and ``VSplit``
    try to make sure to adapt respectively the width and height, possibly
    shrinking other elements. Wrapping something in a ``Box`` makes it flexible.

    Args:
        body: Another container object.
        padding: The margin to be used around the body. This can be
        overridden by `padding_left`, padding_right`, `padding_top` and
            `padding_bottom`.
        style: A style string.
        char: Character to be used for filling the space around the body.
            (This is supposed to be a character with a terminal width of 1.)
    """

    def __init__(
        self,
        body: AnyContainer,
        padding: AnyDimension = None,
        padding_left: AnyDimension = None,
        padding_right: AnyDimension = None,
        padding_top: AnyDimension = None,
        padding_bottom: AnyDimension = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        style: str | Callable[[], str] = "",
        char: None | str | Callable[[], str] = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None:
        """Initialize this widget."""
        if padding is None:
            padding = D(preferred=0)

        def get(value: AnyDimension) -> D:
            if value is None:
                value = padding
            return to_dimension(value)

        self.padding_left = get(padding_left)
        self.padding_right = get(padding_right)
        self.padding_top = get(padding_top)
        self.padding_bottom = get(padding_bottom)
        self.body = body

        self.container = HSplit(
            [
                Fill(height=self.padding_top, char=char),
                VSplit(
                    [
                        Fill(width=self.padding_left, char=char),
                        body,
                        Fill(width=self.padding_right, char=char),
                    ]
                ),
                Fill(height=self.padding_bottom, char=char),
            ],
            width=width,
            height=height,
            style=style,
            modal=modal,
            key_bindings=key_bindings,
        )

    def __pt_container__(self) -> Container:
        """Return the main container for this widget."""
        return self.container


class ConditionalSplit:
    """A split container where the orientation depends on a filter."""

    def __init__(self, vertical: FilterOrBool, *args: Any, **kwargs: Any) -> None:
        """Create a new conditional split container.

        Args:
            vertical: A filter which determines if the container should be displayed vertically
            args: Positional arguments to pass to the split container
            kwargs: Key-word arguments to pass to the split container

        """
        self.vertical = to_filter(vertical)
        self.args = args
        self.kwargs = kwargs
        self._cache: SimpleCache = SimpleCache(maxsize=2)

    def load_container(self, vertical: bool) -> _Split:
        """Load the container."""
        if vertical:
            return HSplit(*self.args, **self.kwargs)
        else:
            return VSplit(*self.args, **self.kwargs)

    def container(self) -> _Split:
        """Return the container for the current orientation."""
        vertical = self.vertical()
        return self._cache.get(vertical, partial(self.load_container, vertical))

    def __pt_container__(self) -> AnyContainer:
        """Return a dynamic container."""
        return DynamicContainer(self.container)


class ReferencedSplit:
    """A split container which maintains a reference to it's children."""

    def __init__(
        self,
        split: type[_Split],
        children: Sequence[AnyContainer],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Create a new instance of the split container.

        Args:
            split: The split container class (:class:`HSplit` or :class:`VSplit`)
            children: A list of child containers
            args: Positional arguments to pass to the split container
            kwargs: Key-word arguments to pass to the split container

        """
        self.container = split([], *args, **kwargs)
        self.children = list(children)

    @property
    def children(self) -> list[AnyContainer]:
        """Convert the referenced children to containers."""
        return self._children

    @children.setter
    def children(self, children: list[AnyContainer]) -> None:
        """Set the containers children."""
        self._children = children
        self.container.children = [to_container(x) for x in self._children]

    def __pt_container__(self) -> Container:
        """Return the child container."""
        return self.container


class StackedSplit(metaclass=ABCMeta):
    """Base class for containers with selectable children."""

    def __init__(
        self,
        children: Sequence[AnyContainer],
        titles: Sequence[AnyFormattedText],
        active: int = 0,
        style: str | Callable[[], str] = "class:tab-split",
        on_change: Callable[[StackedSplit], None] | None = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
    ) -> None:
        """Create a new tabbed container instance.

        Args:
            children: A list of child container or a callable which returns such
            titles: A list of tab titles or a callable which returns such
            active: The index of the active tab
            style: A style to apply to the tabbed container
            on_change: Callback to run when the selected tab changes
            width: The width of the split container
            height: The height of the split container
        """
        self._children = list(children)
        self._titles = list(titles)
        self._active: int | None = active
        self.style = style
        self.on_change = Event(self, on_change)
        self.width = width
        self.height = height

        self.container = self.load_container()

    @abstractmethod
    def load_container(self) -> AnyContainer:
        """Abstract method for loading the widget's container."""
        ...

    def add_style(self, style: str) -> str:
        """Add a style to the widget's base style."""
        base_style = self.style() if callable(self.style) else self.style
        return f"{base_style} {style}"

    @property
    def active(self) -> int | None:
        """Return the index of the active child container."""
        return self._active

    @active.setter
    def active(self, value: int | None) -> None:
        """Set the active child container.

        Args:
            value: The index of the tab to make active
        """
        if value is not None:
            value = max(0, min(value, len(self.children) - 1))
        if value != self._active:
            self._active = value
            self.refresh()
            self.on_change.fire()
            if value is not None:
                try:
                    get_app().layout.focus(self.children[value])
                except ValueError:
                    pass

    @property
    def children(self) -> list[AnyContainer]:
        """Return a list of the widget's child containers."""
        return self._children

    @children.setter
    def children(self, value: Sequence[AnyContainer]) -> None:
        """Set the widget's child containers."""
        self._children = list(value)
        self.refresh()

    def active_child(self) -> AnyContainer:
        """Return the currently active child container."""
        return self.children[self.active or 0]

    @property
    def titles(self) -> list[AnyFormattedText]:
        """Return the titles of the child containers."""
        return self._titles

    @titles.setter
    def titles(self, value: Sequence[AnyFormattedText]) -> None:
        """Set the titles of the child containers."""
        self._titles = list(value)
        self.refresh()

    def refresh(self) -> None:
        """Reload the widget's container when its children or their titles change."""

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container


class TabbedSplit(StackedSplit):
    """A container which switches between children using tabs."""

    def __init__(
        self,
        children: Sequence[AnyContainer],
        titles: Sequence[AnyFormattedText],
        active: int = 0,
        style: str | Callable[[], str] = "class:tab-split",
        on_change: Callable[[StackedSplit], None] | None = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        border: GridStyle = OutsetGrid,
        show_borders: DiBool | None = None,
    ) -> None:
        """Initialize a new tabbed container."""
        self.border = border
        self.show_borders = show_borders or DiBool(False, True, True, True)

        kb = KeyBindings()

        @kb.add("left")
        def _prev(event: KeyPressEvent) -> None:
            """Previous tab."""
            self.active = (self.active or 0) - 1

        @kb.add("right")
        def _next(event: KeyPressEvent) -> None:
            """Next tab."""
            self.active = (self.active or 0) + 1

        self.key_bindings = kb

        super().__init__(
            children=children,
            titles=titles,
            active=active,
            style=style,
            on_change=on_change,
            width=width,
            height=height,
        )

    def load_container(self) -> AnyContainer:
        """Create the tabbed widget's container.

        Consists of a tab-bar control above a dynamic container which shows the active
        child container.

        Returns:
            The widget's container
        """
        self.control = TabBarControl(self.load_tabs(), active=self.active or 0)
        return HSplit(
            [
                Window(
                    self.control,
                    style=partial(self.add_style, "class:tab-bar"),
                    height=2,
                ),
                Frame(
                    Box(
                        DynamicContainer(self.active_child),
                        padding=0,
                        padding_top=1,
                        padding_bottom=1,
                        style="class:tabbed-split,page",
                    ),
                    border=self.border,
                    show_borders=self.show_borders,
                ),
            ],
            style="class:tabbed-split",
            width=self.width,
            height=self.height,
            key_bindings=self.key_bindings,
        )

    def refresh(self) -> None:
        """Refresh the widget - set the tab-bar's tabs and active tab index."""
        self.control.tabs = self.load_tabs()
        if self.active is not None:
            self.control.active = self.active

    def load_tabs(self) -> list[Panel]:
        """Return a list of tabs for the current children."""
        return [
            Panel(
                title=title,
                on_activate=lambda sender, i=i: setattr(self, "active", i),
            )
            for i, title in enumerate(self.titles)
        ]


class AccordionSplit(StackedSplit):
    """A container which switches between children using expandable sections."""

    def load_container(self) -> AnyContainer:
        """Create the accordiion widget's container."""
        self.draw_container()
        return DynamicContainer(lambda: self._container)

    def draw_container(self) -> None:
        """Render the accordion in it's current state."""
        self._container = HSplit(
            [
                Frame(
                    HSplit(
                        [
                            Window(
                                FormattedTextControl(
                                    partial(self.title_text, index, title),
                                    focusable=True,
                                    show_cursor=False,
                                )
                            ),
                            ConditionalContainer(
                                Box(child, padding_left=0),
                                filter=Condition(
                                    partial(lambda i: self.active == i, index)
                                ),
                            ),
                        ]
                    ),
                    style=partial(self.add_style, "class:border"),
                )
                for index, (title, child) in enumerate(zip(self.titles, self.children))
            ],
            style="class:accordion",
        )

    def title_text(self, index: int, title: AnyFormattedText) -> StyleAndTextTuples:
        """Generate the title for each child container."""
        return [
            ("", " "),
            (
                "bold" + (" class:selection" if self.active == index else ""),
                "▶" if self.active == index else "▼",
                cast(
                    "Callable[[MouseEvent], None]", partial(self.mouse_handler, index)
                ),
            ),
            ("", " "),
            *[
                (
                    f"bold {style}",
                    text,
                    cast(
                        "Callable[[MouseEvent], None]",
                        partial(self.mouse_handler, index),
                    ),
                )
                for style, text, *_ in to_formatted_text(title)
            ],
        ]

    def mouse_handler(
        self, index: int, mouse_event: MouseEvent
    ) -> NotImplementedOrNone:
        """Handle mouse events."""
        # if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
        #    get_app().layout.focus()
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.toggle(index)
        else:
            return NotImplemented
        return None

    def toggle(
        self,
        index: int,
    ) -> None:
        """Toggle the visibility of a child container."""
        self.active = index if self.active != index else None

    def refresh(self) -> None:
        """Re-draw the container when the list of child containers changes."""
        self.draw_container()
