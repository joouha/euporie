"""Define widget for defining layouts."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from functools import lru_cache, partial
from typing import TYPE_CHECKING, ClassVar, NamedTuple, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_width
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    to_container,
)
from prompt_toolkit.layout.controls import (
    FormattedTextControl,
    GetLinePrefixCallable,
    UIContent,
    UIControl,
)
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.dimension import to_dimension
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseButton, MouseEventType
from prompt_toolkit.utils import Event

from euporie.core.border import OutsetGrid
from euporie.core.data_structures import DiBool
from euporie.core.ft.utils import truncate
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.widgets.decor import Border

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer, Container, _Split
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.border import GridStyle

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
                Window(height=self.padding_top, char=char),
                VSplit(
                    [
                        Window(width=self.padding_left, char=char),
                        body,
                        Window(width=self.padding_right, char=char),
                    ]
                ),
                Window(height=self.padding_bottom, char=char),
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


class TabBarTab(NamedTuple):
    """A class representing a tab and its callbacks."""

    title: AnyFormattedText
    on_activate: Callable[[], NotImplementedOrNone]
    on_deactivate: Callable[[], NotImplementedOrNone] | None = None
    on_close: Callable[[], NotImplementedOrNone] | None = None
    closeable: bool = False

    def __hash__(self) -> int:
        """Hash the Tab based on current title value."""
        return hash(tuple(to_formatted_text(self.title))) * hash(
            (self.on_activate, self.on_deactivate, self.on_close, self.closeable)
        )


class TabBarControl(UIControl):
    """A control which shows a tab bar."""

    char_scroll_left = "◀"
    char_scroll_right = "▶"
    char_close: ClassVar[str] = "✖"

    def __init__(
        self,
        tabs: Sequence[TabBarTab] | Callable[[], Sequence[TabBarTab]],
        active: int | Callable[[], int],
        spacing: int = 1,
        max_title_width: int = 30,
        grid: GridStyle = OutsetGrid,
    ) -> None:
        """Create a new tab bar instance.

        Args:
            tabs: A list to tuples describing the tab title and the callback to run
                when the tab is activated.
            active: The index of the currently active tab
            spacing: The number of characters between the tabs
            max_title_width: The maximum width of the title to display
            grid: The grid style to use for drawing borders

        """
        self._tabs = tabs
        self.spacing = spacing
        self.max_title_width = max_title_width
        self._active = active
        self._last_active: int | None = None
        self.scroll = -1
        self.grid = grid

        self.mouse_handlers: dict[int, Callable[[], NotImplementedOrNone] | None] = {}
        self.tab_widths: list[int] = []
        # Caches
        self.render_tab = lru_cache(self._render_tab)
        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    @property
    def tabs(self) -> list[TabBarTab]:
        """Return the tab-bar's tabs."""
        if callable(self._tabs):
            return list(self._tabs())
        else:
            return list(self._tabs)

    @tabs.setter
    def tabs(self, tabs: Sequence[TabBarTab]) -> None:
        """Set the tab bar's current tabs."""
        self._tabs = tabs

    @property
    def active(self) -> int:
        """Return the index of the active tab."""
        current_active = self._active() if callable(self._active) else self._active

        # Check if active tab has changed
        if self._last_active != current_active:
            # Handle tab switching
            if self._last_active is not None and 0 <= self._last_active < len(
                self.tabs
            ):
                old_tab = self.tabs[self._last_active]
                if callable(on_deactivate := old_tab.on_deactivate):
                    on_deactivate()

            # Call on_activate for new tab
            if current_active is not None and 0 <= current_active < len(self.tabs):
                new_tab = self.tabs[current_active]
                if callable(on_activate := new_tab.on_activate):
                    on_activate()

            # Ensure active tab is visible
            self.scroll_to(current_active)

            # Update last known active value
            self._last_active = current_active

        return current_active

    @active.setter
    def active(self, active: int | Callable[[], int]) -> None:
        """Set the currently active tab."""
        # Store new active value
        self._active = active

        # If it's a direct value (not callable), handle tab switching immediately
        if not callable(active):
            # Force property getter to handle the change
            _ = self.active

    def preferred_width(self, max_available_width: int) -> int | None:
        """Return the preferred width of the tab-bar control, the maximum available."""
        return max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Return the preferred height of the tab-bar control (2 rows)."""
        return 2

    def is_focusable(self) -> bool:
        """Tell whether this user control is focusable."""
        return False

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate the formatted text fragments which make the controls output."""
        self.available_width = width

        def get_content() -> tuple[
            UIContent, dict[int, Callable[[], NotImplementedOrNone] | None]
        ]:
            *fragment_lines, mouse_handlers = self.render(width)

            return UIContent(
                get_line=lambda i: fragment_lines[i],
                line_count=len(fragment_lines),
                show_cursor=False,
            ), mouse_handlers

        key = (hash(tuple(self.tabs)), width, self.active, self.scroll)
        ui_content, self.mouse_handlers = self._content_cache.get(key, get_content)
        return ui_content

    def scroll_to(self, active: int) -> None:
        """Adjust scroll position to ensure the active tab is visible."""
        # Calculate position of active tab
        pos = self.spacing  # Initial spacing
        for i in range(len(self.tabs)):
            if i == active:
                # Found active tab - check if it's visible
                tab_width = self.tab_widths[i] if i < len(self.tab_widths) else 0
                # Scroll left if tab start is before visible area
                if pos < self.scroll:
                    self.scroll = pos - self.spacing - 1
                # Scroll right if tab end is after visible area
                elif pos + tab_width > self.scroll + self.available_width:
                    self.scroll = pos + tab_width - self.available_width + 2
                break

            # Add tab width and spacing
            pos += (
                self.tab_widths[i] if i < len(self.tab_widths) else 0
            ) + self.spacing

    def _render_tab(
        self,
        title: tuple[OneStyleAndTextTuple, ...],
        on_activate: Callable[[], NotImplementedOrNone],
        on_deactivate: Callable[[], NotImplementedOrNone] | None,
        on_close: Callable[[], NotImplementedOrNone] | None,
        closeable: bool,
        active: bool,
        max_title_width: int,
        grid: GridStyle,
    ) -> tuple[
        StyleAndTextTuples,
        StyleAndTextTuples,
        list[Callable[[], NotImplementedOrNone] | None],
    ]:
        """Render the tab as formatted text.

        Args:
            title: The formatted text fragments making up the tab's title
            on_activate: Callback function to run when the tab is activated
            on_deactivate: Optional callback function to run when the tab is deactivated
            on_close: Optional callback function to run when the tab is closed
            closeable: Whether the tab can be closed
            active: Whether this tab is currently active
            max_title_width: Maximum width to display the tab title
            grid: The grid style to use for drawing borders

        Returns:
            Tuple containing:
            - Top line formatted text fragments
            - Bottom line formatted text fragments
            - List of mouse handler callbacks for each character position
        """
        title_ft = truncate(list(title), max_title_width)
        title_width = fragment_list_width(title_ft)
        style = "class:active" if active else "class:inactive"

        top_line: StyleAndTextTuples = explode_text_fragments([])
        tab_line: StyleAndTextTuples = explode_text_fragments([])
        mouse_handlers: list[Callable[[], NotImplementedOrNone] | None] = []

        # Add top edge over title
        top_line.append(
            (f"{style} class:tab,border,top", grid.TOP_MID * (title_width + 2))
        )

        # Left edge
        tab_line.append((f"{style} class:tab,border,left", grid.MID_LEFT))
        mouse_handlers.append(on_activate)

        # Title
        tab_line.extend(
            [
                (f"{style} class:tab,title {frag_style}", text)
                for frag_style, text, *_ in title_ft
            ]
        )
        for _ in range(title_width):
            mouse_handlers.append(on_activate)

        # Close button
        if closeable:
            top_line.append((f"{style} class:tab,border,top", grid.TOP_MID * 2))
            mouse_handlers.append(on_activate)
            tab_line.extend(
                [
                    (f"{style} class:tab", " "),
                    (f"{style} class:tab,close", self.char_close),
                ]
            )
            mouse_handlers.append(on_close)

        # Right edge
        tab_line.append((f"{style} class:tab,border,right", grid.MID_RIGHT))
        mouse_handlers.append(on_activate)

        return (top_line, tab_line, mouse_handlers)

    def render(
        self, width: int
    ) -> tuple[
        StyleAndTextTuples,
        StyleAndTextTuples,
        dict[int, Callable[[], NotImplementedOrNone] | None],
    ]:
        """Render the tab-bar as lines of formatted text."""
        top_line: StyleAndTextTuples = []
        tab_line: StyleAndTextTuples = []
        mouse_handlers: dict[int, Callable[[], NotImplementedOrNone] | None] = {}
        pos = 0
        full = 0

        renderings = [
            self.render_tab(
                title=tuple(to_formatted_text(tab.title)),
                max_title_width=self.max_title_width,
                on_activate=tab.on_activate,
                on_deactivate=tab.on_deactivate,
                on_close=tab.on_close,
                closeable=tab.closeable,
                active=(self.active == j),
                grid=self.grid,
            )
            for j, tab in enumerate(self.tabs)
        ]
        self.tab_widths = [len(x[0]) for x in renderings]

        # Do initial scroll if first render
        if self.scroll == -1:
            self.scroll_to(self._active() if callable(self._active) else self._active)

        # Apply scroll limits
        self.scroll = max(
            0,
            min(
                self.scroll,
                self.spacing * (len(self.tabs) + 1)
                + sum(len(x[1]) for x in renderings)
                - width,
            ),
        )
        scroll = self.scroll

        # Initial spacing
        for _ in range(self.spacing):
            if full >= scroll:
                top_line += [("", " ")]
                tab_line += [("class:border,bottom", self.grid.TOP_MID)]
                pos += 1
            full += 1

        for rendering in renderings:
            # Add the rendered tab content
            for tab_top, tab_bottom, handler in zip(*rendering):
                if full >= scroll:
                    top_line.append(tab_top)
                    tab_line.append(tab_bottom)
                    mouse_handlers[pos] = handler
                    pos += 1
                full += 1
                if pos == width:
                    break

            if pos == width:
                break

            # Inter-tab spacing
            if rendering is not renderings[-1]:
                if full >= scroll:
                    for _ in range(self.spacing):
                        top_line += [("", " ")]
                        tab_line += [("class:border,bottom", self.grid.TOP_MID)]
                        if pos == width:
                            break
                        pos += 1
                full += 1

            if pos == width:
                break

        # Add scroll indicators
        if scroll > 0:
            top_line[0] = ("", " ")
            tab_line[0] = ("class:overflow", self.char_scroll_left)
        if pos >= width:
            top_line[-1] = ("", " ")
            tab_line[-1] = ("class:overflow", self.char_scroll_right)
        else:
            # Otherwise add border to fill width
            tab_line += [
                (
                    "class:border,bottom",
                    self.grid.TOP_MID * (width - pos + 1),
                )
            ]

        return top_line, tab_line, mouse_handlers

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events."""
        row = mouse_event.position.y
        col = mouse_event.position.x

        if row == 1 and mouse_event.event_type == MouseEventType.MOUSE_UP:
            if mouse_event.button == MouseButton.LEFT and callable(
                handler := self.mouse_handlers.get(col)
            ):
                # Activate the tab
                handler()
                return None
            elif mouse_event.button == MouseButton.MIDDLE:
                if callable(handler := self.mouse_handlers.get(col)):
                    # Activate tab
                    handler()
                    # Close the now active tab
                    tabs = self.tabs
                    tab = tabs[self.active]
                    if tab.closeable and callable(tab.on_close):
                        tab.on_close()
                return None

        tabs = self.tabs
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            index = max(self.active - 1, 0)
            if index != self.active:
                if callable(activate := tabs[index].on_activate):
                    activate()
                return None
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            index = min(self.active + 1, len(tabs) - 1)
            if index != self.active:
                if callable(activate := tabs[index].on_activate):
                    activate()
                return None
        return NotImplemented


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
                Border(
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

    def load_tabs(self) -> list[TabBarTab]:
        """Return a list of tabs for the current children."""
        return [
            TabBarTab(
                title=title,
                on_activate=partial(setattr, self, "active", i),
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
                Border(
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
