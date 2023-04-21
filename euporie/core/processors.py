"""Buffer processors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    Processor,
    Transformation,
)
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.utils import get_cwidth

if TYPE_CHECKING:
    from typing import Callable

    from prompt_toolkit.layout.processors import TransformationInput


log = logging.getLogger(__name__)


class AppendLineAutoSuggestion(AppendAutoSuggestion):
    """Append the auto suggestion to the current line of the input."""

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Inert fragments at the end of the current line."""
        if ti.lineno == ti.document.cursor_position_row:
            buffer = ti.buffer_control.buffer

            if buffer.suggestion and ti.document.is_cursor_at_the_end_of_line:
                suggestion = buffer.suggestion.text
            else:
                suggestion = ""
            return Transformation(fragments=ti.fragments + [(self.style, suggestion)])
        else:
            return Transformation(fragments=ti.fragments)


class ShowTrailingWhiteSpaceProcessor(Processor):
    """Make trailing whitespace visible."""

    def __init__(
        self,
        char: str = "·",
        style: str = "class:trailing-whitespace",
    ) -> None:
        """Create a new processor instance."""
        self.char = char
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Walk backwards through all the fragments and replace whitespace."""
        fragments = ti.fragments
        if fragments and fragments[-1][1].endswith(" "):
            fragments = explode_text_fragments(fragments)
            new_char = self.char
            for i in range(len(fragments) - 1, -1, -1):
                style, char, *_ = fragments[i]
                if char == " ":
                    fragments[i] = (f"{style} {self.style}", new_char)
                else:
                    break
        return Transformation(fragments)


class CursorProcessor(Processor):
    """Show a mouse cursor."""

    def __init__(
        self,
        get_cursor_position: Callable[[], Point],
        char: str = "🮰",
        style: str = "class:mouse",
    ) -> None:
        """Create a new processor instance."""
        self.char = char
        self.style = style
        self.get_cursor_position = get_cursor_position

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Replace character at the cursor position."""
        pos = self.get_cursor_position()
        fragments = ti.fragments
        if ti.lineno == pos.y:
            fragments = explode_text_fragments(fragments)
            if (length := len(fragments)) < (x := pos.x):
                fragments.append(("", " " * (x - length)))
            frag = fragments[x]
            char = self.char.ljust(get_cwidth(frag[1]))
            fragments[x] = (
                f"{frag[0]} {self.style}",
                char,
            )
        return Transformation(fragments)
