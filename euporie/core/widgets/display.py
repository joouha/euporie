"""Defines custom controls which re-render on resize."""

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
from prompt_toolkit.layout.containers import Float, Window
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, WritePosition
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event

from euporie.core.commands import add_cmd
from euporie.core.convert.base import convert, find_route
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
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.margins import ScrollbarMargin
from euporie.core.terminal import tmuxify
from euporie.core.widgets.page import BoundedWritePosition

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable, Type, Union

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer, WindowRenderInfo
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.layout.screen import Screen
    from upath import UPath


log = logging.getLogger(__name__)


class DisplayControl(UIControl):
    """A data formatter, which displays cell output data.

    It will attempt to display the data in the best way possible, and reacts to resize
    events - i.e. images are downscaled to fit, markdown is re-flowed, etc.
    """

    def __init__(
        self,
        data: "Any",
        format_: "str",
        path: "UPath|None" = None,
        fg_color: "str|None" = None,
        bg_color: "str|None" = None,
        sizing_func: "Callable[[], tuple[int, float]]|None" = None,
        focusable: "FilterOrBool" = False,
        focus_on_click: "FilterOrBool" = False,
    ) -> "None":
        """Creates a new data formatter control.

        Args:
            data: Raw cell output data
            format_: The conversion format of the data to render
            path: The path to the data's original location
            fg_color: The foreground colour to use when renderin this output
            bg_color: The background colour to use when renderin this output
            sizing_func: Function which returns the maximum width and aspect ratio of
                the output
            focusable: Whether the control can be focused
            focus_on_click: Whether to focus the control when clicked

        """
        self._data = data
        self.format_ = format_
        self.path = path
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.focusable = to_filter(focusable)
        self.focus_on_click = to_filter(focus_on_click)
        self.key_bindings = load_registered_bindings(
            "euporie.core.widgets.display.Display"
        )
        self.app = get_app()

        self.on_cursor_position_changed = Event(self)
        self._cursor_position = Point(x=0, y=0)
        self.dy = 0

        self.sizing_func = sizing_func or (lambda: (0, 0))
        self._max_cols = 0
        self._aspect = 0.0

        self.rendered_lines: "list[StyleAndTextTuples]" = []
        self._format_cache: SimpleCache = SimpleCache(maxsize=50)
        self._content_cache: SimpleCache = SimpleCache(maxsize=50)
        self._size_cache: SimpleCache = SimpleCache(maxsize=1)

    def reset(self) -> "None":
        """Clear the display control's caches (required if the control's data changes)."""
        self._format_cache.clear()
        self._size_cache.clear()
        self._content_cache.clear()

    @property
    def data(self) -> "Any":
        """Return the control's display data."""
        return self._data

    @data.setter
    def data(self, value: "Any") -> "None":
        """Set the control's data."""
        self._data = value
        self.reset()

    def get_key_bindings(self) -> "KeyBindingsBase|None":
        """Return the control's key bindings."""
        return self.key_bindings

    @property
    def cursor_position(self) -> "Point":
        """Get the cursor position."""
        return self._cursor_position

    @cursor_position.setter
    def cursor_position(self, value: "Point") -> "None":
        """Set the cursor position."""
        changed = self._cursor_position != value
        self._cursor_position = value
        if changed:
            self.on_cursor_position_changed.fire()

    def move_cursor_down(self) -> "None":
        """Moves the cursor down one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x, y=y + 1)

    def move_cursor_up(self) -> "None":
        """Moves the cursor up one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x, y=max(0, y - 1))

    def move_cursor_left(self) -> "None":
        """Moves the cursor down one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=max(0, x - 1), y=y)

    def move_cursor_right(self) -> "None":
        """Moves the cursor up one line."""
        x, y = self.cursor_position
        self.cursor_position = Point(x=x + 1, y=y)

    def is_focusable(self) -> "bool":
        """Determines if the current control is focusable."""
        return self.focusable()

    def size(self) -> "None":
        """Load the maximum cell width and aspect ratio of the output."""
        self._max_cols, self._aspect = self._size_cache.get(
            self.app.render_counter, self.sizing_func
        )

    def hide(self) -> "None":
        """Hides the output from show."""
        pass

    @property
    def max_cols(self) -> "int":
        """Load the maximum width of the output in terminal columns."""
        self.size()
        return self._max_cols

    @property
    def aspect(self) -> "float":
        """Lazily load the aspect ratio of the output."""
        self.size()
        return self._aspect

    def preferred_width(self, max_available_width: "int") -> "int|None":
        """Returns the width of the rendered content."""
        self.max_available_width = max_available_width
        return (
            min(self.max_cols, max_available_width)
            if self.max_cols
            else max_available_width
        )

    def get_rendered_lines(
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Render the output data."""
        return []

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> "int":
        """Returns the number of lines in the rendered content."""
        if self.aspect:
            return ceil(min(width, self.max_cols) * self.aspect)
        else:
            self.rendered_lines = self.get_rendered_lines(width, max_available_height)
            return len(self.rendered_lines)

    def create_content(self, width: "int", height: "int") -> "UIContent":
        """Generates rendered output at a given size.

        Args:
            width: The desired output width
            height: The desired output height

        Returns:
            `UIContent` for the given output size.

        """
        cols = min(self.max_cols, width) if self.max_cols else width
        rows = ceil(cols * self.aspect) if self.aspect else height

        def get_content() -> "dict[str, Any]":
            rendered_lines = self.get_rendered_lines(width=cols, height=rows)
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: "int") -> "StyleAndTextTuples":
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
        key = (cols, self.app.term_info.cell_size_px)
        return UIContent(
            cursor_position=self.cursor_position,
            **self._content_cache.get(key, get_content),
        )

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        """Mouse handler for this control."""
        if self.focus_on_click() and mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.app.layout.current_control = self
            return None
        return NotImplemented

    def get_invalidate_events(self) -> "Iterable[Event[object]]":
        """Return the Window invalidate events."""
        # Whenever the cursor position changes, the UI has to be updated.
        yield self.on_cursor_position_changed

    @property
    def content_width(self) -> "int":
        """Return the maximum line length of the content."""
        return max(fragment_list_width(line) for line in self.rendered_lines)

    def close(self) -> "None":
        """Remove the displayed object entirely."""
        if not self.app.leave_graphics():
            self.hide()


class DisplayWindow(Window):
    """A window sub-class which can scroll left and right."""

    content: "DisplayControl"
    render_info: "WindowRenderInfo"
    vertical_scroll: "int"

    def _write_to_screen_at_index(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
    ) -> None:
        """Ensure the :attr:`horizontal_scroll` is recorded."""
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
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
            return list(
                split_lines(
                    convert(
                        data=self.data,
                        from_=self.format_,
                        to="formatted_text",
                        cols=width,
                        rows=height,
                        fg=self.fg_color,
                        bg=self.bg_color,
                        path=self.path,
                    )
                )
            )

        # Re-render if the image width changes, or the terminal character size changes
        key = (width, self.app.term_info.cell_size_px)
        return self._format_cache.get(key, render_lines)


class GraphicControl(DisplayControl, metaclass=ABCMeta):
    """A base-class for display controls which render terminal graphics."""

    def __init__(
        self,
        data: "Any",
        format_: "str",
        path: "UPath|None" = None,
        fg_color: "str|None" = None,
        bg_color: "str|None" = None,
        sizing_func: "Callable[[], tuple[int, float]]|None" = None,
        focusable: "FilterOrBool" = False,
        focus_on_click: "FilterOrBool" = False,
        scale: "float" = 0,
        bbox: "DiInt|None" = None,
    ) -> "None":
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

    def create_content(self, width: "int", height: "int") -> "UIContent":
        """Generates rendered output at a given size.

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

        def get_content() -> "dict[str, Any]":
            rendered_lines = self.get_rendered_lines(width=cols, height=rows)
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: "int") -> "StyleAndTextTuples":
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
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""
        cell_size_x, cell_size_y = self.app.term_info.cell_size_px

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
            full_width = width + self.bbox.left + self.bbox.right
            full_height = height + self.bbox.top + self.bbox.bottom
            cmd = convert(
                data=self.data,
                from_=self.format_,
                to="sixel",
                cols=full_width,
                rows=full_height,
                fg=self.fg_color,
                bg=self.bg_color,
                path=self.path,
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

        key = (width, self.bbox, (cell_size_x, cell_size_y))
        return self._format_cache.get(key, render_lines)


class ItermGraphicControl(GraphicControl):
    """A graphic control which displays images using iTerm's graphics protocol."""

    def convert_data(self, rows: "int", cols: "int") -> "str":
        """Converts the graphic's data to base64 data."""
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
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
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
        data: "Any",
        format_: "str",
        path: "UPath|None" = None,
        fg_color: "str|None" = None,
        bg_color: "str|None" = None,
        sizing_func: "Callable[[], tuple[int, float]]|None" = None,
        focusable: "FilterOrBool" = False,
        focus_on_click: "FilterOrBool" = False,
        scale: "float" = 0,
        bbox: "DiInt|None" = None,
    ) -> "None":
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

    def convert_data(self, rows: "int", cols: "int") -> "str":
        """Converts the graphic's data to base64 data for kitty graphics protocol."""
        return convert(
            self.data,
            from_=self.format_,
            to="base64-png",
            cols=cols,
            rows=rows,
            fg=self.fg_color,
            bg=self.bg_color,
            path=self.path,
        ).replace("\n", "")

    @staticmethod
    def _kitty_cmd(chunk: "str" = "", **params: "Any") -> "str":
        param_str = ",".join(
            [f"{key}={value}" for key, value in params.items() if value is not None]
        )
        cmd = f"\x1b_G{param_str}"
        if chunk:
            cmd += f";{chunk}"
        cmd += "\x1b\\"
        return cmd

    def load(self, rows: "int", cols: "int") -> "None":
        """Sends the graphic to the terminal without displaying it."""
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

    def hide(self) -> "None":
        """Hides the graphic from show without deleting it."""
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

    def delete(self) -> "None":
        """Deletes the graphic from the terminal."""
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
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""
        # TODO - wezterm does not scale kitty graphics, so we might want to resize
        # images at this point rather than just loading them once
        if not self.loaded:
            self.load(cols=width, rows=height)

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
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

    def reset(self) -> "None":
        """Hide and delete the kitty graphic from the terminal."""
        self.hide()
        self.delete()
        super().reset()

    def close(self) -> "None":
        """Remove the displayed object entirely."""
        super().close()
        if not self.app.leave_graphics():
            self.delete()


class GraphicWindow(Window):
    """A window responsible for displaying terminal graphics content.

    The content is displays floating on top of a target window.

    The graphic will be displayed if:
    - a completion menu is not being shown
    - a dialog is not being shown
    - a menu is not being shown
    - the output it attached to is fully in view
    """

    content: "GraphicControl"

    def __init__(
        self,
        content: "GraphicControl",
        target_window: "Window",
        filter: "FilterOrBool",
        *args: "Any",
        **kwargs: "Any",
    ) -> "None":
        """Initiates a new :py:class:`GraphicWindow` object.

        Args:
            content: A control which generates the graphical content to display
            target_window: The window this graphic should position itself over
            filter: A filter which determines if the graphic should be shown
            args: Positional arguments for :py:method:`Window.__init__`
            kwargs: Key-word arguments for :py:method:`Window.__init__`
        """
        super().__init__(*args, **kwargs)
        self.target_window = target_window
        self.content = content
        self.filter = to_filter(filter)

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "int|None",
    ) -> "None":
        """Draws the graphic window's contents to the screen if required."""
        filter_value = self.filter()
        target_wp = screen.visible_windows_to_write_positions.get(self.target_window)
        if (
            filter_value
            and target_wp
            and (render_info := self.target_window.render_info) is not None
        ):

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

            # Inform the graphic control of the calculated cropping region
            self.content.bbox = bbox

            if content_height and content_width:
                # Adjust the write position of the output
                new_write_position = WritePosition(
                    xpos=xpos,
                    ypos=ypos,
                    width=max(0, content_width),
                    height=max(0, content_height),
                )

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
        self, screen: Screen, write_position: WritePosition, erase_bg: bool
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
            for y in range(wp.ypos, wp.ypos + wp.height):
                row = screen.data_buffer[y]
                for x in range(wp.xpos, wp.xpos + wp.width):
                    row[x] = char_obj


class GraphicFloat(Float):
    """A :py:class:`Float` which displays a graphic."""

    def __init__(
        self,
        target_window: "Window",
        data: "Any",
        format_: "str",
        path: "UPath|None" = None,
        fg_color: "str|None" = None,
        bg_color: "str|None" = None,
        sizing_func: "Callable[[], tuple[int, float]]|None" = None,
        filter: "FilterOrBool" = True,
    ) -> "None":
        """Create a new instance.

        Args:
            data: The graphical data to be displayed
            format_: The format of the graphical data
            path: The path to the data's original location
            target_window: The window above which the graphic should be displayed
            fg_color: The graphic's foreground color
            bg_color: The graphic's background color
            sizing_func: A callable which returns in the graphic's width in terminal
                cells and its aspect ratio
            filter: A filter which is used to hide and show the graphic
        """
        self.GraphicControl: "Type[GraphicControl]|None" = None
        self.control = None

        app = get_app()
        term_info = app.term_info
        preferred_graphics_protocol = app.config.graphics
        useable_graphics_controls: "list[Type[GraphicControl]]" = []
        _in_tmux = in_tmux()

        if (
            not _in_tmux or (_in_tmux and app.config.tmux_graphics)
        ) and preferred_graphics_protocol != "none":
            if term_info.iterm_graphics_status.value and find_route(
                format_, "base64-png"
            ):
                useable_graphics_controls.append(ItermGraphicControl)
            if (
                preferred_graphics_protocol == "iterm"
                and ItermGraphicControl in useable_graphics_controls
            ):
                self.GraphicControl = ItermGraphicControl
            elif term_info.kitty_graphics_status.value and find_route(
                format_, "base64-png"
            ):
                useable_graphics_controls.append(KittyGraphicControl)
            if (
                preferred_graphics_protocol == "kitty"
                and KittyGraphicControl in useable_graphics_controls
            ):
                self.GraphicControl = KittyGraphicControl
            elif term_info.sixel_graphics_status.value and find_route(format_, "sixel"):
                useable_graphics_controls.append(SixelGraphicControl)
            if (
                preferred_graphics_protocol == "sixel"
                and SixelGraphicControl in useable_graphics_controls
            ):
                self.GraphicControl = SixelGraphicControl

            if self.GraphicControl is None and useable_graphics_controls:
                self.GraphicControl = useable_graphics_controls[0]

        if self.GraphicControl:
            self.control = self.GraphicControl(
                data,
                format_=format_,
                path=path,
                fg_color=fg_color,
                bg_color=bg_color,
                sizing_func=sizing_func,
            )
            weak_self_ref = weakref.ref(self)
            super().__init__(
                content=GraphicWindow(
                    content=self.control,
                    target_window=target_window,
                    filter=to_filter(filter)
                    & (Condition(lambda: weak_self_ref() in get_app().graphics)),
                ),
                left=0,
                top=0,
            )
            # Hide the graphic if the float is deleted
            weakref.finalize(self, self.control.close)

    @property
    def data(self) -> "Any":
        """Return the graphic's current data."""
        return self._data

    @data.setter
    def data(self, value: "Any") -> "None":
        """Set the graphic float's data."""
        self._data = value
        if self.control is not None:
            self.control.data = value
            self.control.reset()


class Display:
    """Rich output displays.

    A container for displaying rich output data.

    """

    def __init__(
        self,
        data: "Any",
        format_: "str",
        path: "UPath|None" = None,
        fg_color: "str|None" = None,
        bg_color: "str|None" = None,
        height: "AnyDimension" = None,
        width: "AnyDimension" = None,
        px: "int|None" = None,
        py: "int|None" = None,
        focusable: "FilterOrBool" = False,
        focus_on_click: "FilterOrBool" = False,
        wrap_lines: "FilterOrBool" = False,
        always_hide_cursor: "FilterOrBool" = True,
        scrollbar: "FilterOrBool" = True,
        scrollbar_autohide: "FilterOrBool" = True,
        dont_extend_height: "FilterOrBool" = True,
        style: "Union[str, Callable[[], str]]" = "",
    ) -> "None":
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
        self.style = style

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
        )

        self.window = DisplayWindow(
            content=self.control,
            height=height,
            width=width,
            wrap_lines=wrap_lines,
            always_hide_cursor=always_hide_cursor,
            dont_extend_height=dont_extend_height,
            style=self.style,
            char=" ",
        )

        self.window.right_margins = [
            ConditionalMargin(
                ScrollbarMargin(),
                filter=to_filter(scrollbar)
                & (
                    ~to_filter(scrollbar_autohide)
                    | (to_filter(scrollbar_autohide) & scrollable(self.window))
                ),
            )
        ]

        # Add graphic
        app = get_app()
        self.graphic_float = GraphicFloat(
            target_window=self.window,
            data=data,
            format_=format_,
            path=path,
            fg_color=fg_color,
            bg_color=bg_color,
            sizing_func=sizing_func,
            filter=~has_completions & ~has_dialog & ~has_menus,
        )
        if self.graphic_float.GraphicControl is not None:
            app.graphics.add(self.graphic_float)

    @property
    def data(self) -> "Any":
        """Return the display's current data."""
        return self.control.data

    @data.setter
    def data(self, value: "Any") -> "None":
        """Set the display container's data."""
        self.control.data = value
        self.graphic_float.data = value

    def make_sizing_func(
        self, data: "Any", format_: "str", fg: "str|None", bg: "str|None"
    ) -> "Callable[[], tuple[int, float]]":
        """Create a function to recalculate the data's dimensions in terminal cells."""
        px, py = self.px, self.py
        if px is None or py is None:
            px, py = data_pixel_size(data, format_, fg=fg, bg=bg)
        return partial(pixels_to_cell_size, px, py)

    @property
    def px(self) -> "int|None":
        """Return the displayed data's pixel widget."""
        return self._px

    @px.setter
    def px(self, value: "int|None") -> "None":
        """Set the display container's width in pixels."""
        self._px = value
        self.update_sizing()

    @property
    def py(self) -> "int|None":
        """Return the displayed data's pixel height."""
        return self._py

    @py.setter
    def py(self, value: "int|None") -> "None":
        """Set the display container's height in pixels."""
        self._py = value
        self.update_sizing()

    def update_sizing(self) -> "None":
        """Create a sizing function when the data's pixel size changes."""
        sizing_func = self.make_sizing_func(
            data=self.control.data,
            format_=self.control.format_,
            fg=self.control.fg_color,
            bg=self.control.bg_color,
        )
        self.control.sizing_func = sizing_func
        self.control.reset()
        if self.graphic_float.control is not None:
            self.graphic_float.control.sizing_func = sizing_func
            self.graphic_float.control.reset()

    def __pt_container__(self) -> "AnyContainer":
        """Return the content of this output."""
        return self.window

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_left() -> "None":
        """Scroll the display up one line."""
        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_left()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_right() -> "None":
        """Scroll the display down one line."""
        window = get_app().layout.current_window
        assert isinstance(window, DisplayWindow)
        window._scroll_right()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_up() -> "None":
        """Scroll the display up one line."""
        get_app().layout.current_window._scroll_up()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _scroll_display_down() -> "None":
        """Scroll the display down one line."""
        get_app().layout.current_window._scroll_down()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _page_up_display() -> "None":
        """Scroll the display up one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_up()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _page_down_display() -> "None":
        """Scroll the display down one page."""
        window = get_app().layout.current_window
        if window.render_info is not None:
            for _ in range(window.render_info.window_height):
                window._scroll_down()

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _go_to_start_of_display() -> "None":
        """Scroll the display to the top."""
        from euporie.core.widgets.display import DisplayControl

        current_control = get_app().layout.current_control
        if isinstance(current_control, DisplayControl):
            current_control.cursor_position = Point(0, 0)

    @staticmethod
    @add_cmd(filter=display_has_focus)
    def _go_to_end_of_display() -> "None":
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
