"""Buffer processors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    Processor,
    Transformation,
)
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.utils import get_cwidth

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.layout.processors import TransformationInput

    from euporie.core.diagnostics import Report


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
            return Transformation(fragments=[*ti.fragments, (self.style, suggestion)])
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


class DiagnosticProcessor(Processor):
    """Highlight diagnostics."""

    def __init__(
        self,
        report: Report | Callable[[], Report],
        style: str = "underline",
    ) -> None:
        """Create a new processor instance."""
        self._report = report
        self.style = style

    @property
    def report(self) -> Report:
        """Return the current diagnostics report."""
        if callable(self._report):
            return self._report()
        return self._report

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Underline the text ranges relating to diagnostics in the report."""
        line = ti.lineno
        fragments = ti.fragments
        self_style = self.style
        for item in self.report:
            if item.lines.start < line < item.lines.stop - 1:
                fragments = cast(
                    "StyleAndTextTuples",
                    [
                        (f"{style} {self.style}", text, *rest)
                        for style, text, *rest in fragments
                    ],
                )
            elif line == item.lines.start or line == item.lines.stop - 1:
                fragments = explode_text_fragments(fragments)
                start = item.chars.start if line == item.lines.start else 0
                end = (
                    item.chars.stop - 1
                    if line == item.lines.stop - 1
                    else len(fragments)
                )
                for i in range(start, min(len(fragments), end)):
                    fragments[i] = (
                        f"{fragments[i][0]} {self_style}",
                        *fragments[i][1:],
                    )

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


# Apply processors
# merged_processor = self.cursor_processor
# line = lines[i]
# transformation = merged_processor.apply_transformation(
#     TransformationInput(
#         buffer_control=self, document=Document(), lineno=i, source_to_display=lambda i: i, fragments=line, width=width, height=height,
#     )
# )
# return transformation.fragments
