"""Defines custom controls which re-render on resize."""

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event

from euporie.app.current import get_tui_app as get_app
from euporie.convert.base import convert
from euporie.key_binding.bindings.commands import load_command_bindings
from euporie.terminal import tmuxify

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable, Optional

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone

__all__ = [
    "FormattedOutputControl",
]

log = logging.getLogger(__name__)


class OutputControl(UIControl):
    """A data formatter, which displays cell output data.

    It will attempt to display the data in the best way possible, and reacts to resize
    events - i.e. images are downscaled to fit, markdown is re-flowed, etc.
    """

    def __init__(
        self,
        data: "Any",
        format_: "str",
        fg_color: "Optional[str]" = None,
        bg_color: "Optional[str]" = None,
        sizing_func: "Optional[Callable[[], tuple[int, float]]]" = None,
        focusable: "FilterOrBool" = False,
        focus_on_click: "FilterOrBool" = False,
    ) -> "None":
        """Creates a new data formatter control.

        Args:
            data: Raw cell output data
            format_: The conversion format of the data to render
            fg_color: The foreground colour to use when renderin this output
            bg_color: The background colour to use when renderin this output
            sizing_func: Function which returns the maximum width and aspect ratio of
                the output
            focusable: Whether the control can be focused
            focus_on_click: Whether to focus the control when clicked

        """
        self.data = data
        self.format_ = format_
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.focusable = to_filter(focusable)
        self.focus_on_click = to_filter(focus_on_click)
        self.key_bindings = load_command_bindings("cell-output")
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

    def get_key_bindings(self) -> "Optional[KeyBindingsBase]":
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

    def is_focusable(self) -> "bool":
        """Determines if the current control is focusable."""
        return self.focusable()

    def size(self) -> "None":
        """Load the maximum cell width and apect ratio of the output."""
        self._max_cols, self._aspect = self._size_cache.get(
            (self.app.render_counter,), self.sizing_func
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

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
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
        get_line_prefix: Optional[GetLinePrefixCallable],
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
            rendered_lines = self.get_rendered_lines(cols, rows)
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: "int") -> "StyleAndTextTuples":
                # Return blank lines if the renderer expects more content than we have
                line = []
                if i < line_count:
                    line += rendered_lines[i]
                # Add a space at the end, because that is a possible cursor position.
                # This is what PTK does, and fixes a nasty bug which took me ages to
                # track down the source of where scrolling would stop working when the
                # cursor was on an empty line.
                line += [("", " ")]
                return line

            return {
                "get_line": get_line,
                "line_count": line_count,
                "menu_position": Point(0, 0),
            }

        # Re-render if the image width changes, or the terminal character size changes
        return UIContent(
            cursor_position=self.cursor_position,
            **self._content_cache.get((width,), get_content),
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


class FormattedOutputControl(OutputControl):
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
                    )
                )
            )

        # Re-render if the image width changes, or the terminal character size changes
        key = (width, self.app.term_info.cell_size_px)
        # log.debug(key)
        return self._format_cache.get(key, render_lines)


class SixelGraphicControl(OutputControl):
    def get_rendered_lines(
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
            cmd = convert(
                data=self.data,
                from_=self.format_,
                to="sixel",
                cols=width,
                rows=height,
                fg=self.fg_color,
                bg=self.bg_color,
            )
            return list(
                split_lines(
                    to_formatted_text(
                        [
                            ("", "\n".join([" " * width] * (height))[:-1]),
                            (
                                "[ZeroWidthEscape]",
                                tmuxify(
                                    f"\x1b[s\x1b[{height-1}A\x1b[{width-1}D{cmd}\x1b[u"
                                ),
                            ),
                        ]
                    )
                )
            )

        return self._format_cache.get(
            (width,),
            render_lines,
        )


class ItermGraphicControl(OutputControl):
    def __init__(
        self,
        data: "Any",
        format_: "str",
        fg_color: "Optional[str]" = None,
        bg_color: "Optional[str]" = None,
        sizing_func: "Optional[Callable]" = None,
    ) -> "None":
        super().__init__(
            data,
            format_,
            fg_color,
            bg_color,
            sizing_func,
        )
        if format_.startswith("base64-"):
            self.b64data = data
        else:
            self.b64data = convert(
                data=data,
                from_=self.format_,
                to="base64-png",
                fg=self.fg_color,
                bg=self.bg_color,
            )
        self.b64data = self.b64data.replace("\n", "").strip()

    def get_rendered_lines(
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
            cmd = f"\x1b]1337;File=inline=1;width={width}:{self.b64data}\a"
            return list(
                split_lines(
                    to_formatted_text(
                        [
                            ("", "\n".join([" " * width] * (height))),
                            (
                                "[ZeroWidthEscape]",
                                tmuxify(
                                    f"\x1b[s\x1b[{height-1}A\x1b[{width}D{cmd}\x1b[u"
                                ),
                            ),
                            ("", "\n"),
                        ]
                    )
                )
            )

        return self._format_cache.get(
            (width,),
            render_lines,
        )


_kitty_image_count = 1


class KittyGraphicControl(OutputControl):
    def __init__(
        self,
        data: "Any",
        format_: "str",
        fg_color: "Optional[str]" = None,
        bg_color: "Optional[str]" = None,
        sizing_func: "Optional[Callable]" = None,
    ) -> "None":
        super().__init__(
            data,
            format_,
            fg_color,
            bg_color,
            sizing_func,
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

        data = self.convert_data(rows, cols)
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

    def get_rendered_lines(
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""
        # TODO - wezterm does not scale kitty graphics, so we might want to resize
        # images at this point rather than just loading them once
        if not self.loaded:
            self.load(width, height)

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
            cmd = self._kitty_cmd(
                a="p",  # Display a previously transmitted image
                i=self.kitty_image_id,
                p=1,  # Placement ID
                m=0,  # No batches remaining
                q=2,  # No backchat
                c=width,
                r=height,
                C=1,  # Do not scroll
                z=-(2**30) - 1,
            )
            cmd = cmd
            return list(
                split_lines(
                    to_formatted_text(
                        [
                            ("", "\n".join([" " * width] * height)),
                            (
                                "[ZeroWidthEscape]",
                                tmuxify(
                                    f"\x1b[s\x1b[{height-1}A\x1b[{width}D{cmd}\x1b[u"
                                ),
                            ),
                            ("", "\n"),
                        ]
                    )
                )
            )

        return self._format_cache.get(
            (width,),
            render_lines,
        )
