"""Adds ability to deduplicate completions asynchronously."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion.deduplicate import (
    DeduplicateCompleter as PtkDeduplicateCompleter,
)
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from euporie.apptk.completion.base import CompleteEvent, Completion
    from euporie.apptk.document import Document

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from euporie.apptk.document import Document

__all__ = ["DeduplicateCompleter"]


class DeduplicateCompleter(PtkDeduplicateCompleter):
    """Wrapper around a completer that removes duplicates asynchronously.

    Only the first unique completions are kept. Completions are considered to be a
    duplicate if they result in the same document text when they would be applied.
    """

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion]:
        """Get completions from wrapped completer."""
        # Keep track of the document strings we'd get after applying any completion.
        found_so_far: set[str] = set()

        async for completion in self.completer.get_completions_async(
            document, complete_event
        ):
            text_if_applied = (
                document.text[: document.cursor_position + completion.start_position]
                + completion.text
                + document.text[document.cursor_position :]
            )

            if text_if_applied == document.text:
                # Don't include completions that don't have any effect at all.
                continue

            if text_if_applied in found_so_far:
                continue

            found_so_far.add(text_if_applied)
            yield completion
