"""Contains containers which display children at full height vertically stacked."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.filters import is_searching
from prompt_toolkit.layout.containers import (
    Container,
    ScrollOffsets,
    Window,
    WindowRenderInfo,
)
from prompt_toolkit.layout.controls import UIContent
from prompt_toolkit.layout.dimension import Dimension, to_dimension
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType, MouseModifier

from euporie.core.layout.cache import CachedContainer
from euporie.core.layout.screen import BoundedWritePosition

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Callable, Literal

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen as PtkScreen
    from prompt_toolkit.layout.screen import WritePosition

    MouseHandler = Callable[[MouseEvent], object]

log = logging.getLogger(__name__)


class ScrollingContainer(Container):
    """A scrollable container which renders only the currently visible children."""

    render_info: WindowRenderInfo | None

    def __init__(
        self,
        children: Callable[[], Sequence[AnyContainer]] | Sequence[AnyContainer],
        height: AnyDimension = None,
        width: AnyDimension = None,
        style: str | Callable[[], str] = "",
        scroll_offsets: ScrollOffsets | None = None,
    ) -> None:
        """Initiate the `ScrollingContainer`."""
        if callable(children):
            _children_func = children
        else:

            def _children_func() -> Sequence[AnyContainer]:
                """Return the pass sequence of children."""
                assert not callable(children)
                return children

        self.children_func = _children_func
        self._child_cache: dict[int, CachedContainer] = {}
        self._children: list[CachedContainer] = []
        self._known_sizes_cache: FastDictCache[tuple[int], list[int]] = FastDictCache(
            self._known_sizes
        )
        self.refresh_children = True
        self.pre_rendered: float | None = None

        self._selected_slice = slice(
            0, 1
        )  # The index of the currently selected children
        self.selected_child_position: int = 0

        self.visible_indices: set[int] = {0}
        self.index_positions: dict[int, int | None] = {}

        self.last_write_position: WritePosition = BoundedWritePosition(0, 0, 0, 0)
        self.last_total_height = 0

        self.width = to_dimension(width).preferred
        self.height = to_dimension(height).preferred
        self.style = style
        self.scroll_offsets = scroll_offsets or ScrollOffsets(
            top=1, bottom=1, left=1, right=1
        )

        self.scroll_to_cursor = False
        self.scrolling = 0

    def pre_render_children(self, width: int, height: int) -> None:
        """Render all unrendered children in a background thread."""
        children = self.all_children()
        if not children:
            return
        self.pre_rendered = 0.0
        incr = 1 / len(children)
        app = get_app()

        def _cb(task: asyncio.Task) -> None:
            """Task callback to update pre-rendering percentage."""
            assert isinstance(self.pre_rendered, float)
            self.pre_rendered += incr
            app.invalidate()

        tasks = set()
        for child in children:
            if isinstance(child, CachedContainer):
                task = app.create_background_task(
                    asyncio.to_thread(child.render, width, height)
                )
                task.add_done_callback(_cb)
                tasks.add(task)

        async def _finish() -> None:
            await asyncio.gather(*tasks)
            self.pre_rendered = 1.0
            app.invalidate()
            # app.exit()

        app.create_background_task(_finish())

    def reset(self) -> None:
        """Reset the state of this container and all the children."""
        for child in self.all_children():
            child.reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Do not provide a preferred width - grow to fill the available space."""
        if self.width is not None:
            return Dimension(min=1, preferred=self.width, weight=1)
        return Dimension(weight=1)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return the preferred height only if one is provided."""
        if self.height is not None:
            return Dimension(min=1, preferred=self.height, weight=1)
        return Dimension(weight=1)

    def _set_selected_slice(
        self, req_slice: slice, force: bool = False, scroll: bool = True
    ) -> None:
        # Only update the selected child if it was not selected before
        if force or req_slice != self._selected_slice:
            app = get_app()
            self.refresh_children = True
            children = self.all_children()
            # Ensure new selected slice is valid
            new_slice = self.validate_slice(req_slice)
            # Scroll into view
            if scroll:
                anchor: Literal["top", "bottom"] | None = None
                if (
                    new_slice.start == len(children) - 1
                    and new_slice.stop
                    and req_slice.stop > new_slice.stop
                ):
                    anchor = "bottom"
                elif req_slice.start == -1:
                    anchor = "top"
                self.scroll_to(new_slice.start, anchor)
            # Request a refresh of the previously selected children
            for child in self._selected_children:
                child.invalidate()
            # Get the first selected child and focus it
            child = children[new_slice.start]
            if not app.layout.has_focus(child):
                try:
                    app.layout.focus(child)
                except ValueError:
                    pass
            # Track which child was selected
            self._selected_slice = new_slice

    @property
    def selected_slice(self) -> slice:
        """Return the currently selected slice."""
        return self._selected_slice

    @selected_slice.setter
    def selected_slice(self, new_slice: slice) -> None:
        """Set the currently selected child index.

        Args:
            new_slice: The slice of the children to select.
        """
        self._set_selected_slice(new_slice)

    def validate_slice(self, slice_: slice) -> slice:
        """Ensure a slice describes a valid range of children."""
        start = min(max(slice_.start, 0), len(self._children) - 1)
        stop = slice_.stop
        if stop == -1:
            stop = None
        if stop is not None:
            stop = min(max(slice_.stop, int(start == 0)), len(self._children))
        return slice(start, stop, slice_.step)

    @property
    def selected_indices(self) -> list[int]:
        """Return in indices of the currently selected children."""
        return list(range(*self.selected_slice.indices(len(self._children))))

    def select(
        self,
        index: int,
        extend: bool = False,
        position: int | None = None,
        scroll: bool = True,
    ) -> None:
        """Select a child or adds it to the selection.

        Args:
            index: The index of the cell to select
            extend: If true, the selection will be extended to include the cell
            position: An optional cursor position index to apply to the cell input
            scroll: Whether to scroll the page
        """
        # Update the selected slice if we are extending the child selection
        if extend:
            slice_ = self._selected_slice
            stop = -1 if slice_.stop is None else slice_.stop
            step = slice_.step
            if step == -1 and index <= stop:
                stop += 2
                step = 1
            elif step == -1 and index >= stop:
                pass
            elif step in (1, None) and index < stop:
                step = 1
            elif step in (1, None) and index >= stop:
                step = -1
                stop -= 2
            self._set_selected_slice(slice(index, stop, step), scroll=scroll)
        # Otherwise set the cell selection to the given cell index
        else:
            self._set_selected_slice(slice(index, index + 1), scroll=scroll)

    def scroll(self, n: int) -> NotImplementedOrNone:
        """Scroll up or down a number of rows.

        Args:
            n: The number of rows to scroll, negative for up, positive for down

        Returns:
            :py:const:`NotImplemented` is scrolling is not allowed, otherwise
                :py:const:`None`

        """
        if n > 0:
            if (
                min(self.visible_indices) == 0
                and self.index_positions
                and self.index_positions[0] is not None
            ):
                n = min(n, 0 - self.index_positions[0] - self.scrolling)
                if self.index_positions[0] + self.scrolling + n > 0:
                    return NotImplemented
        elif n < 0:
            bottom_index = len(self._children) - 1
            if bottom_index in self.visible_indices:
                bottom_child = self.get_child(bottom_index)
                bottom_pos = self.index_positions[bottom_index]
                if bottom_pos is not None:
                    n = max(
                        n,
                        self.last_write_position.height
                        - (bottom_pos + bottom_child.height + self.scrolling),
                    )
                    if (
                        bottom_pos + bottom_child.height + self.scrolling + n
                        < self.last_write_position.height
                    ):
                        return NotImplemented

        # Very basic scrolling acceleration
        if n:
            self.scrolling += n
            return None
        else:
            return NotImplemented

    def mouse_scroll_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Mouse handler to scroll the pane."""
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            return self.scroll(-1)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            return self.scroll(1)
        else:
            return NotImplemented
        return None

    def _mouse_handler_wrapper(
        self, handler: MouseHandler | None = None, child: CachedContainer | None = None
    ) -> MouseHandler:
        def wrapped(mouse_event: MouseEvent) -> NotImplementedOrNone:
            response: NotImplementedOrNone = NotImplemented

            if callable(handler):
                response = handler(mouse_event)

            if response is NotImplemented:
                if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                    response = self.scroll(-1)
                elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                    response = self.scroll(1)

            # Refresh the child if there was a response
            if response is None:
                return response

            # Select the clicked child if clicked
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                if child:
                    index = self._children.index(child)
                    if mouse_event.modifiers & {
                        MouseModifier.SHIFT,
                        MouseModifier.CONTROL,
                    }:
                        self.select(index, extend=True)
                    else:
                        self.select(index, extend=False)
                    get_app().layout.focus(child)
                else:
                    try:
                        get_app().layout.focus(self)
                    except Exception:
                        ...
                response = None

            return response

        return wrapped

    def write_to_screen(
        self,
        screen: PtkScreen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Write the actual content to the screen.

        Children are rendered only if they are visible and have changed, and the output
        is cached to a separate screen object stored in a :py::class:`ChildRenderInfo`. The
        cached rendering of the children which are actually visible are then copied to
        the screen. This results in faster rendering of the scrolling container, and
        makes scrolling more performant.

        Args:
            screen: The :class:`~prompt_toolkit.layout.screen.Screen` class to which
                the output has to be written.
            mouse_handlers: :class:`prompt_toolkit.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`prompt_toolkit.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`prompt_toolkit.layout.containers.HSplit` can use it to pass
                their style down to the windows that they contain.
            z_index: Used for propagating z_index from parent to child.
        """
        # Record where the container was last drawn so we can determine if cell outputs
        # are partially obscured
        self.last_write_position = write_position

        ypos = write_position.ypos
        xpos = write_position.xpos

        available_width = write_position.width
        available_height = write_position.height

        # Update screen height
        screen.height = max(screen.height, ypos + write_position.height)

        # Record children which are currently visible
        visible_indices = set()

        # Force the selected children to refresh
        selected_indices = self.selected_indices
        self._selected_children: list[CachedContainer] = []
        for index in selected_indices:
            child = self.get_child(index)
            # Do not bother to re-render selected children if we are scrolling
            if not self.scrolling:
                child.invalidate()
            self._selected_children.append(child)
            self.index_positions[index] = None

        # Refresh **visible** children if searching
        if is_searching():
            for index in self.visible_indices:
                self.get_child(index).invalidate()

        # Scroll to make the cursor visible
        layout = get_app().layout
        if self.scroll_to_cursor:
            selected_child = self._selected_children[0]
            selected_child.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
                start=self.selected_child_position,
            )
            if cursor_position := selected_child.screen.cursor_positions.get(
                layout.current_window
            ):
                cursor_row = self.selected_child_position + cursor_position.y
                scroll_offsets = self.scroll_offsets
                if cursor_row < scroll_offsets.top + scroll_offsets.top:
                    self.selected_child_position -= cursor_row - scroll_offsets.top
                elif cursor_row >= available_height - (scroll_offsets.bottom + 1):
                    self.selected_child_position -= (
                        cursor_row - available_height + (scroll_offsets.bottom + 1)
                    )
            # Set this to false again, allowing us to scroll the cursor out of view
            self.scroll_to_cursor = False

        # Adjust scrolling offset
        heights = self.known_sizes
        total_height = sum(heights)
        if self.scrolling or total_height != self.last_total_height:
            heights_above = sum(heights[: self._selected_slice.start])
            new_child_position = self.selected_child_position + self.scrolling
            # Do not allow scrolling if there is no overflow
            if sum(heights) < available_height:
                self.selected_child_position = heights_above
                self.scrolling = 0
            else:
                # Prevent overscrolling at the top of the document
                overscroll = heights_above - new_child_position
                if overscroll < 0:
                    # Scroll as far as we are able without overscrolling
                    self.scrolling = max(0, self.scrolling + overscroll)
                # Prevent underscrolling at the bottom
                elif overscroll > 0:
                    heights_below = sum(heights[self._selected_slice.start :])
                    underscroll = new_child_position + heights_below - available_height
                    if underscroll < 0:
                        # Scroll as far as we are able without underscrolling
                        self.scrolling = min(0, self.scrolling - underscroll)
            self.selected_child_position += self.scrolling

        self.last_total_height = total_height

        # Blit first selected child and those below it that are on screen
        line = self.selected_child_position
        for i in range(self._selected_slice.start, len(self._children)):
            child = self.get_child(i)
            child.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
                start=line,
            )
            if line + child.height > 0 and line < available_height:
                self.index_positions[i] = line
                child.blit(
                    screen=screen,
                    mouse_handlers=mouse_handlers,
                    left=xpos,
                    top=ypos + line,
                    cols=slice(0, available_width),
                    rows=slice(
                        max(0, 0 - line),
                        min(child.height, available_height - line),
                    ),
                )
                visible_indices.add(i)
            line += child.height
            if line >= available_height:
                break
        else:
            if line < available_height:
                Window(char=" ").write_to_screen(
                    screen,
                    mouse_handlers,
                    BoundedWritePosition(
                        xpos, ypos + line, available_width, available_height - line
                    ),
                    parent_style,
                    erase_bg,
                    z_index,
                )
                for y in range(ypos + line, ypos + available_height):
                    for x in range(xpos, xpos + available_width):
                        mouse_handlers.mouse_handlers[y][x] = (
                            self._mouse_handler_wrapper(
                                mouse_handlers.mouse_handlers[y][x]
                            )
                        )
        # Blit children above the selected that are on screen
        line = self.selected_child_position
        for i in range(self._selected_slice.start - 1, -1, -1):
            child = self.get_child(i)
            child.render(
                available_width=available_width,
                available_height=available_height,
                style=f"{parent_style} {self.style}",
                end=line,
            )
            # TODOD - prevent lagged child height
            line -= child.height
            if line + child.height > 0 and line < available_height:
                self.index_positions[i] = line
                child.blit(
                    screen=screen,
                    mouse_handlers=mouse_handlers,
                    left=xpos,
                    top=ypos + line,
                    cols=slice(0, available_width),
                    rows=slice(
                        max(0, 0 - line),
                        min(child.height, available_height - line),
                    ),
                )
                visible_indices.add(i)
            if line <= 0:
                break
        else:
            if line > 0:
                Window(char=" ").write_to_screen(
                    screen,
                    mouse_handlers,
                    BoundedWritePosition(xpos, ypos, available_width, line),
                    parent_style,
                    erase_bg,
                    z_index,
                )
                for y in range(ypos, ypos + line):
                    for x in range(xpos, xpos + available_width):
                        mouse_handlers.mouse_handlers[y][x] = (
                            self._mouse_handler_wrapper(
                                mouse_handlers.mouse_handlers[y][x]
                            )
                        )

        # Dont bother drawing floats
        # screen.draw_all_floats()

        # Ensure the focused child is always in the layout
        visible_indices.add(self._selected_slice.start)

        # Update which children will appear in the layout
        self.visible_indices = visible_indices

        # Update parent relations in layout
        def _walk(e: Container) -> None:
            for c in e.get_children():
                layout._child_to_parent[c] = e
                _walk(c)

        _walk(self)

        # Mock up a WindowRenderInfo so we can draw a scrollbar margin
        self.render_info = WindowRenderInfo(
            window=cast("Window", self),
            ui_content=UIContent(line_count=max(sum(heights), 1)),
            horizontal_scroll=0,
            vertical_scroll=self.vertical_scroll,
            window_width=available_width,
            window_height=available_height,
            configured_scroll_offsets=ScrollOffsets(),
            visible_line_to_row_col={i: (i, 0) for i in range(available_height)},
            rowcol_to_yx={},
            x_offset=xpos,
            y_offset=ypos,
            wrap_lines=False,
        )
        # Signal that we are no longer scrolling
        self.scrolling = 0

        # Trigger pre-rendering of children
        if self.pre_rendered is None:
            self.pre_render_children(available_width, available_height)

    @property
    def known_sizes(self) -> list[int]:
        """Map of child indices to height values."""
        return self._known_sizes_cache[get_app().render_counter,]

    def _known_sizes(self, render_counter: int) -> list[int]:
        """Calculate sizes of children once per render cycle."""
        sizes = {}
        missing = set()
        available_width = self.last_write_position.width
        available_height = self.last_write_position.height
        for i, child in enumerate(self._children):
            if isinstance(child, CachedContainer) and child.height:
                sizes[i] = child.preferred_height(
                    available_width, available_height
                ).preferred
            else:
                missing.add(i)
        avg = int(sum(sizes.values()) / (len(sizes) or 1))
        sizes.update(dict.fromkeys(missing, avg))
        return [v for k, v in sorted(sizes.items())]

    @property
    def vertical_scroll(self) -> int:
        """The best guess at the absolute vertical scroll position."""
        return (
            sum(self.known_sizes[: self._selected_slice.start])
            - self.selected_child_position
        )

    @vertical_scroll.setter
    def vertical_scroll(self, value: int) -> None:
        """Set the absolute vertical scroll position."""
        self.selected_child_position = (
            sum(self.known_sizes[: self._selected_slice.start]) - value
        )

    def all_children(self) -> Sequence[Container]:
        """Return the list of all children of this container."""
        _children = self._children
        if self.refresh_children or not self._children:
            self.refresh_children = False
            new_children = []
            new_child_hashes = set()
            for child in self.children_func():
                if not (
                    wrapped_child := (self._child_cache.get(child_hash := hash(child)))
                ):
                    wrapped_child = self._child_cache[child_hash] = CachedContainer(
                        child, mouse_handler_wrapper=self._mouse_handler_wrapper
                    )
                new_children.append(wrapped_child)
                new_child_hashes.add(child_hash)
            _children[:] = new_children

            # Clean up metacache
            for child_hash in set(self._child_cache) - new_child_hashes:
                del self._child_cache[child_hash]

            # Clean up positions
            self.index_positions = {
                i: pos
                for i, pos in self.index_positions.items()
                if i < len(self._children)
            }
        return _children

    def get_children(self) -> list[Container]:
        """Return the list of currently visible children to include in the layout."""
        # Ensure children are loaded
        self.all_children()
        # Return only the visible children
        return [
            self.get_child(i) for i in self.visible_indices if i < len(self._children)
        ]

    def get_child(self, index: int | None = None) -> CachedContainer:
        """Return a rendered instance of the child at the given index.

        If no index is given, the currently selected child is returned.

        Args:
            index: The index of the child to return.

        Returns:
            A rendered instance of the child.

        """
        if index is None:
            index = self.selected_slice.start
        if self._children:
            index = max(0, min(len(self._children) - 1, index))
            return self._children[index]
        else:
            return CachedContainer(Window())

    def scroll_to(
        self, index: int, anchor: Literal["top", "bottom"] | None = None
    ) -> None:
        """Scroll a child into view.

        Args:
            index: The child index to scroll into view
            anchor: Whether to scroll to the top or bottom the given child index

        """
        child = self.get_child(index)

        new_top: int | None = None
        if index in self.visible_indices:
            new_top = self.index_positions[index]
        else:
            if index < self._selected_slice.start:
                new_top = max(0, child.height - self.last_write_position.height)
            elif index == self._selected_slice.start:
                new_top = self.selected_child_position
            elif index > self._selected_slice.start:
                indices = [k for k, v in self.index_positions.items() if v is not None]
                if indices:
                    last_index = max(indices)
                    new_top = max(
                        min(
                            self.last_write_position.height,
                            (self.index_positions[last_index] or 0)
                            + self.get_child(last_index).height,
                        ),
                        0,
                    )

        # If the child height is not know, we'll need to render it to determine its height
        if not child.height:
            child.render(
                self.last_write_position.width,
                self.last_write_position.height,
            )

        if new_top is None or new_top < 0:
            if anchor == "top":
                self.selected_child_position = 0
            else:
                self.selected_child_position = min(
                    0, self.last_write_position.height - child.height
                )
        elif new_top > self.last_write_position.height - child.height:
            self.selected_child_position = max(
                0, self.last_write_position.height - child.height
            )
            if anchor == "bottom":
                self.selected_child_position -= (
                    child.height - self.last_write_position.height
                )
        else:
            self.selected_child_position = new_top

    def _scroll_up(self) -> None:
        """Scroll up one line: for compatibility with :py:class:`Window`."""
        self.scroll(1)

    def _scroll_down(self) -> None:
        """Scroll down one line: for compatibility with :py:class:`Window`."""
        self.scroll(-1)
