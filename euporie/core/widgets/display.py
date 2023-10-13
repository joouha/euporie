"""Define custom controls which re-render on resize."""

from __future__ import annotations

import logging
import weakref
from abc import ABCMeta
from functools import partial
from math import ceil
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters.app import has_completions
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_width, split_lines
from prompt_toolkit.layout.containers import ConditionalContainer, Float, VSplit, Window
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event, to_str

from euporie.core.commands import add_cmd
from euporie.core.convert.core import convert, find_route
from euporie.core.convert.utils import data_pixel_size, pixels_to_cell_size
from euporie.core.current import get_app
from euporie.core.data_structures import DiInt
from euporie.core.filters import (
    display_has_focus,
    has_dialog,
    has_menus,
    in_tmux,
    scrollable,
)
from euporie.core.ft.utils import wrap
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.terminal import tmuxify
from euporie.core.widgets.page import BoundedWritePosition

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable, Iterable

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.layout.screen import Screen


log = logging.getLogger(__name__)


class DisplayControl(UIControl):
    """A data formatter, which displays cell output data.

    It will attempt to display the data in the best way possible, and reacts to resize
    events - i.e. images are downscaled to fit, markdown is re-flowed, etc.
    """

    def __init__(
        self,
        data: Any,
        format_: str,
        path: Path | None = None,
        fg_color: str | None = None,
        bg_color: str | None = None,
        sizing_func: Callable[[], tuple[int, float]] | None = None,
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
    ) -> None:
        """Create a new data formatter control.

        Args:
            data: Raw cell output data
            format_: The conversion format of the data to render
            path: The path to the data's original location
            fg_color: The foreground colour to use when rendering this output
            bg_color: The background colour to use when rendering this output
            sizing_func: Function which returns the maximum width and aspect ratio of
                the output
            focusable: Whether the control can be focused
            focus_on_click: Whether to focus the control when clicked
            wrap_lines: Whether lines of output should be wrapped

        """
        self._data = data
        self.format_ = format_
        self.path = path
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.focusable = to_filter(focusable)
        self.focus_on_click = to_filter(focus_on_click)
        self.wrap_lines = to_filter(wrap_lines)
        self.key_bindings = load_registered_bindings(
            "euporie.core.widgets.display.Display"
        )
        self._cursor_position = Point(x=0, y=0)
        self.dy = 0
        self.app = get_app()

        # Whenever the data changes, the UI has to be updated.
        self.on_data_changed = Event(self)
        # Whenever the cursor position changes, the UI has to be updated.
        self.on_cursor_position_changed = Event(self)
        # Allow invalidation events to be added to a specific instance of this control
        self.invalidate_events: list[Event] = [
            self.on_data_changed,
            self.on_cursor_position_changed,
        ]

        self.sizing_func = sizing_func or (lambda: (0, 0))
        self._max_cols = 0
        self._aspect = 0.0

        self.rendered_lines: list[StyleAndTextTuples] = []
        self._format_cache: SimpleCache = SimpleCache(maxsize=50)
        self._content_cache: SimpleCache = SimpleCache(maxsize=50)
        self._size_cache: SimpleCache = SimpleCache(maxsize=1)

    def reset(self) -> None:
        """Clear the display control's caches (required if the control's data changes)."""
        self._format_cache.clear()
        self._size_cache.clear()
        self._content_cache.clear()

    @property
    def data(self) -> Any:
        """Return the control's display data."""
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        """Set the control's data."""
        self._data = value
        self.reset()
        self.on_data_changed.fire()

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Return the control's key bindings."""
        return self.key_bindings

    @property
    def cursor_position(self) -> Point:
        """Get the cursor position."""
        return self._cursor_position

    @cursor_position.setter
    def cursor_position(self, value: Point) -> None:
        """Set the cursor position."""
        changed = self._cursor_position != value
        self._cursor_position = value
        if changed:
            self.on_cursor_position_changed.fire()

    def move_cursor_down(self) -> None:
        """Move the cursor down one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x, y=y + 1)

    def move_cursor_up(self) -> None:
        """Move the cursor up one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x, y=max(0, y - 1))

    def move_cursor_left(self) -> None:
        """Move the cursor down one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=max(0, x - 1), y=y)

    def move_cursor_right(self) -> None:
        """Move the cursor up one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x + 1, y=y)

    def is_focusable(self) -> bool:
        """Determine if the current control is focusable."""
        return self.focusable()

    def size(self) -> None:
        """Load the maximum cell width and aspect ratio of the output."""
        self._max_cols, self._aspect = self._size_cache.get(
            self.app.render_counter, self.sizing_func
        )

    def hide(self) -> None:
        """Hide the output from show."""
        pass

    @property
    def max_cols(self) -> int:
        """Load the maximum width of the output in terminal columns."""
        self.size()
        return self._max_cols

    @property
    def aspect(self) -> float:
        """Lazily load the aspect ratio of the output."""
        self.size()
        return self._aspect

    def preferred_width(self, max_available_width: int) -> int | None:
        """Return the width of the rendered content."""
        self.max_available_width = max_available_width
        return (
            min(self.max_cols, max_available_width)
            if self.max_cols
            else max_available_width
        )

    def get_rendered_lines(
        self, width: int, height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Render the output data."""
        return []

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int:
        """Return the number of lines in the rendered content."""
        if self.aspect:
            return ceil(min(width, self.max_cols) * self.aspect)
        else:
            self.rendered_lines = self.get_rendered_lines(
                width, max_available_height, self.wrap_lines()
            )
            return len(self.rendered_lines)

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate rendered output at a given size.

        Args:
            width: The desired output width
            height: The desired output height

        Returns:
            `UIContent` for the given output size.

        """
        cols = min(self.max_cols, width) if self.max_cols else width
        rows = ceil(cols * self.aspect) if self.aspect else height
        wrap_lines = self.wrap_lines()

        def get_content() -> dict[str, Any]:
            rendered_lines = self.get_rendered_lines(
                width=cols, height=rows, wrap_lines=wrap_lines
            )
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: int) -> StyleAndTextTuples:
                # Return blank lines if the renderer expects more content than we have
                line = rendered_lines[i] if i < line_count else []
                # Add space at end of empty lines as that is a possible cursor position
                # This is what PTK does, and fixes a bug where scrolling would stop
                # working when the cursor was on an empty line.
                if not line:
                    line += [("", " ")]
                return line

            return {
                "get_line": get_line,
                "line_count": line_count,
                "menu_position": Point(0, 0),
            }

        # Re-render if the image width changes, or the terminal character size changes
        key = (cols, self.app.term_info.cell_size_px, wrap_lines)
        return UIContent(
            cursor_position=self.cursor_position,
            **self._content_cache.get(key, get_content),
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Mouse handler for this control."""
        if self.focus_on_click() and mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.app.layout.current_control = self
            return None
        return NotImplemented

    def get_invalidate_events(self) -> Iterable[Event[object]]:
        """Return the Window invalidate events."""
        yield from self.invalidate_events

    @property
    def content_width(self) -> int:
        """Return the maximum line length of the content."""
        return max(fragment_list_width(line) for line in self.rendered_lines)

    def close(self) -> None:
        """Remove the displayed object entirely."""
        if not self.app.leave_graphics():
            self.hide()


class DisplayWindow(Window):
    """A window sub-class which can scroll left and right."""

    content: DisplayControl
    vertical_scroll: int

    def _write_to_screen_at_index(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
    ) -> None:
        """Enure the :attr:`horizontal_scroll` is recorded."""
        super()._write_to_screen_at_index(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
        )
        # Set the horizontal scroll offset on the render info
        # TODO - fix this upstream
        if self.render_info is not None:
            setattr(  # noqa B010
                self.render_info, "horizontal_scroll", self.horizontal_scroll
            )

    def _scroll_right(self) -> None:
        """Scroll window right."""
        info = self.render_info
        if info is None:
            return
        content_width = self.content.content_width
        if self.horizontal_scroll < content_width - info.window_width:
            if info.cursor_position.y <= info.configured_scroll_offsets.right:
                self.content.move_cursor_right()
            self.horizontal_scroll += 1

    def _scroll_left(self) -> None:
        """Scroll window left."""
        info = self.render_info
        if info is None:
            return
        horizontal_scroll = getattr(
            self.render_info, "horizontal_scroll", 0
        )  # noqa B009
        if horizontal_scroll > 0:
            self.content.move_cursor_left()
            self.horizontal_scroll -= 1


class FormattedTextDisplayControl(DisplayControl):
    """A data formatter, which displays cell output data.

    It will attempt to display the data in the best way possible, and reacts to resize
    events - i.e. images are downscaled to fit, markdown is re-flowed, etc.
    """

    def get_rendered_lines(
        self, width: int, height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            lines = list(
                split_lines(
                    to_formatted_text(
                        convert(
                            data=self.data,
                            from_=self.format_,
                            to="ft",
                            cols=width,
                            rows=height,
                            fg=self.fg_color,
                            bg=self.bg_color,
                            path=self.path,
                        )
                    )
                )
            )
            if wrap_lines:
                lines = [
                    wrapped_line
                    for line in lines
                    for wrapped_line in split_lines(
                        wrap(line, width, truncate_long_words=False)
                    )
                ]

            # Ensure we have enough lines to fill the data's calculated height
            rows = ceil(min(width, self.max_cols) * self.aspect)
            lines.extend([[]] * max(0, rows - len(lines)))

            return lines

        # Re-render if the image width changes, or the terminal character size changes
        key = (width, self.app.term_info.cell_size_px, wrap_lines)
        return self._format_cache.get(key, render_lines)


class GraphicControl(DisplayControl, metaclass=ABCMeta):
    """A base-class for display controls which render terminal graphics."""

    def __init__(
        self,
        data: Any,
        format_: str,
        path: Path | None = None,
        fg_color: str | None = None,
        bg_color: str | None = None,
        sizing_func: Callable[[], tuple[int, float]] | None = None,
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        scale: float = 0,
        bbox: DiInt | None = None,
    ) -> None:
        """Initialize the graphic control."""
        super().__init__(
            data,
            format_,
            path,
            fg_color,
            bg_color,
            sizing_func,
            focusable,
            focus_on_click,
        )
        self.bbox = bbox or DiInt(0, 0, 0, 0)

        # Record the original pixel size of the imge
        px, py = data_pixel_size(data, format_, fg=fg_color, bg=bg_color)
        if not px or not py:
            log.warning("Cannot determine image size")
            px, py = px or 100, py or 100
        self.px, self.py = px, py

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate rendered output at a given size.

        Args:
            width: The desired output width
            height: The desired output height

        Returns:
            `UIContent` for the given output size.

        """
        cols = min(self.max_cols, width) if self.max_cols else width
        rows = (
            ceil(cols * self.aspect) - self.bbox.top - self.bbox.bottom
            if self.aspect
            else height
        )

        def get_content() -> dict[str, Any]:
            rendered_lines = self.get_rendered_lines(width=cols, height=rows)
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: int) -> StyleAndTextTuples:
                # Return blank lines if the renderer expects more content than we have
                line = []
                if i < line_count:
                    line += rendered_lines[i]
                # Add a space at the end, because that is a possible cursor position.
                # This is what PTK does, and fixes a nasty bug which took me ages to
                # track down the source of, where scrolling would stop working when the
                # cursor was on an empty line.
                line += [("", " ")]
                return line

            return {
                "get_line": get_line,
                "line_count": line_count,
                "menu_position": Point(0, 0),
            }

        # Re-render if the image width changes, or the terminal character size changes
        key = (cols, rows, self.app.term_info.cell_size_px, self.bbox)
        return UIContent(
            cursor_position=self.cursor_position,
            **self._content_cache.get(key, get_content),
        )


class SixelGraphicControl(GraphicControl):
    """A graphic control which displays images as sixels."""

    def get_rendered_lines(
        self, width: int, height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""
        cell_size_x, cell_size_y = self.app.term_info.cell_size_px

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            full_width = width + self.bbox.left + self.bbox.right
            full_height = height + self.bbox.top + self.bbox.bottom
            cmd = str(
                convert(
                    data=self.data,
                    from_=self.format_,
                    to="sixel",
                    cols=full_width,
                    rows=full_height,
                    fg=self.fg_color,
                    bg=self.bg_color,
                    path=self.path,
                )
            )
            if any(self.bbox):
                from sixelcrop import sixelcrop

                cmd = sixelcrop(
                    data=cmd,
                    # Horizontal pixel offset of the displayed image region
                    x=self.bbox.left * cell_size_x,
                    # Vertical pixel offset of the displayed image region
                    y=self.bbox.top * cell_size_y,
                    # Pixel width of the displayed image region
                    w=width * cell_size_x,
                    # Pixel height of the displayed image region
                    h=height * cell_size_y,
                )

            if get_app().config.tmux_graphics:
                cmd = tmuxify(cmd)

            return list(
                split_lines(
                    to_formatted_text(
                        [
                            # Move cursor down and across by image height and width
                            ("", "\n".join((height) * [" " * (width)])),
                            # Save position, then move back
                            ("[ZeroWidthEscape]", "\x1b[s"),
                            # Move cursor up if there is more than one line to display
                            *(
                                [("[ZeroWidthEscape]", f"\x1b[{height-1}A")]
                                if height > 1
                                else []
                            ),
                            ("[ZeroWidthEscape]", f"\x1b[{width}D"),
                            # Place the image without moving cursor
                            ("[ZeroWidthEscape]", cmd),
                            # Restore the last known cursor position (at the bottom)
                            ("[ZeroWidthEscape]", "\x1b[u"),
                        ]
                    )
                )
            )

        key = (width, self.bbox, (cell_size_x, cell_size_y))
        return self._format_cache.get(key, render_lines)


class ItermGraphicControl(GraphicControl):
    """A graphic control which displays images using iTerm's graphics protocol."""

    def convert_data(self, rows: int, cols: int) -> str:
        """Convert the graphic's data to base64 data."""
        data = self.data
        format_ = self.format_

        full_width = cols + self.bbox.left + self.bbox.right
        full_height = rows + self.bbox.top + self.bbox.bottom

        # Crop image if necessary
        if any(self.bbox):
            import io

            image = convert(
                data=data,
                from_=format_,
                to="pil",
                cols=full_width,
                rows=full_height,
                fg=self.fg_color,
                bg=self.bg_color,
                path=self.path,
            )
            if image is not None:
                cell_size_x, cell_size_y = self.app.term_info.cell_size_px
                # Downscale image to fit target region for precise cropping
                image.thumbnail((full_width * cell_size_x, full_height * cell_size_y))
                image = image.crop(
                    (
                        self.bbox.left * cell_size_x,  # left
                        self.bbox.top * cell_size_y,  # top
                        (self.bbox.left + cols) * cell_size_x,  # right
                        (self.bbox.top + rows) * cell_size_y,  # bottom
                    )
                )
                with io.BytesIO() as output:
                    image.save(output, format="PNG")
                    data = output.getvalue()
                format_ = "png"

        if format_.startswith("base64-"):
            b64data = data
        else:
            b64data = convert(
                data=data,
                from_=format_,
                to="base64-png",
                cols=full_width,
                rows=full_height,
                fg=self.fg_color,
                bg=self.bg_color,
                path=self.path,
            )
        b64data = b64data.replace("\n", "").strip()
        return b64data

    def get_rendered_lines(
        self, width: int, height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            b64data = self.convert_data(cols=width, rows=height)
            cmd = f"\x1b]1337;File=inline=1;width={width}:{b64data}\a"
            return list(
                split_lines(
                    to_formatted_text(
                        [
                            # Move cursor down and across by image height and width
                            ("", "\n".join((height) * [" " * (width)])),
                            # Save position, then move back
                            ("[ZeroWidthEscape]", "\x1b[s"),
                            # Move cursor up if there is more than one line to display
                            *(
                                [("[ZeroWidthEscape]", f"\x1b[{height-1}A")]
                                if height > 1
                                else []
                            ),
                            ("[ZeroWidthEscape]", f"\x1b[{width}D"),
                            # Place the image without moving cursor
                            ("[ZeroWidthEscape]", tmuxify(cmd)),
                            # Restore the last known cursor position (at the bottom)
                            ("[ZeroWidthEscape]", "\x1b[u"),
                        ]
                    )
                )
            )

        key = (width, self.bbox, self.app.term_info.cell_size_px)
        return self._format_cache.get(key, render_lines)


_kitty_image_count = 1


class KittyGraphicControl(GraphicControl):
    """A graphic control which displays images using Kitty's graphics protocol."""

    def __init__(
        self,
        data: Any,
        format_: str,
        path: Path | None = None,
        fg_color: str | None = None,
        bg_color: str | None = None,
        sizing_func: Callable[[], tuple[int, float]] | None = None,
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        scale: float = 0,
        bbox: DiInt | None = None,
    ) -> None:
        """Create a new kitty graphic instance."""
        super().__init__(
            data=data,
            format_=format_,
            path=path,
            fg_color=fg_color,
            bg_color=bg_color,
            sizing_func=sizing_func,
            focusable=focusable,
            focus_on_click=focus_on_click,
            scale=scale,
            bbox=bbox,
        )
        self.kitty_image_id = 0
        self.loaded = False

    def convert_data(self, rows: int, cols: int) -> str:
        """Convert the graphic's data to base64 data for kitty graphics protocol."""
        return str(
            convert(
                self.data,
                from_=self.format_,
                to="base64-png",
                cols=cols,
                rows=rows,
                fg=self.fg_color,
                bg=self.bg_color,
                path=self.path,
            )
        ).replace("\n", "")

    @staticmethod
    def _kitty_cmd(chunk: str = "", **params: Any) -> str:
        param_str = ",".join(
            [f"{key}={value}" for key, value in params.items() if value is not None]
        )
        cmd = f"\x1b_G{param_str}"
        if chunk:
            cmd += f";{chunk}"
        cmd += "\x1b\\"
        return cmd

    def load(self, rows: int, cols: int) -> None:
        """Send the graphic to the terminal without displaying it."""
        global _kitty_image_count

        data = self.convert_data(rows=rows, cols=cols)
        self.kitty_image_id = _kitty_image_count
        _kitty_image_count += 1

        while data:
            chunk, data = data[:4096], data[4096:]
            cmd = self._kitty_cmd(
                chunk=chunk,
                a="t",  # We are sending an image without displaying it
                t="d",  # Transferring the image directly
                i=self.kitty_image_id,  # Send a unique image number, wait for an image id
                # I=self.kitty_image_number,  # Send a unique image number, wait for an image id
                p=1,  # Placement ID
                q=2,  # No chatback
                f=100,  # Sending a PNG image
                C=1,  # Do not move the cursor
                m=1 if data else 0,  # Data will be chunked
            )
            self.app.output.write_raw(tmuxify(cmd))
        self.app.output.flush()
        self.loaded = True

    def hide(self) -> None:
        """Hide the graphic from show without deleting it."""
        if self.kitty_image_id > 0:
            self.app.output.write_raw(
                tmuxify(
                    self._kitty_cmd(
                        a="d",
                        d="i",
                        i=self.kitty_image_id,
                        q=1,
                    )
                )
            )
            self.app.output.flush()

    def delete(self) -> None:
        """Delete the graphic from the terminal."""
        if self.kitty_image_id > 0:
            self.app.output.write_raw(
                tmuxify(
                    self._kitty_cmd(
                        a="D",
                        d="I",
                        i=self.kitty_image_id,
                        q=2,
                    )
                )
            )
            self.app.output.flush()
            self.loaded = False

    def get_rendered_lines(
        self, width: int, height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""
        # TODO - wezterm does not scale kitty graphics, so we might want to resize
        # images at this point rather than just loading them once
        if not self.loaded:
            self.load(cols=width, rows=height)

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            full_width = width + self.bbox.left + self.bbox.right
            full_height = height + self.bbox.top + self.bbox.bottom
            cmd = self._kitty_cmd(
                a="p",  # Display a previously transmitted image
                i=self.kitty_image_id,
                p=1,  # Placement ID
                m=0,  # No batches remaining
                q=2,  # No backchat
                c=width,
                r=height,
                C=1,  # 1 = Do move the cursor
                # Horizontal pixel offset of the displayed image region
                x=int(self.px * self.bbox.left / full_width),
                # Vertical pixel offset of the displayed image region
                y=int(self.py * self.bbox.top / full_height),
                # Pixel width of the displayed image region
                w=int(self.px * width / full_width),
                # Pixel height of the displayed image region
                h=int(self.py * height / full_height),
                z=-(2**30) - 1,
            )
            return list(
                split_lines(
                    to_formatted_text(
                        [
                            # Move cursor down and acoss by image height and width
                            ("", "\n".join((height) * [" " * (width)])),
                            # Save position, then move back
                            ("[ZeroWidthEscape]", "\x1b[s"),
                            # Move cursor up if there is more than one line to display
                            *(
                                [("[ZeroWidthEscape]", f"\x1b[{height-1}A")]
                                if height > 1
                                else []
                            ),
                            ("[ZeroWidthEscape]", f"\x1b[{width}D"),
                            # Place the image without moving cursor
                            ("[ZeroWidthEscape]", tmuxify(cmd)),
                            # Restore the last known cursor position (at the bottom)
                            ("[ZeroWidthEscape]", "\x1b[u"),
                        ]
                    )
                )
            )

        key = (width, height, self.bbox, self.app.term_info.cell_size_px)
        return self._format_cache.get(key, render_lines)

    def reset(self) -> None:
        """Hide and delete the kitty graphic from the terminal."""
        self.hide()
        self.delete()
        super().reset()

    def close(self) -> None:
        """Remove the displayed object entirely."""
        super().close()
        if not self.app.leave_graphics():
            self.delete()


class NotVisible(Exception):
    """Exception to signal that a graphic is not currently visible."""

    pass


def get_position_func_overlay(
    target_window: Window,
) -> Callable[[Screen], tuple[WritePosition, DiInt]]:
    """Generate function to positioning floats over existing windows."""

    def get_position(screen: Screen) -> tuple[WritePosition, DiInt]:
        target_wp = screen.visible_windows_to_write_positions.get(target_window)
        if target_wp is None:
            raise NotVisible

        render_info = target_window.render_info
        if render_info is None:
            raise NotVisible

        xpos = target_wp.xpos
        ypos = target_wp.ypos

        content_height = render_info.ui_content.line_count
        content_width = target_wp.width  # TODO - get the actual content width

        # Calculate the cropping box in case the window is scrolled
        bbox = DiInt(
            top=render_info.vertical_scroll,
            right=max(
                0,
                content_height
                - target_wp.width
                - getattr(render_info, "horizontal_scroll", 0),
            ),
            bottom=max(
                0,
                content_height - target_wp.height - render_info.vertical_scroll,
            ),
            left=getattr(render_info, "horizontal_scroll", 0),
        )

        # If the target is within a scrolling container, we might need to adjust
        # the position of the cropped region so the float covers only the visible
        # part of the target window
        if isinstance(target_wp, BoundedWritePosition):
            bbox = bbox._replace(
                top=bbox.top + target_wp.bbox.top,
                right=bbox.right + target_wp.bbox.right,
                bottom=bbox.bottom + target_wp.bbox.bottom,
                left=bbox.left + target_wp.bbox.left,
            )
            xpos += bbox.left
            ypos += bbox.top
            content_height -= bbox.top + bbox.bottom
            content_width -= bbox.left + bbox.right

        new_write_position = WritePosition(
            xpos=xpos,
            ypos=ypos,
            width=max(0, content_width),
            height=max(0, content_height),
        )

        return new_write_position, bbox

    return get_position


class GraphicWindow(Window):
    """A window responsible for displaying terminal graphics content.

    The content is displayed floating on top of a target window.

    The graphic will be displayed if:
    - a completion menu is not being shown
    - a dialog is not being shown
    - a menu is not being shown
    - the output it attached to is fully in view
    """

    content: GraphicControl

    def __init__(
        self,
        content: GraphicControl,
        position: Callable[[Screen], tuple[WritePosition, DiInt]],
        filter: FilterOrBool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initiate a new :py:class:`GraphicWindow` object.

        Args:
            content: A control which generates the graphical content to display
            position: A function which returns the position of the graphic
            filter: A filter which determines if the graphic should be shown
            args: Positional arguments for :py:method:`Window.__init__`
            kwargs: Key-word arguments for :py:method:`Window.__init__`
        """
        super().__init__(*args, **kwargs)
        self.content = content
        self.position = position
        self.filter = ~has_completions & ~has_dialog & ~has_menus & to_filter(filter)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw the graphic window's contents to the screen if required."""
        filter_value = self.filter()
        if filter_value:
            try:
                new_write_position, bbox = self.position(screen)
            except NotVisible:
                pass
            else:
                # Inform the graphic control of the calculated cropping region
                self.content.bbox = bbox

                # Draw the graphic content to the screen
                if (
                    new_write_position
                    and new_write_position.width
                    and new_write_position.height
                ):
                    super().write_to_screen(
                        screen,
                        MouseHandlers(),  # Do not let the float add mouse events
                        new_write_position,
                        # Force renderer refreshes by constantly changing the style
                        f"{parent_style} class:render-{get_app().render_counter}",
                        erase_bg=True,
                        z_index=z_index,
                    )
                    return

        # Otherwise hide the content (required for kitty graphics)
        if not filter_value or not get_app().leave_graphics():
            self.content.hide()

    def _fill_bg(
        self,
        screen: Screen,
        # mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        erase_bg: bool,
    ) -> None:
        """Erase/fill the background."""
        char: str | None
        if callable(self.char):
            char = self.char()
        else:
            char = self.char
        if erase_bg or char:
            wp = write_position
            char_obj = Char(char or " ", f"class:render-{get_app().render_counter}")

            # mouse_handlers_dict = mouse_handlers.mouse_handlers
            for y in range(wp.ypos, wp.ypos + wp.height):
                row = screen.data_buffer[y]
                # mouse_handler_row = mouse_handlers_dict[y]
                for x in range(wp.xpos, wp.xpos + wp.width):
                    row[x] = char_obj
                    # mouse_handler_row[x] = lambda e: NotImplemented


def select_graphic_control(format_: str) -> type[GraphicControl] | None:
    """Determine which graphic control to use."""
    SelectedGraphicControl: type[GraphicControl] | None = None
    app = get_app()
    term_info = app.term_info
    preferred_graphics_protocol = app.config.graphics
    useable_graphics_controls: list[type[GraphicControl]] = []
    _in_tmux = in_tmux()

    if preferred_graphics_protocol != "none":
        if term_info.iterm_graphics_status.value and find_route(format_, "base64-png"):
            useable_graphics_controls.append(ItermGraphicControl)
        if (
            preferred_graphics_protocol == "iterm"
            and ItermGraphicControl in useable_graphics_controls
            # Iterm does not work in tmux without pass-through
            and (not _in_tmux or (_in_tmux and app.config.tmux_graphics))
        ):
            SelectedGraphicControl = ItermGraphicControl
        elif (
            term_info.kitty_graphics_status.value
            and find_route(format_, "base64-png")
            # Kitty does not work in tmux without pass-through
            and (not _in_tmux or (_in_tmux and app.config.tmux_graphics))
        ):
            useable_graphics_controls.append(KittyGraphicControl)
        if (
            preferred_graphics_protocol == "kitty"
            and KittyGraphicControl in useable_graphics_controls
        ):
            SelectedGraphicControl = KittyGraphicControl
        # Tmux now supports sixels (>=3.4)
        elif term_info.sixel_graphics_status.value and find_route(format_, "sixel"):
            useable_graphics_controls.append(SixelGraphicControl)
        if (
            preferred_graphics_protocol == "sixel"
            and SixelGraphicControl in useable_graphics_controls
        ):
            SelectedGraphicControl = SixelGraphicControl

        if SelectedGraphicControl is None and useable_graphics_controls:
            SelectedGraphicControl = useable_graphics_controls[0]

    return SelectedGraphicControl


class Display:
    """Rich output displays.

    A container for displaying rich output data.

    """

    def __init__(
        self,
        data: Any,
        format_: str,
        path: Path | None = None,
        fg_color: str | None = None,
        bg_color: str | None = None,
        height: AnyDimension = None,
        width: AnyDimension = None,
        px: int | None = None,
        py: int | None = None,
        focusable: FilterOrBool = False,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        always_hide_cursor: FilterOrBool = True,
        scrollbar: FilterOrBool = True,
        scrollbar_autohide: FilterOrBool = True,
        dont_extend_height: FilterOrBool = True,
        style: str | Callable[[], str] = "",
    ) -> None:
        """Instantiate an Output container object.

        Args:
            data: Raw cell output data
            format_: The conversion format of the data to render
            path: The path to the data's original location
            fg_color: The foreground colour to use when renderin this output
            bg_color: The background colour to use when renderin this output
            height: The height of the output
            width: The width of the output
            px: The pixel width of the data if known
            py: The pixel height of the data if known
            focusable: If the output should be focusable
            focus_on_click: If the output should become focused when clicked
            wrap_lines: If the output's lines should be wrapped
            always_hide_cursor: When true, the cursor is never shown
            scrollbar: Whether to show a scrollbar
            scrollbar_autohide: Whether to automatically hide the scrollbar
            dont_extend_height: Whether the window should fill the available height
            style: The style to apply to the output

        """
        self._style = style
        self.fg_color = fg_color
        self.bg_color = bg_color

        # Get data pixel dimensions
        self._px = px
        self._py = py

        sizing_func = self.make_sizing_func(
            data=data,
            format_=format_,
            fg=fg_color,
            bg=bg_color,
        )

        self.control = FormattedTextDisplayControl(
            data,
            format_=format_,
            path=path,
            fg_color=fg_color,
            bg_color=bg_color,
            sizing_func=sizing_func,
            focusable=focusable,
            focus_on_click=focus_on_click,
            wrap_lines=wrap_lines,
        )

        self.window = DisplayWindow(
            content=self.control,
            height=height,
            width=width,
            wrap_lines=False,
            always_hide_cursor=always_hide_cursor,
            dont_extend_height=dont_extend_height,
            style=self.style,
            char=" ",
        )

        self.container = VSplit(
            [
                self.window,
                ConditionalContainer(
                    MarginContainer(ScrollbarMargin(), target=self.window),
                    filter=to_filter(scrollbar)
                    & (
                        ~to_filter(scrollbar_autohide)
                        | (to_filter(scrollbar_autohide) & scrollable(self.window))
                    ),
                ),
            ]
        )

        # Add graphic
        self.graphic_control = None
        if SelectedGraphicControl := select_graphic_control(format_):
            self.graphic_control = SelectedGraphicControl(
                data,
                format_=format_,
                path=path,
                fg_color=fg_color,
                bg_color=bg_color,
                sizing_func=sizing_func,
            )
            graphic_window = GraphicWindow(
                content=self.graphic_control,
                position=get_position_func_overlay(self.window),
                style=self.style,
            )

            # The only reference to the float is saved on the Display widget
            self.graphic_float = Float(content=graphic_window)
            # Hide the graphic if not in the app's list of graphics
            weak_float_ref = weakref.ref(self.graphic_float)
            graphic_window.filter &= Condition(
                lambda: weak_float_ref() in get_app().graphics
            )
            # Hide the graphic if the float is deleted
            weakref.finalize(self.graphic_float, self.graphic_control.close)
            # Add graphic to app
            get_app().graphics.add(self.graphic_float)

    def style(self) -> str:
        """Use the background color of the data as the default style."""
        style = to_str(self._style)
        if self.bg_color:
            style = f"bg:{self.bg_color} {style}"
        return style

    @property
    def data(self) -> Any:
        """Return the display's current data."""
        return self.control.data

    @data.setter
    def data(self, value: Any) -> None:
        """Set the display container's data."""
        self.control.data = value
        if self.graphic_control is not None:
            self.graphic_control.data = value

    @property
    def format_(self) -> str:
        """Return the display's current data format."""
        return self.control.format_

    @format_.setter
    def format_(self, value: str) -> None:
        """Set the display container's data format."""
        self.control.format_ = value
        if self.graphic_control is not None:
            self.graphic_control.format_ = value

    @property
    def path(self) -> Path | None:
        """Return the display's current data path."""
        return self.control.path

    @path.setter
    def path(self, value: Path | None) -> None:
        """Set the display container's data path."""
        self.control.path = value
        if self.graphic_control is not None:
            self.graphic_control.path = value

    def make_sizing_func(
        self, data: Any, format_: str, fg: str | None, bg: str | None
    ) -> Callable[[], tuple[int, float]]:
        """Create a function to recalculate the data's dimensions in terminal cells."""
        px, py = self.px, self.py
        if px is None or py is None:
            px, py = data_pixel_size(data, format_, fg=fg, bg=bg)
        return partial(pixels_to_cell_size, px, py)

    @property
    def px(self) -> int | None:
        """Return the displayed data's pixel widget."""
        return self._px

    @px.setter
    def px(self, value: int | None) -> None:
        """Set the display container's width in pixels."""
        self._px = value
        self.update_sizing()

    @property
    def py(self) -> int | None:
        """Return the displayed data's pixel height."""
        return self._py

    @py.setter
    def py(self, value: int | None) -> None:
        """Set the display container's height in pixels."""
        self._py = value
        self.update_sizing()

    def update_sizing(self) -> None:
        """Create a sizing function when the data's pixel size changes."""
        sizing_func = self.make_sizing_func(
            data=self.control.data,
            format_=self.control.format_,
            fg=self.control.fg_color,
            bg=self.control.bg_color,
        )
        self.control.sizing_func = sizing_func
        self.control.reset()
        if self.graphic_control is not None:
            self.graphic_control.sizing_func = sizing_func
            self.graphic_control.reset()

    def __pt_container__(self) -> AnyContainer:
        """Return the content of this output."""
        return self.container

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_left() -> None:
        """Scroll the display up one line."""
        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_left()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_right() -> None:
        """Scroll the display down one line."""
        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_right()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_up() -> None:
        """Scroll the display up one line."""
        get_app().layout.current_window._scroll_up()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_down() -> None:
        """Scroll the display down one line."""
        get_app().layout.current_window._scroll_down()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _page_up_display() -> None:
        """Scroll the display up one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_up()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _page_down_display() -> None:
        """Scroll the display down one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_down()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _go_to_start_of_display() -> None:
        """Scroll the display to the top."""
        from euporie.core.widgets.display import DisplayControl

        current_control = get_app().layout.current_control
        if isinstance(current_control, DisplayControl):
            current_control.cursor_position = Point(0, 0)

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _go_to_end_of_display() -> None:
        """Scroll the display down one page."""
        from euporie.core.widgets.display import DisplayControl

        layout = get_app().layout
        current_control = layout.current_control
        window = layout.current_window
        if (
            isinstance(current_control, DisplayControl)
            and window.render_info is not None
        ):
            current_control.cursor_position = Point(
                0, window.render_info.ui_content.line_count - 1
            )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.widgets.display.Display": {
                "scroll-display-left": "left",
                "scroll-display-right": "right",
                "scroll-display-up": ["up", "k"],
                "scroll-display-down": ["down", "j"],
                "page-up-display": "pageup",
                "page-down-display": "pagedown",
                "go-to-start-of-display": "home",
                "go-to-end-of-display": "end",
            }
        }
    )
