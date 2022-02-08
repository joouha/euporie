"""Defines custom controls which re-render on resize."""

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl

from euporie.config import config
from euporie.convert.base import convert
from euporie.text import ANSI

if TYPE_CHECKING:
    from typing import Any, Iterable, Optional

    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.utils import Event

    from euporie.graphics import TerminalGraphic

__all__ = [
    "FormatterControl",
]

log = logging.getLogger(__name__)


class FormatterControl(UIControl):
    """A data formatter, which displays cell output data.

    It will attempt to display the data in the best way possible, and reacts to resize
    events - i.e. images are downscaled to fit, markdown is re-flowed, etc.
    """

    def __init__(
        self,
        data: "Any",
        format_: "str",
        graphic: "Optional[TerminalGraphic]" = None,
        fg_color: "Optional[str]" = None,
        bg_color: "Optional[str]" = None,
        max_cols: "Optional[int]" = None,
        aspect: "Optional[float]" = None,
    ) -> "None":
        """Creates a new data formatter control.

        Args:
            data: Raw cell output data
            format_: The conversion format of the data to render
            graphic: The terminal graphic linked to this output
            fg_color: The foreground colour to use when renderin this output
            bg_color: The background colour to use when renderin this output
            max_cols: The maximum width of the output in temrinal columns
            aspect: The aspect ration of the output

        """
        self.data = data
        self.format_ = format_
        self.graphic = graphic
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.max_cols = max_cols or 0
        self.aspect = aspect

        self.rendered_lines: "list[StyleAndTextTuples]" = []
        self._format_cache: SimpleCache = SimpleCache(maxsize=50)
        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def get_rendered_lines(
        self, width: "int", height: "int"
    ) -> "list[StyleAndTextTuples]":
        """Get rendered lines from the cache, or generate them."""

        def render_lines() -> "list[StyleAndTextTuples]":
            """Renders the lines to display in the control."""
            lines = ""
            if self.graphic and config.dump:
                # We are displaying graphics images inline, so don't show any ansi
                log.debug(width)
                lines += "\n" * (height - 1) + " " * (width - 1) + " "
                lines += "\001" + self.graphic._draw_inline() + "\002"
            else:
                lines += convert(
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

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        """Returns the width of the rendered content."""
        return (
            min(self.max_cols, max_available_width)
            if self.max_cols
            else max_available_width
        )

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
            if not self.rendered_lines:
                self.rendered_lines = self.get_rendered_lines(
                    width, max_available_height
                )
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
        rows = int(cols * self.aspect) if self.aspect else height

        if self.graphic is not None:
            self.graphic.set_size(cols, rows)

        def get_content() -> "Optional[UIContent]":
            self.rendered_lines = self.get_rendered_lines(cols, rows)
            line_count = len(self.rendered_lines)

            def get_line(i: "int") -> "StyleAndTextTuples":
                # Return black lines if the renderer expects more content than we have
                if i >= line_count or (
                    self.graphic is not None
                    and self.graphic.visible()
                    and not config.dump
                ):
                    return []
                else:
                    return self.rendered_lines[i]

            return UIContent(
                get_line=get_line,
                line_count=line_count,
            )

        return self._content_cache.get((width,), get_content)

    def get_invalidate_events(self) -> "Iterable[Event[object]]":
        """Return the Window invalidate events."""
        # Whenever the buffer changes, the UI has to be updated.
        if self.graphic is not None:
            yield self.graphic.on_resize
            yield self.graphic.on_move
