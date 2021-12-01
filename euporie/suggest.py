# -*- coding: utf-8 -*-
"""Suggests line completions from kernel history."""
from __future__ import annotations

import logging
from typing import Optional

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    Transformation,
    TransformationInput,
)

from euporie.config import config
from euporie.kernel import NotebookKernel

log = logging.getLogger(__name__)


class KernelAutoSuggest(AutoSuggest):
    """Suggests line completions from kernel history."""

    def __init__(self, kernel: "NotebookKernel") -> "None":
        """Sets the kernel instance in initalization."""
        self.kernel = kernel

    def get_suggestion(
        self, buffer: "Buffer", document: Document
    ) -> Optional[Suggestion]:
        """Does nothing."""
        return None

    async def get_suggestion_async(
        self, buff: "Buffer", document: "Document"
    ) -> Optional[Suggestion]:
        """Return suggestions based on matching kernel history."""
        if config.autosuggest:
            line = document.current_line.strip()
            if line:
                suggestions = await self.kernel._history(f"*{line}*")
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
