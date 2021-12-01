# -*- coding: utf-8 -*-
"""Suggests line completions from kernel history."""
from __future__ import annotations

import logging
from typing import Optional

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document

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
