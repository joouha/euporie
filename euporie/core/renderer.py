"""Extended version of prompt_toolkit's renderer."""

from __future__ import annotations

import logging
from hashlib import md5
from typing import TYPE_CHECKING

from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.filters import to_filter
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.renderer import Renderer as PtkRenderer
from prompt_toolkit.renderer import _StyleStringHasStyleCache, _StyleStringToAttrsCache

from euporie.core.io import Vt100_Output
from euporie.core.layout.screen import BoundedWritePosition, Screen

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from prompt_toolkit.application import Application
    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.layout.screen import Char
    from prompt_toolkit.layout.screen import Screen as PtkScreen
    from prompt_toolkit.output import ColorDepth, Output
    from prompt_toolkit.styles import BaseStyle

__all__ = ["Renderer"]

log = logging.getLogger(__name__)


def _output_screen_diff(
    app: Application[Any],
    output: Output,
    screen: PtkScreen,
    current_pos: Point,
    color_depth: ColorDepth,
    previous_screen: PtkScreen | None,
    last_style: str | None,
    is_done: bool,  # XXX: drop is_done
    full_screen: bool,
    attrs_for_style_string: _StyleStringToAttrsCache,
    style_string_has_style: _StyleStringHasStyleCache,
    size: Size,
    previous_width: int,
) -> tuple[Point, str | None]:
    """Render the diff between this screen and the previous screen."""
    width, height = size.columns, size.rows

    #: Variable for capturing the output.
    write = output.write
    write_raw = output.write_raw

    # Create locals for the most used output methods.
    # (Save expensive attribute lookups.)
    _output_set_attributes = output.set_attributes
    _output_reset_attributes = output.reset_attributes
    _output_cursor_forward = output.cursor_forward
    _output_cursor_up = output.cursor_up
    _output_cursor_backward = output.cursor_backward

    # Hide cursor before rendering. (Avoid flickering.)
    output.hide_cursor()

    def reset_attributes() -> None:
        """Wrap Output.reset_attributes."""
        nonlocal last_style
        _output_reset_attributes()
        last_style = None  # Forget last char after resetting attributes.

    def move_cursor(new: Point) -> Point:
        """Move cursor to this `new` point & return the given Point."""
        current_x, current_y = current_pos.x, current_pos.y

        if new.y > current_y:
            # Use newlines instead of CURSOR_DOWN, because this might add new lines.
            # CURSOR_DOWN will never create new lines at the bottom.
            # Also reset attributes, otherwise the newline could draw a
            # background color.
            reset_attributes()
            write("\r\n" * (new.y - current_y))
            current_x = 0
            _output_cursor_forward(new.x)
            return new
        elif new.y < current_y:
            _output_cursor_up(current_y - new.y)

        if current_x >= width - 1:
            write("\r")
            _output_cursor_forward(new.x)
        elif new.x < current_x or current_x >= width - 1:
            _output_cursor_backward(current_x - new.x)
        elif new.x > current_x:
            _output_cursor_forward(new.x - current_x)

        return new

    def output_char(char: Char) -> None:
        """Write the output of this character."""
        nonlocal last_style

        # If the last printed character has the same style, don't output the
        # style again.
        if last_style == char.style:
            write(char.char)
        else:
            # Look up `Attr` for this style string. Only set attributes if different.
            # (Two style strings can still have the same formatting.)
            # Note that an empty style string can have formatting that needs to
            # be applied, because of style transformations.
            new_attrs = attrs_for_style_string[char.style]
            if not last_style or new_attrs != attrs_for_style_string[last_style]:
                _output_set_attributes(new_attrs, color_depth)

            write(char.char)
            last_style = char.style

    def hash_screen_row(row: dict[int, Char], zwe_row: dict[int, str]) -> str:
        """Generate a hash for a screen row to quickly detect changes."""
        hasher = md5(usedforsecurity=False)
        # Hash the character data
        for idx in sorted(row.keys()):
            cell = row[idx]
            hasher.update(f"{idx}:{cell.char}:{cell.style}".encode())
        # Hash the zero-width escapes
        for idx in sorted(zwe_row.keys()):
            hasher.update(f"{idx}:{zwe_row[idx]}".encode())
        return hasher.hexdigest()

    def get_max_column_index(row: dict[int, Char], zwe_row: dict[int, str]) -> int:
        """Return max used column index, ignoring trailing unstyled whitespace."""
        max_idx = 0
        for idx, cell in row.items():
            if cell.char != " " or style_string_has_style[cell.style]:
                max_idx = max(max_idx, idx)
        for idx in zwe_row:
            max_idx = max(max_idx, idx - 1)
        return max_idx

    # Render for the first time: reset styling.
    if not previous_screen:
        reset_attributes()

    # Disable autowrap. (When entering a the alternate screen, or anytime when
    # we have a prompt. - In the case of a REPL, like IPython, people can have
    # background threads, and it's hard for debugging if their output is not
    # wrapped.)
    if not previous_screen or not full_screen:
        output.disable_autowrap()

    # When the previous screen has a different size, redraw everything anyway.
    # Also when we are done. (We might take up less rows, so clearing is important.)
    if (
        is_done or not previous_screen or previous_width != width
    ):  # XXX: also consider height??
        current_pos = move_cursor(Point(x=0, y=0))
        reset_attributes()
        output.erase_down()

        previous_screen = Screen()
    assert previous_screen is not None

    # Get height of the screen.
    # (height changes as we loop over data_buffer, so remember the current value.)
    # (Also make sure to clip the height to the size of the output.)
    current_height = min(screen.height, height)

    # Loop over the rows.
    row_count = min(max(screen.height, previous_screen.height), height)
    c = 0  # Column counter.

    for y in range(row_count):
        new_row = screen.data_buffer[y]
        previous_row = previous_screen.data_buffer[y]
        zwe_row = screen.zero_width_escapes[y]
        previous_zwe_row = previous_screen.zero_width_escapes[y]

        # Quick comparison using row hashes
        new_hash = hash_screen_row(new_row, zwe_row)
        prev_hash = hash_screen_row(previous_row, previous_zwe_row)

        if new_hash == prev_hash:
            # Rows are identical, skip to next row
            continue

        new_max_line_len = min(width - 1, get_max_column_index(new_row, zwe_row))
        previous_max_line_len = min(
            width - 1, get_max_column_index(previous_row, previous_zwe_row)
        )

        # Loop over the columns.
        c = 0

        prev_diff_char = False

        # Loop just beyond the line length to check for ZWE sequences right at the end
        # of the line
        while c <= new_max_line_len + 1:
            new_char = new_row[c]
            old_char = previous_row[c]
            new_zwe = zwe_row[c]
            char_width = new_char.width or 1

            # When the old and new character at this position are different,
            # draw the output. (Because of the performance, we don't call
            # `Char.__ne__`, but inline the same expression.)
            diff_char = (
                new_char.char != old_char.char or new_char.style != old_char.style
            )

            # Redraw escape sequences if the escape sequence at this position changed,
            # or if the current or previous character changed
            if new_zwe != previous_zwe_row[c] or diff_char or prev_diff_char:
                # Send injected escape sequences to output.
                write_raw(new_zwe)

            if diff_char:
                # Don't move the cursor if it is already in the correct position
                if c != current_pos.x or y != current_pos.y:
                    current_pos = move_cursor(Point(x=c, y=y))

                output_char(new_char)
                current_pos = Point(x=current_pos.x + char_width, y=current_pos.y)

            prev_diff_char = diff_char

            c += char_width

        # If the new line is shorter, trim it.
        if previous_screen and new_max_line_len < previous_max_line_len:
            # Don't move the cursor if it is already in the correct position
            if current_pos.x != new_max_line_len or current_pos.y != current_pos.y:
                current_pos = move_cursor(Point(x=new_max_line_len + 1, y=y))
            reset_attributes()
            output.erase_end_of_line()

    # Correctly reserve vertical space as required by the layout.
    # When this is a new screen (drawn for the first time), or for some reason
    # higher than the previous one. Move the cursor once to the bottom of the
    # output. That way, we're sure that the terminal scrolls up, even when the
    # lower lines of the canvas just contain whitespace.

    # The most obvious reason that we actually want this behaviour is the avoid
    # the artifact of the input scrolling when the completion menu is shown.
    # (If the scrolling is actually wanted, the layout can still be build in a
    # way to behave that way by setting a dynamic height.)
    if current_height > previous_screen.height:
        current_pos = move_cursor(Point(x=0, y=current_height - 1))

    # Move cursor:
    if is_done:
        current_pos = move_cursor(Point(x=0, y=current_height))
        output.erase_down()
    else:
        current_pos = move_cursor(screen.get_cursor_position(app.layout.current_window))

    if is_done or not full_screen:
        output.enable_autowrap()

    # Always reset the color attributes. This is important because a background
    # thread could print data to stdout and we want that to be displayed in the
    # default colors. (Also, if a background color has been set, many terminals
    # give weird artifacts on resize events.)
    reset_attributes()

    if screen.show_cursor or is_done:
        output.show_cursor()

    return current_pos, last_style


class Renderer(PtkRenderer):
    """Renderer with modifications."""

    def __init__(
        self,
        style: BaseStyle,
        output: Output,
        full_screen: bool = False,
        mouse_support: FilterOrBool = False,
        cpr_not_supported_callback: Callable[[], None] | None = None,
        extend_height: FilterOrBool = False,
        extend_width: FilterOrBool = False,
    ) -> None:
        """Create a new :py:class:`Renderer` instance."""
        self.app: Application[Any] | None = None
        self._extended_keys_enabled = False
        self._palette_dsr_enabled = False
        self._sgr_pixel_enabled = False
        self.extend_height = to_filter(extend_height)
        self.extend_width = to_filter(extend_width)
        super().__init__(
            style, output, full_screen, mouse_support, cpr_not_supported_callback
        )

    def reset(self, _scroll: bool = False, leave_alternate_screen: bool = True) -> None:
        """Reset the output."""
        output = self.output
        if isinstance(output, Vt100_Output):
            # Disable extended keys before resetting the output
            if self._extended_keys_enabled:
                output.disable_extended_keys()
                self._extended_keys_enabled = False

            # Disable palette change reporting
            if self._palette_dsr_enabled:
                output.disable_palette_dsr()
                self._palette_dsr_enabled = False

            # Disable sgr pixel mode
            if self._sgr_pixel_enabled:
                output.disable_sgr_pixel()
                self._sgr_pixel_enabled = False

        super().reset(_scroll, leave_alternate_screen)

    def render(
        self, app: Application[Any], layout: Layout, is_done: bool = False
    ) -> None:
        """Render the current interface to the output."""
        from euporie.core.app.app import BaseApp

        output = self.output
        self.app = app

        # Enter alternate screen.
        if self.full_screen and not self._in_alternate_screen:
            self._in_alternate_screen = True
            output.enter_alternate_screen()

        # Enable bracketed paste.
        if not self._bracketed_paste_enabled:
            self.output.enable_bracketed_paste()
            self._bracketed_paste_enabled = True

        # Reset cursor key mode.
        if not self._cursor_key_mode_reset:
            self.output.reset_cursor_key_mode()
            self._cursor_key_mode_reset = True

        # Enable/disable mouse support.
        needs_mouse_support = self.mouse_support()

        if needs_mouse_support and not self._mouse_support_enabled:
            output.enable_mouse_support()
            self._mouse_support_enabled = True

            if (
                isinstance(output, Vt100_Output)
                and isinstance(app, BaseApp)
                and app.term_sgr_pixel
            ):
                output.enable_sgr_pixel()
                self._sgr_pixel_enabled = True

        elif not needs_mouse_support and self._mouse_support_enabled:
            output.disable_mouse_support()
            self._mouse_support_enabled = False

            if (
                isinstance(output, Vt100_Output)
                and isinstance(app, BaseApp)
                and (app.term_sgr_pixel or self._sgr_pixel_enabled)
            ):
                output.disable_sgr_pixel()
                self._sgr_pixel_enabled = False

        # Enable extended keys
        if not self._extended_keys_enabled and isinstance(output, Vt100_Output):
            output.enable_extended_keys()
            self._extended_keys_enabled = True

        # Enable theme DSR
        if not self._palette_dsr_enabled and isinstance(output, Vt100_Output):
            output.enable_palette_dsr()
            self._palette_dsr_enabled = True

        # Create screen and write layout to it.
        size = output.get_size()
        screen = Screen()
        screen.show_cursor = False  # Hide cursor by default, unless one of the
        # containers decides to display it.
        mouse_handlers = MouseHandlers()

        # Calculate height.
        if self.full_screen:
            height = size.rows
        elif is_done:
            # When we are done, we don't necessary want to fill up until the bottom.
            height = layout.container.preferred_height(
                size.columns, size.rows
            ).preferred
        else:
            last_height = self._last_screen.height if self._last_screen else 0
            height = max(
                self._min_available_height,
                last_height,
                layout.container.preferred_height(size.columns, size.rows).preferred,
            )

        height = min(height, size.rows)

        # When the size changes, don't consider the previous screen.
        if self._last_size != size:
            self._last_screen = None

        # When we render using another style or another color depth, do a full
        # repaint. (Forget about the previous rendered screen.)
        # (But note that we still use _last_screen to calculate the height.)
        if (
            self.style.invalidation_hash() != self._last_style_hash
            or app.style_transformation.invalidation_hash()
            != self._last_transformation_hash
            or app.color_depth != self._last_color_depth
        ):
            self._last_screen = None
            self._attrs_for_style = None
            self._style_string_has_style = None

        if self._attrs_for_style is None:
            self._attrs_for_style = _StyleStringToAttrsCache(
                self.style.get_attrs_for_style_str, app.style_transformation
            )
        if self._style_string_has_style is None:
            self._style_string_has_style = _StyleStringHasStyleCache(
                self._attrs_for_style
            )

        self._last_style_hash = self.style.invalidation_hash()
        self._last_transformation_hash = app.style_transformation.invalidation_hash()
        self._last_color_depth = app.color_depth

        layout.container.write_to_screen(
            screen,
            mouse_handlers,
            BoundedWritePosition(
                xpos=0,
                ypos=0,
                width=size.columns,
                height=height,
            ),
            parent_style="",
            erase_bg=False,
            z_index=None,
        )
        screen.draw_all_floats()

        # When grayed. Replace all styles in the new screen.
        if app.exit_style:
            screen.append_style_to_content(app.exit_style)

        # Expand size if required
        output_size = size
        if self.extend_height():
            output_size = Size(9999999, output_size.columns)
        if self.extend_width():
            output_size = Size(size.rows, output_size.columns + 1)

        # Process diff and write to output.
        self._cursor_pos, self._last_style = _output_screen_diff(
            app,
            output,
            screen,
            self._cursor_pos,
            app.color_depth,
            self._last_screen,
            self._last_style,
            is_done,
            full_screen=self.full_screen,
            attrs_for_style_string=self._attrs_for_style,
            style_string_has_style=self._style_string_has_style,
            size=output_size,
            previous_width=(self._last_size.columns if self._last_size else 0),
        )
        self._last_screen = screen
        self._last_size = size
        self.mouse_handlers = mouse_handlers

        # Handle cursor shapes.
        new_cursor_shape = app.cursor.get_cursor_shape(app)
        if (
            self._last_cursor_shape is None
            or self._last_cursor_shape != new_cursor_shape
        ):
            output.set_cursor_shape(new_cursor_shape)
            self._last_cursor_shape = new_cursor_shape

        # Flush buffered output.
        output.flush()

        # Set visible windows in layout.
        app.layout.visible_windows = screen.visible_windows

        if is_done:
            self.reset()
