"""Suggests line completions from kernel history."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.auto_suggest import AutoSuggest, ConditionalAutoSuggest, Suggestion
from prompt_toolkit.filters import to_filter
from prompt_toolkit.layout.processors import AppendAutoSuggestion, Transformation

if TYPE_CHECKING:
    from typing import Optional, Union

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.document import Document
    from prompt_toolkit.filters import Filter
    from prompt_toolkit.layout.processors import TransformationInput

    from euporie.kernel import NotebookKernel

log = logging.getLogger(__name__)

__all__ = ["KernelAutoSuggest"]


class KernelAutoSuggest(AutoSuggest):
    """Suggests line completions from kernel history."""

    def __init__(self, kernel: "NotebookKernel") -> "None":
        """Sets the kernel instance in initialization."""
        self.kernel = kernel

    def get_suggestion(
        self, buffer: "Buffer", document: "Document"
    ) -> Optional[Suggestion]:
        """Does nothing."""
        return None

    async def get_suggestion_async(
        self, buff: "Buffer", document: "Document"
    ) -> "Optional[Suggestion]":
        """Return suggestions based on matching kernel history."""
        line = document.current_line.strip()
        if line:
            suggestions = await self.kernel.history_(f"*{line}*")
            log.debug("Suggestor got suggestions %s", suggestions)
            if suggestions:
                _, _, text = suggestions[0]
                # Find matching line
                for hist_line in text.split("\n"):
                    hist_line = hist_line.strip()
                    if hist_line.startswith(line):
                        # Return from the match to end from the history line
                        suggestion = hist_line[len(line) :]
                        log.debug("Suggesting %s", suggestion)
                        return Suggestion(suggestion)
        return None


class ConditionalAutoSuggestAsync(ConditionalAutoSuggest):
    """Auto suggest that can be turned on and of according to a certain condition."""

    def __init__(
        self, auto_suggest: "AutoSuggest", filter: "Union[bool, Filter]"
    ) -> "None":
        """An asynchronous conditional autosuggestion wrapper.

        Args:
            auto_suggest: The :class:`AutoSuggest` to use to retrieve suggestions
            filter: The filter use to determine if autosuggestions should be retrieved

        """
        self.auto_suggest = auto_suggest
        self.filter = to_filter(filter)

    async def get_suggestion_async(
        self, buffer: "Buffer", document: "Document"
    ) -> "Optional[Suggestion]":
        """Get suggestions asynchronously if the filter allows."""
        if self.filter():
            return await self.auto_suggest.get_suggestion_async(buffer, document)

        return None


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
