"""Overrides for PTK containers with optimized rendering.

This module provides enhanced versions of prompt_toolkit containers that:
- Only render visible lines rather than the entire content
- Use cached dimension calculations for better performance
- Support bounded write positions to clip rendering
- Share padding window instances for efficiency
- Apply cursor line styles more efficiently
"""

from __future__ import annotations

import logging
from functools import lru_cache, partial
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout import containers as ptk_containers
from prompt_toolkit.layout.containers import (
    Container,
    HorizontalAlign,
    VerticalAlign,
    WindowAlign,
    WindowRenderInfo,
)
from prompt_toolkit.layout.controls import DummyControl as PtkDummyControl
from prompt_toolkit.layout.controls import (
    FormattedTextControl,
    UIContent,
    fragment_list_width,
    to_formatted_text,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.screen import _CHAR_CACHE
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.utils import get_cwidth, take_using_weights, to_str

from euporie.core.cache import SimpleCache
from euporie.core.data_structures import DiInt
from euporie.core.layout.controls import DummyControl
from euporie.core.layout.screen import BoundedWritePosition
from euporie.core.mouse_events import MouseEvent

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.layout.containers import (
        AnyContainer,
        AnyDimension,
        Float,
    )
    from prompt_toolkit.layout.margins import Margin
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition
    from prompt_toolkit.mouse_events import MouseEvent as PtkMouseEvent


log = logging.getLogger(__name__)


class DimensionTuple(NamedTuple):
    """A hashable representation of a PTK :py:class:`Dimension`.

    This allows caching dimension calculations by making them hashable.
    Used internally by distribute_dimensions() for performance optimization.
    """

    min: int
    max: int
    preferred: int
    weight: int = 1


@lru_cache
def distribute_dimensions(
    size: int, dimensions: tuple[DimensionTuple, ...]
) -> list[int] | None:
    """Return the heights/widths for all rows/columns, or None when there is not enough space.

    This is a cached version of prompt_toolkit's dimension distribution logic that improves
    performance by memoizing calculations based on the input dimensions.

    Args:
        size: Total size to distribute
        dimensions: Tuple of DimensionTuple objects specifying min/max/preferred sizes

    Returns:
        List of distributed sizes or None if not enough space
    """
    if not dimensions:
        return []

    # Sum dimensions
    sum_dimensions = DimensionTuple(
        min=sum(d.min for d in dimensions),
        max=sum(d.max for d in dimensions),
        preferred=sum(d.preferred for d in dimensions),
    )

    # If there is not enough space for both.
    # Don't do anything.
    if sum_dimensions.min > size:
        return None

    # Find optimal sizes. (Start with minimal size, increase until we cover
    # the whole size.)
    sizes = [d.min for d in dimensions]

    child_generator = take_using_weights(
        items=list(range(len(dimensions))), weights=[d.weight for d in dimensions]
    )

    i = next(child_generator)

    # Increase until we meet at least the 'preferred' size.
    preferred_stop = min(size, sum_dimensions.preferred)
    preferred_dimensions = [d.preferred for d in dimensions]

    while sum(sizes) < preferred_stop:
        if sizes[i] < preferred_dimensions[i]:
            sizes[i] += 1
        i = next(child_generator)

    # Increase until we use all the available space. (or until "max")
    if not get_app().is_done:
        max_stop = min(size, sum_dimensions.max)
        max_dimensions = [d.max for d in dimensions]

        while sum(sizes) < max_stop:
            if sizes[i] < max_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

    return sizes


@lru_cache(maxsize=None)
class DummyContainer(Container):
    """A minimal container with fixed dimensions.

    This is a more efficient version of prompt_toolkit's DummyContainer that:
    - Supports explicit width/height
    - Uses caching for better performance
    - Avoids unnecessary style calculations
    """

    def __init__(self, width: int = 0, height: int = 0) -> None:
        """Define width and height if any."""
        self.width = width
        self.height = height

    def reset(self) -> None:
        """Reset the state of this container (does nothing)."""

    def preferred_width(self, max_available_width: int) -> Dimension:
        """Return a zero-width dimension."""
        return Dimension.exact(self.width)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """Return a zero-height dimension."""
        return Dimension.exact(self.height)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Write the actual content to the screen. Does nothing."""

    def get_children(self) -> list[Container]:
        """Return an empty list of child :class:`.Container` objects."""
        return []


class HSplit(ptk_containers.HSplit):
    """Several layouts, one stacked above/under the other."""

    _pad_window: Window

    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        align: VerticalAlign = VerticalAlign.JUSTIFY,
        padding: AnyDimension = 0,
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None:
        """Initialize the HSplit with a cache."""
        if window_too_small is None:
            window_too_small = DummyContainer()
        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style,
        )

    def _divide_heights(self, write_position: WritePosition) -> list[int] | None:
        """Calculate and cache heights for all rows."""
        width = write_position.width
        height = write_position.height
        dimensions = [c.preferred_height(width, height) for c in self._all_children]
        result = distribute_dimensions(
            height,
            tuple(
                DimensionTuple(
                    min=d.min, max=d.max, preferred=d.preferred, weight=d.weight
                )
                for d in dimensions
            ),
        )
        return result

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Render the prompt to a `Screen` instance.

        :param screen: The :class:`~prompt_toolkit.layout.screen.Screen` class
            to which the output has to be written.
        """
        assert isinstance(write_position, BoundedWritePosition)
        sizes = self._divide_heights(write_position)
        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        if sizes is None:
            self.window_too_small.write_to_screen(
                screen, mouse_handlers, write_position, style, erase_bg, z_index
            )
        else:
            #
            ypos = write_position.ypos
            xpos = write_position.xpos
            width = write_position.width
            bbox = write_position.bbox

            # Draw child panes.
            for s, c in zip(sizes, self._all_children):
                c.write_to_screen(
                    screen,
                    mouse_handlers,
                    BoundedWritePosition(
                        xpos,
                        ypos,
                        width,
                        s,
                        bbox=DiInt(
                            top=max(0, bbox.top - (ypos - write_position.ypos)),
                            right=bbox.right,
                            bottom=max(
                                0,
                                bbox.bottom
                                - (
                                    write_position.ypos
                                    + write_position.height
                                    - ypos
                                    - s
                                ),
                            ),
                            left=bbox.left,
                        ),
                    ),
                    style,
                    erase_bg,
                    z_index,
                )
                ypos += s

            # Fill in the remaining space. This happens when a child control
            # refuses to take more space and we don't have any padding. Adding a
            # dummy child control for this (in `self._all_children`) is not
            # desired, because in some situations, it would take more space, even
            # when it's not required. This is required to apply the styling.
            remaining_height = write_position.ypos + write_position.height - ypos
            if remaining_height > 0:
                self._remaining_space_window.write_to_screen(
                    screen,
                    mouse_handlers,
                    BoundedWritePosition(
                        xpos,
                        ypos,
                        width,
                        remaining_height,
                        bbox=DiInt(
                            top=max(0, bbox.top - (ypos - write_position.ypos)),
                            right=bbox.right,
                            bottom=min(bbox.bottom, remaining_height),
                            left=bbox.left,
                        ),
                    ),
                    style,
                    erase_bg,
                    z_index,
                )

    @property
    def pad_window(self) -> Window:
        """Create a single instance of the padding window."""
        try:
            return self._pad_window
        except AttributeError:
            self._pad_window = Window(
                height=self.padding,
                char=self.padding_char,
                style=self.padding_style,
            )
            return self._pad_window

    @property
    def _all_children(self) -> list[Container]:
        """List of child objects, including padding."""

        def get() -> list[Container]:
            result: list[Container] = []
            # Padding Top.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.BOTTOM):
                result.append(Window(width=Dimension(preferred=0)))
            # The children with padding.
            for child in self.children:
                result.append(child)
                result.append(self.pad_window)
            if result:
                result.pop()
            # Padding right.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.TOP):
                result.append(Window(width=Dimension(preferred=0)))
            return result

        return self._children_cache.get(tuple(self.children), get)


class VSplit(ptk_containers.VSplit):
    """Several layouts, one stacked left/right of the other."""

    _pad_window: Window

    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        align: HorizontalAlign = HorizontalAlign.JUSTIFY,
        padding: AnyDimension = 0,
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None:
        """Initialize the VSplit with a cache."""
        if window_too_small is None:
            window_too_small = DummyContainer()
        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style,
        )

    def _divide_widths(self, width: int) -> list[int] | None:
        """Calculate and cache widths for all columns."""
        dimensions = [c.preferred_width(width) for c in self._all_children]
        result = distribute_dimensions(
            width,
            tuple(
                DimensionTuple(
                    min=d.min, max=d.max, preferred=d.preferred, weight=d.weight
                )
                for d in dimensions
            ),
        )
        return result

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Render the prompt to a `Screen` instance.

        :param screen: The :class:`~prompt_toolkit.layout.screen.Screen` class
            to which the output has to be written.
        """
        assert isinstance(write_position, BoundedWritePosition)
        if not self.children:
            return

        children = self._all_children
        sizes = self._divide_widths(write_position.width)
        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        # If there is not enough space.
        if sizes is None:
            self.window_too_small.write_to_screen(
                screen, mouse_handlers, write_position, style, erase_bg, z_index
            )
            return

        # Calculate heights, take the largest possible, but not larger than
        # write_position.height.
        heights = [
            child.preferred_height(width, write_position.height).preferred
            for width, child in zip(sizes, children)
        ]
        height = max(write_position.height, min(write_position.height, max(heights)))

        #
        ypos = write_position.ypos
        xpos = write_position.xpos
        bbox = write_position.bbox

        # Draw all child panes.
        for s, c in zip(sizes, children):
            c.write_to_screen(
                screen,
                mouse_handlers,
                BoundedWritePosition(
                    xpos,
                    ypos,
                    s,
                    height,
                    DiInt(
                        top=bbox.top,
                        right=max(
                            bbox.right,
                            xpos + s - write_position.xpos - write_position.width,
                        ),
                        bottom=bbox.bottom,
                        left=max(0, bbox.left - write_position.xpos - xpos),
                    ),
                ),
                style,
                erase_bg,
                z_index,
            )
            xpos += s

        # Fill in the remaining space. This happens when a child control
        # refuses to take more space and we don't have any padding. Adding a
        # dummy child control for this (in `self._all_children`) is not
        # desired, because in some situations, it would take more space, even
        # when it's not required. This is required to apply the styling.
        remaining_width = write_position.xpos + write_position.width - xpos
        if remaining_width > 0:
            self._remaining_space_window.write_to_screen(
                screen,
                mouse_handlers,
                BoundedWritePosition(
                    xpos,
                    ypos,
                    remaining_width,
                    height,
                    DiInt(
                        bbox.top,
                        max(0, bbox.left - write_position.xpos - xpos),
                        bbox.bottom,
                        max(
                            bbox.right,
                            write_position.xpos + write_position.width - xpos - s,
                        ),
                    ),
                ),
                style,
                erase_bg,
                z_index,
            )

    @property
    def pad_window(self) -> Window:
        """Create a single instance of the padding window."""
        try:
            return self._pad_window
        except AttributeError:
            self._pad_window = Window(
                width=self.padding,
                char=self.padding_char,
                style=self.padding_style,
            )
            return self._pad_window

    @property
    def _all_children(self) -> list[Container]:
        """List of child objects, including padding."""

        def get() -> list[Container]:
            result: list[Container] = []

            # Padding left.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.RIGHT):
                result.append(Window(width=Dimension(preferred=0)))
            # The children with padding.
            for child in self.children:
                result.append(child)
                result.append(self.pad_window)
            if result:
                result.pop()
            # Padding right.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.LEFT):
                result.append(Window(width=Dimension(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)


class Window(ptk_containers.Window):
    """Container that holds a control."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize `Windows`, updating the default control for empty windows."""
        super().__init__(*args, **kwargs)
        if isinstance(self.content, PtkDummyControl):
            self.content = DummyControl()
        # Use thread-safe cache for margin widths
        self._margin_width_cache: SimpleCache[tuple[Margin, int], int] = SimpleCache(
            maxsize=1
        )

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Write window to screen."""
        # If dont_extend_width/height was given, then reduce width/height in
        # WritePosition, if the parent wanted us to paint in a bigger area.
        # (This happens if this window is bundled with another window in a
        # HSplit/VSplit, but with different size requirements.)
        if isinstance(write_position, BoundedWritePosition):
            bbox = write_position.bbox
        else:
            bbox = DiInt(0, 0, 0, 0)
        write_position = BoundedWritePosition(
            xpos=write_position.xpos,
            ypos=write_position.ypos,
            width=write_position.width,
            height=write_position.height,
            bbox=bbox,
        )

        if self.dont_extend_width():
            write_position.width = min(
                write_position.width,
                self.preferred_width(write_position.width).preferred,
            )

        if self.dont_extend_height():
            write_position.height = min(
                write_position.height,
                self.preferred_height(
                    write_position.width, write_position.height
                ).preferred,
            )

        # Draw
        z_index = z_index if self.z_index is None else self.z_index

        draw_func = partial(
            self._write_to_screen_at_index,
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
        )

        if z_index is None or z_index <= 0:
            # When no z_index is given, draw right away.
            draw_func()
        else:
            # Otherwise, postpone.
            screen.draw_with_z_index(z_index=z_index, draw_func=draw_func)

    def _write_to_screen_at_index(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
    ) -> None:
        assert isinstance(write_position, BoundedWritePosition)
        # Don't bother writing invisible windows.
        # (We save some time, but also avoid applying last-line styling.)
        if write_position.height <= 0 or write_position.width <= 0:
            return

        # Calculate margin sizes.
        left_margin_widths = [self._get_margin_width(m) for m in self.left_margins]
        right_margin_widths = [self._get_margin_width(m) for m in self.right_margins]
        total_margin_width = sum(left_margin_widths + right_margin_widths)

        # Render UserControl.
        ui_content = self.content.create_content(
            write_position.width - total_margin_width, write_position.height
        )
        assert isinstance(ui_content, UIContent)

        # Scroll content.
        wrap_lines = self.wrap_lines()
        self._scroll(
            ui_content, write_position.width - total_margin_width, write_position.height
        )

        # Erase background and fill with `char`.
        self._fill_bg(screen, write_position, erase_bg)

        # Resolve `align` attribute.
        align = self.align() if callable(self.align) else self.align

        # Write body
        bbox = write_position.bbox
        visible_line_to_row_col, rowcol_to_yx = self._copy_body(
            ui_content,
            screen,
            write_position,
            sum(left_margin_widths),
            write_position.width - total_margin_width - bbox.left - bbox.right,
            self.vertical_scroll,
            self.horizontal_scroll,
            wrap_lines=wrap_lines,
            highlight_lines=True,
            vertical_scroll_2=self.vertical_scroll_2,
            always_hide_cursor=self.always_hide_cursor(),
            has_focus=get_app().layout.current_control == self.content,
            align=align,
            get_line_prefix=self.get_line_prefix,
        )

        # Remember render info. (Set before generating the margins. They need this.)
        x_offset = write_position.xpos + sum(left_margin_widths)
        y_offset = write_position.ypos

        render_info = WindowRenderInfo(
            window=self,
            ui_content=ui_content,
            horizontal_scroll=self.horizontal_scroll,
            vertical_scroll=self.vertical_scroll,
            window_width=write_position.width - total_margin_width,
            window_height=write_position.height,
            configured_scroll_offsets=self.scroll_offsets,
            visible_line_to_row_col=visible_line_to_row_col,
            rowcol_to_yx=rowcol_to_yx,
            x_offset=x_offset,
            y_offset=y_offset,
            wrap_lines=wrap_lines,
        )
        self.render_info = render_info

        # Set mouse handlers.
        def mouse_handler(mouse_event: PtkMouseEvent) -> NotImplementedOrNone:
            """Turn screen coordinates into line coordinates."""
            # Don't handle mouse events outside of the current modal part of
            # the UI.
            if self not in get_app().layout.walk_through_modal_area():
                return NotImplemented

            # Find row/col position first.
            yx_to_rowcol = {v: k for k, v in rowcol_to_yx.items()}
            y = mouse_event.position.y
            x = mouse_event.position.x

            # If clicked below the content area, look for a position in the
            # last line instead.
            max_y = write_position.ypos + len(visible_line_to_row_col) - 1
            y = min(max_y, y)
            result: NotImplementedOrNone

            while x >= 0:
                try:
                    row, col = yx_to_rowcol[y, x]
                except KeyError:
                    # Try again. (When clicking on the right side of double
                    # width characters, or on the right side of the input.)
                    x -= 1
                else:
                    # Found position, call handler of UIControl.
                    result = self.content.mouse_handler(
                        MouseEvent(
                            position=Point(x=col, y=row),
                            event_type=mouse_event.event_type,
                            button=mouse_event.button,
                            modifiers=mouse_event.modifiers,
                            cell_position=getattr(mouse_event, "cell_position", None),
                        )
                    )
                    break
            else:
                # nobreak.
                # (No x/y coordinate found for the content. This happens in
                # case of a DummyControl, that does not have any content.
                # Report (0,0) instead.)
                result = self.content.mouse_handler(
                    MouseEvent(
                        position=Point(x=0, y=0),
                        event_type=mouse_event.event_type,
                        button=mouse_event.button,
                        modifiers=mouse_event.modifiers,
                        cell_position=getattr(mouse_event, "cell_position", None),
                    )
                )

            # If it returns NotImplemented, handle it here.
            if result == NotImplemented:
                result = self._mouse_handler(mouse_event)

            return result

        mouse_handlers.set_mouse_handler_for_range(
            x_min=write_position.xpos + max(sum(left_margin_widths), bbox.left),
            x_max=write_position.xpos
            + write_position.width
            - max(total_margin_width, bbox.right),
            y_min=write_position.ypos + bbox.top,
            y_max=write_position.ypos + write_position.height - bbox.bottom,
            handler=mouse_handler,
        )

        # Render and copy margins.
        move_x = 0

        def render_margin(m: Margin, width: int) -> UIContent:
            """Render margin. Return `Screen`."""
            # Retrieve margin fragments.
            fragments = m.create_margin(render_info, width, write_position.height)

            # Turn it into a UIContent object.
            # already rendered those fragments using this size.)
            return FormattedTextControl(fragments).create_content(
                width + 1, write_position.height
            )

        for m, width in zip(self.left_margins, left_margin_widths):
            if width > 0:  # (ConditionalMargin returns a zero width. -- Don't render.)
                # Create screen for margin.
                margin_content = render_margin(m, width)

                # Copy and shift X.
                self._copy_margin(margin_content, screen, write_position, move_x, width)
                move_x += width

        move_x = write_position.width - sum(right_margin_widths)

        for m, width in zip(self.right_margins, right_margin_widths):
            # Create screen for margin.
            margin_content = render_margin(m, width)

            # Copy and shift X.
            self._copy_margin(margin_content, screen, write_position, move_x, width)
            move_x += width

        # Apply 'self.style'
        self._apply_style(screen, write_position, parent_style)

        # Additionally apply style to line with cursor if it is visible
        if ui_content.show_cursor and not self.always_hide_cursor():
            _col, _row = ui_content.cursor_position
            if cp_yx := rowcol_to_yx.get((_row, _col)):
                self._apply_style(
                    screen,
                    BoundedWritePosition(
                        xpos=write_position.xpos,
                        ypos=cp_yx[0],
                        width=write_position.width,
                        height=1,
                    ),
                    parent_style,
                )

        # Tell the screen that this user control has been painted at this
        # position.
        screen.visible_windows_to_write_positions[self] = write_position

    def _copy_body(
        self,
        ui_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
        vertical_scroll: int = 0,
        horizontal_scroll: int = 0,
        wrap_lines: bool = False,
        highlight_lines: bool = False,
        vertical_scroll_2: int = 0,
        always_hide_cursor: bool = False,
        has_focus: bool = False,
        align: WindowAlign = WindowAlign.LEFT,
        get_line_prefix: Callable[[int, int], AnyFormattedText] | None = None,
    ) -> tuple[dict[int, tuple[int, int]], dict[tuple[int, int], tuple[int, int]]]:
        """Copy the UIContent into the output screen."""
        assert isinstance(write_position, BoundedWritePosition)
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos
        line_count = ui_content.line_count
        new_buffer = new_screen.data_buffer
        empty_char = _CHAR_CACHE["", ""]

        bbox = write_position.bbox

        # Map visible line number to (row, col) of input.
        # 'col' will always be zero if line wrapping is off.
        visible_line_to_row_col: dict[int, tuple[int, int]] = {}

        # Maps (row, col) from the input to (y, x) screen coordinates.
        rowcol_to_yx: dict[tuple[int, int], tuple[int, int]] = {}

        def copy_line(
            line: StyleAndTextTuples,
            lineno: int,
            x: int,
            y: int,
            is_input: bool = False,
        ) -> tuple[int, int]:
            """Copy over a single line to the output screen."""
            current_rowcol_to_yx = (
                rowcol_to_yx if is_input else {}
            )  # Throwaway dictionary.

            # Draw line prefix.
            if is_input and get_line_prefix:
                prompt = to_formatted_text(get_line_prefix(lineno, 0))
                x, y = copy_line(prompt, lineno, x, y, is_input=False)

            # Scroll horizontally.
            skipped = 0  # Characters skipped because of horizontal scrolling.
            if horizontal_scroll and is_input:
                h_scroll = horizontal_scroll
                line = explode_text_fragments(line)
                while h_scroll > 0 and line:
                    h_scroll -= get_cwidth(line[0][1])
                    skipped += 1
                    del line[:1]  # Remove first character.

                x -= h_scroll  # When scrolling over double width character,
                # this can end up being negative.

            # Align this line. (Note that this doesn't work well when we use
            # get_line_prefix and that function returns variable width prefixes.)
            if align == WindowAlign.CENTER:
                line_width = fragment_list_width(line)
                if line_width < width:
                    x += (width - line_width) // 2
            elif align == WindowAlign.RIGHT:
                line_width = fragment_list_width(line)
                if line_width < width:
                    x += width - line_width

            col = 0
            wrap_count = 0
            for style, text, *_ in line:
                new_buffer_row = new_buffer[y + ypos]

                # Remember raw VT escape sequences. (E.g. FinalTerm's
                # escape sequences.)
                if "[ZeroWidthEscape]" in style:
                    new_screen.zero_width_escapes[y + ypos][x + xpos] += text
                    continue

                for c in text:
                    char = _CHAR_CACHE[c, style]
                    char_width = char.width

                    # Wrap when the line width is exceeded.
                    if wrap_lines and x + char_width > width:
                        visible_line_to_row_col[y + 1] = (
                            lineno,
                            visible_line_to_row_col[y][1] + x,
                        )
                        y += 1
                        wrap_count += 1
                        x = 0

                        # Insert line prefix (continuation prompt).
                        if is_input and get_line_prefix:
                            prompt = to_formatted_text(
                                get_line_prefix(lineno, wrap_count)
                            )
                            x, y = copy_line(prompt, lineno, x, y, is_input=False)

                        new_buffer_row = new_buffer[y + ypos]

                        if y >= write_position.height:
                            return x, y  # Break out of all for loops.

                    # Set character in screen and shift 'x'.
                    if x >= 0 and y >= 0 and x < width:
                        new_buffer_row[x + xpos] = char

                        # When we print a multi width character, make sure
                        # to erase the neighbors positions in the screen.
                        # (The empty string if different from everything,
                        # so next redraw this cell will repaint anyway.)
                        if char_width > 1:
                            for i in range(1, char_width):
                                new_buffer_row[x + xpos + i] = empty_char

                        # If this is a zero width characters, then it's
                        # probably part of a decomposed unicode character.
                        # See: https://en.wikipedia.org/wiki/Unicode_equivalence
                        # Merge it in the previous cell.
                        elif char_width == 0:
                            # Handle all character widths. If the previous
                            # character is a multiwidth character, then
                            # merge it two positions back.
                            for pw in [2, 1]:  # Previous character width.
                                if (
                                    x - pw >= 0
                                    and new_buffer_row[x + xpos - pw].width == pw
                                ):
                                    prev_char = new_buffer_row[x + xpos - pw]
                                    char2 = _CHAR_CACHE[
                                        prev_char.char + c, prev_char.style
                                    ]
                                    new_buffer_row[x + xpos - pw] = char2

                        # Keep track of write position for each character.
                        current_rowcol_to_yx[lineno, col + skipped] = (
                            y + ypos,
                            x + xpos,
                        )

                    col += 1
                    x += char_width
            return x, y

        # Copy content.
        y = -vertical_scroll_2
        lineno = vertical_scroll

        # Render lines down to the end of the visible region (or to the cursor
        # position, whichever is lower)
        cursor_visible = ui_content.show_cursor and not self.always_hide_cursor()
        while (
            y < write_position.height - bbox.bottom
            or (cursor_visible and lineno <= ui_content.cursor_position.y)
        ) and lineno < line_count:
            visible_line_to_row_col[y] = (lineno, horizontal_scroll)

            # If lines are wrapped, we need to render all of them so we know how many
            # rows each line occupies.
            # Otherwise, we can skip rendering lines which are not visible.
            # Also always render the line with the visible cursor so we know it's position
            if (wrap_lines or bbox.top <= y) or (
                cursor_visible and lineno == ui_content.cursor_position.y
            ):
                # Take the next line and copy it in the real screen.
                line = ui_content.get_line(lineno)
                # Copy margin and actual line.
                x = 0
                x, y = copy_line(line, lineno, x, y, is_input=True)

            lineno += 1
            y += 1

        def cursor_pos_to_screen_pos(row: int, col: int) -> Point:
            """Translate row/col from UIContent to real Screen coordinates."""
            try:
                y, x = rowcol_to_yx[row, col]
            except KeyError:
                # Normally this should never happen. (It is a bug, if it happens.)
                # But to be sure, return (0, 0)
                return Point(x=0, y=0)

                # raise ValueError(
                #     'Invalid position. row=%r col=%r, vertical_scroll=%r, '
                #     'horizontal_scroll=%r, height=%r' %
                #     (row, col, vertical_scroll, horizontal_scroll, write_position.height))
            else:
                return Point(x=x, y=y)

        # Set cursor and menu positions.
        if ui_content.cursor_position:
            screen_cursor_position = cursor_pos_to_screen_pos(
                ui_content.cursor_position.y, ui_content.cursor_position.x
            )

            if has_focus:
                new_screen.set_cursor_position(self, screen_cursor_position)

                if always_hide_cursor:
                    new_screen.show_cursor = False
                else:
                    new_screen.show_cursor = ui_content.show_cursor

                self._highlight_digraph(new_screen)

            if highlight_lines:
                self._highlight_cursorlines(
                    new_screen,
                    screen_cursor_position,
                    xpos,
                    ypos,
                    width,
                    write_position.height,
                )

        # Draw input characters from the input processor queue.
        if has_focus and ui_content.cursor_position:
            self._show_key_processor_key_buffer(new_screen)

        # Set menu position.
        if ui_content.menu_position:
            new_screen.set_menu_position(
                self,
                cursor_pos_to_screen_pos(
                    ui_content.menu_position.y, ui_content.menu_position.x
                ),
            )

        # Update output screen height.
        new_screen.height = max(new_screen.height, ypos + write_position.height)

        return visible_line_to_row_col, rowcol_to_yx

    def _copy_margin(
        self,
        margin_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
    ) -> None:
        """Copy characters from the margin screen to the real screen."""
        assert isinstance(write_position, BoundedWritePosition)
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos
        wp_bbox = write_position.bbox

        margin_write_position = BoundedWritePosition(
            xpos, ypos, width, write_position.height, wp_bbox
        )
        self._copy_body(margin_content, new_screen, margin_write_position, 0, width)

    def _fill_bg(
        self, screen: Screen, write_position: WritePosition, erase_bg: bool
    ) -> None:
        """Erase/fill the background."""
        assert isinstance(write_position, BoundedWritePosition)
        char: str | None
        char = self.char() if callable(self.char) else self.char

        if erase_bg or char:
            wp = write_position
            char_obj = _CHAR_CACHE[char or " ", ""]

            bbox = wp.bbox
            for y in range(wp.ypos + bbox.top, wp.ypos + wp.height - bbox.bottom):
                row = screen.data_buffer[y]
                for x in range(wp.xpos + bbox.left, wp.xpos + wp.width - bbox.right):
                    row[x] = char_obj

    def _apply_style(
        self,
        new_screen: Screen,
        write_position: WritePosition,
        parent_style: str,
    ) -> None:
        # Apply `self.style`.
        style = f"{parent_style} {to_str(self.style)}"

        new_screen.fill_area(write_position, style=style, after=False)

        # Apply the 'last-line' class to the last line of each Window. This can
        # be used to apply an 'underline' to the user control.
        if isinstance(write_position, BoundedWritePosition):
            if write_position.bbox.bottom == 0:
                wp = BoundedWritePosition(
                    write_position.xpos,
                    write_position.ypos + write_position.height - 1,
                    write_position.width,
                    1,
                )
                new_screen.fill_area(wp, "class:last-line", after=True)
        else:
            new_screen.fill_area(write_position, "class:last-line", after=True)

    def _mouse_handler(self, mouse_event: PtkMouseEvent) -> NotImplementedOrNone:
        """Mouse handler. Called when the UI control doesn't handle this particular event.

        Return `NotImplemented` if nothing was done as a consequence of this
        key binding (no UI invalidate required in that case).
        """
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            return self._scroll_down()
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            return self._scroll_up()

        return NotImplemented

    def _scroll_down(self) -> NotImplementedOrNone:  # type: ignore [override]
        """Scroll window down."""
        info = self.render_info

        if info is None:
            return NotImplemented

        if self.vertical_scroll < info.content_height - info.window_height:
            if info.cursor_position.y <= info.configured_scroll_offsets.top:
                self.content.move_cursor_down()
            self.vertical_scroll += 1
            return None

        return NotImplemented

    def _scroll_up(self) -> NotImplementedOrNone:  # type: ignore [override]
        """Scroll window up."""
        info = self.render_info

        if info is None:
            return NotImplemented

        if info.vertical_scroll > 0:
            # TODO: not entirely correct yet in case of line wrapping and long lines.
            if (
                info.cursor_position.y
                >= info.window_height - 1 - info.configured_scroll_offsets.bottom
            ):
                self.content.move_cursor_up()
            self.vertical_scroll -= 1
            return None

        return NotImplemented


class FloatContainer(ptk_containers.FloatContainer):
    """A `FloatContainer` which uses :py`BoundedWritePosition`s."""

    def _draw_float(
        self,
        fl: Float,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw a single Float."""
        # When a menu_position was given, use this instead of the cursor
        # position. (These cursor positions are absolute, translate again
        # relative to the write_position.)
        # Note: This should be inside the for-loop, because one float could
        #       set the cursor position to be used for the next one.
        cpos = screen.get_menu_position(
            fl.attach_to_window or get_app().layout.current_window
        )
        cursor_position = Point(
            x=cpos.x - write_position.xpos, y=cpos.y - write_position.ypos
        )

        fl_width = fl.get_width()
        fl_height = fl.get_height()
        width: int
        height: int
        xpos: int
        ypos: int

        # Left & width given.
        if fl.left is not None and fl_width is not None:
            xpos = fl.left
            width = fl_width
        # Left & right given -> calculate width.
        elif fl.left is not None and fl.right is not None:
            xpos = fl.left
            width = write_position.width - fl.left - fl.right
        # Width & right given -> calculate left.
        elif fl_width is not None and fl.right is not None:
            xpos = write_position.width - fl.right - fl_width
            width = fl_width
        # Near x position of cursor.
        elif fl.xcursor:
            if fl_width is None:
                width = fl.content.preferred_width(write_position.width).preferred
                width = min(write_position.width, width)
            else:
                width = fl_width

            xpos = cursor_position.x
            if xpos + width > write_position.width:
                xpos = max(0, write_position.width - width)
        # Only width given -> center horizontally.
        elif fl_width:
            xpos = int((write_position.width - fl_width) / 2)
            width = fl_width
        # Otherwise, take preferred width from float content.
        else:
            width = fl.content.preferred_width(write_position.width).preferred

            if fl.left is not None:
                xpos = fl.left
            elif fl.right is not None:
                xpos = max(0, write_position.width - width - fl.right)
            else:  # Center horizontally.
                xpos = max(0, int((write_position.width - width) / 2))

            # Trim.
            width = min(width, write_position.width - xpos)

        # Top & height given.
        if fl.top is not None and fl_height is not None:
            ypos = fl.top
            height = fl_height
        # Top & bottom given -> calculate height.
        elif fl.top is not None and fl.bottom is not None:
            ypos = fl.top
            height = write_position.height - fl.top - fl.bottom
        # Height & bottom given -> calculate top.
        elif fl_height is not None and fl.bottom is not None:
            ypos = write_position.height - fl_height - fl.bottom
            height = fl_height
        # Near cursor.
        elif fl.ycursor:
            ypos = cursor_position.y + (0 if fl.allow_cover_cursor else 1)

            if fl_height is None:
                height = fl.content.preferred_height(
                    width, write_position.height
                ).preferred
            else:
                height = fl_height

            # Reduce height if not enough space. (We can use the height
            # when the content requires it.)
            if height > write_position.height - ypos:
                if write_position.height - ypos + 1 >= ypos:
                    # When the space below the cursor is more than
                    # the space above, just reduce the height.
                    height = write_position.height - ypos
                else:
                    # Otherwise, fit the float above the cursor.
                    height = min(height, cursor_position.y)
                    ypos = cursor_position.y - height

        # Only height given -> center vertically.
        elif fl_height:
            ypos = int((write_position.height - fl_height) / 2)
            height = fl_height
        # Otherwise, take preferred height from content.
        else:
            height = fl.content.preferred_height(width, write_position.height).preferred

            if fl.top is not None:
                ypos = fl.top
            elif fl.bottom is not None:
                ypos = max(0, write_position.height - height - fl.bottom)
            else:  # Center vertically.
                ypos = max(0, int((write_position.height - height) / 2))

            # Trim.
            height = min(height, write_position.height - ypos)

        # Write float.
        # (xpos and ypos can be negative: a float can be partially visible.)
        if height > 0 and width > 0:
            wp = BoundedWritePosition(
                xpos=xpos + write_position.xpos,
                ypos=ypos + write_position.ypos,
                width=width,
                height=height,
            )

            if not fl.hide_when_covering_content or self._area_is_empty(screen, wp):
                fl.content.write_to_screen(
                    screen,
                    mouse_handlers,
                    wp,
                    style,
                    erase_bg=not fl.transparent(),
                    z_index=z_index,
                )


ptk_containers.HSplit = HSplit  # type: ignore[misc]
ptk_containers.VSplit = VSplit  # type: ignore[misc]
ptk_containers.Window = Window  # type: ignore[misc]
ptk_containers.FloatContainer = FloatContainer  # type: ignore[misc]
