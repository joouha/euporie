"""Buffer processors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    Processor,
    Transformation,
)
from prompt_toolkit.layout.utils import explode_text_fragments

if TYPE_CHECKING:
    from prompt_toolkit.layout.processors import TransformationInput


log = logging.getLogger(__name__)


class AppendLineAutoSuggestion(AppendAutoSuggestion):
    """Append the auto suggestion to the current line of the input."""

    def apply_transformation(self, ti: "TransformationInput") -> "Transformation":
        """Insert fragments at the end of the current line."""
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
        char: "str" = "·",
        style: "str" = "class:trailing-whitespace",
    ) -> "None":
        """Create a new processor instance."""
        self.char = char
        self.style = style

    def apply_transformation(self, ti: "TransformationInput") -> "Transformation":
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
