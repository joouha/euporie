"""Buffer processors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apptk.formatted_text.utils import fragment_list_to_text, strip
from apptk.layout.processors import (
    AppendAutoSuggestion,
    Processor,
    Transformation,
)
from apptk.layout.processors import (
    TabsProcessor as PtkTabsProcessor,
)
from apptk.layout.utils import explode_text_fragments
from apptk.utils import get_cwidth

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.data_structures import Point
    from apptk.layout.processors import TransformationInput


log = logging.getLogger(__name__)


class TabsProcessor(PtkTabsProcessor):
    r""":py:class:`TabsProcessor` with a fast path for lines without tabs.

    The upstream implementation always calls :py:func:`explode_text_fragments`
    and builds position mappings even when the line has no tab character.
    Height calculation for a large cell runs every per-line processor over
    every line, several times per render, so this check is on the hot path.

    The fast path uses :py:func:`fragment_list_to_text` on the raw fragments
    (cheap: it just joins the text parts) and returns the fragments unchanged
    when there is no ``\t`` in the line.  Behaviour is identical to the
    upstream processor whenever a tab is present.
    """

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Expand tabs, or return the fragments unchanged when none are present."""
        if "\t" not in fragment_list_to_text(ti.fragments):
            return Transformation(ti.fragments)
        return super().apply_transformation(ti)


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


class StripTrailingWhiteSpaceProcessor(Processor):
    """Strip trailing whitespace from line fragments.

    Args:
        only_unstyled: If :py:const:`True`, only strip whitespace from fragments
            that have no style applied.
    """

    def __init__(self, chars: str | None = None, only_unstyled: bool = True) -> None:
        """Create a new processor instance."""
        self.chars = chars
        self.only_unstyled = only_unstyled

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Remove trailing whitespace from the line fragments."""
        fragments = ti.fragments

        if not fragments:
            return Transformation(fragments)

        result = strip(
            fragments,
            left=False,
            right=True,
            chars=self.chars,
            only_unstyled=self.only_unstyled,
        )
        return Transformation(result)


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


# How to apply processors
# merged_processor = self.cursor_processor
# line = lines[i]
# transformation = merged_processor.apply_transformation(
#     TransformationInput(
#         buffer_control=self, document=Document(), lineno=i, source_to_display=lambda i: i, fragments=line, width=width, height=height,
#     )
# )
# return transformation.fragments
