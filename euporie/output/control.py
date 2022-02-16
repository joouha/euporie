"""Defines custom controls which re-render on resize."""

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl

from euporie.app.current import get_tui_app as get_app
from euporie.convert.base import convert
from euporie.text import ANSI

if TYPE_CHECKING:
    from typing import Any, Callable, Optional

    from prompt_toolkit.formatted_text import StyleAndTextTuples

__all__ = [
    "AnsiControl",
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
        sizing_func: "Optional[Callable]" = None,
    ) -> "None":
        """Creates a new data formatter control.

        Args:
            data: Raw cell output data
            format_: The conversion format of the data to render
            fg_color: The foreground colour to use when renderin this output
            bg_color: The background colour to use when renderin this output
            sizing_func: Function which returns the maximum width and aspect ratio of
                the output

        """
        self.data = data
        self.format_ = format_
        self.fg_color = fg_color
        self.bg_color = bg_color

        self.sizing_func = sizing_func
        self.sized = False
        self._max_cols = 0
        self._aspect: "Optional[float]" = None

        self.rendered_lines: "list[StyleAndTextTuples]" = []
        self._format_cache: SimpleCache = SimpleCache(maxsize=50)
        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def size(self) -> "None":
        """Lazily load the maximum width and apect ratio of the output."""
        if self.sizing_func is not None:
            self._max_cols, self._aspect = self.sizing_func()
        self.sized = True

    def hide(self) -> "None":
        """Hides the output from show."""
        pass

    @property
    def max_cols(self) -> "int":
        """Lazily load the maximum width of the output in terminal columns."""
        if not self.sized:
            self.size()
        return self._max_cols

    @property
    def aspect(self) -> "Optional[float]":
        """Lazily load the aspect ratio of the output."""
        if not self.sized:
            self.size()
        return self._aspect

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        """Returns the width of the rendered content."""
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

        def get_content() -> "Optional[UIContent]":
            rendered_lines = self.get_rendered_lines(cols, rows)
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: "int") -> "StyleAndTextTuples":
                # Return blank lines if the renderer expects more content than we have
                if i > line_count - 1:
                    return []
                else:
                    return rendered_lines[i]

            return UIContent(
                get_line=get_line,
                line_count=line_count,
                menu_position=Point(0, 0),
            )

        return self._content_cache.get((width,), get_content)


class AnsiControl(OutputControl):
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
            lines = convert(
                data=self.data,
                from_=self.format_,
                to="ansi",
                cols=width,
                rows=height,
                fg=self.fg_color,
                bg=self.bg_color,
            ).strip()
            return list(split_lines(to_formatted_text(ANSI(lines))))

        return self._format_cache.get(
            (width,),
            render_lines,
        )


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
                            ("", "\n".join([" " * width] * (height))),
                            (
                                "[ZeroWidthEscape]",
                                f"\x1b[s\x1b[{height-1}A\x1b[{width}D{cmd}\x1b[u",
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
        self.app = get_app()

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
            self.app.output.write_raw(cmd)
        self.app.output.flush()
        self.loaded = True

    def hide(self) -> "None":
        """Hides the graphic from show without deleting it."""
        if self.kitty_image_id > 0:
            self.app.output.write_raw(
                self._kitty_cmd(
                    a="d",
                    d="i",
                    i=self.kitty_image_id,
                    q=1,
                )
            )
            self.app.output.flush()

    def delete(self) -> "None":
        """Deletes the graphic from the terminal."""
        self.app.output.write_raw(
            self._kitty_cmd(
                a="D",
                d="I",
                i=self.kitty_image_id,
                q=2,
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
            return list(
                split_lines(
                    to_formatted_text(
                        [
                            ("", "\n".join([" " * width] * height)),
                            (
                                "[ZeroWidthEscape]",
                                f"\x1b[s\x1b[{height-1}A\x1b[{width}D{cmd}\x1b[u",
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

    def create_content(self, width: "int", height: "int") -> "UIContent":
        return super().create_content(width, height)
