"""Suggest line completions from kernel history."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.auto_suggest import AutoSuggest, ConditionalAutoSuggest, Suggestion
from prompt_toolkit.filters import to_filter

if TYPE_CHECKING:
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.document import Document
    from prompt_toolkit.filters import Filter
    from prompt_toolkit.history import History


log = logging.getLogger(__name__)


class HistoryPosition(NamedTuple):
    """Store position information for a history match."""

    idx: int  # Index in history
    context_start: int  # Position where context starts
    context_end: int  # Position where context ends


class HistoryAutoSuggest(AutoSuggest):
    """Suggest line completions from a :class:`History` object."""

    _context_lines = 10
    _max_line_len = 200
    _max_item_lines = 1000

    def __init__(self, history: History) -> None:
        """Set the kernel instance in initialization."""
        self.history = history
        self.calculate_similarity = lru_cache(maxsize=1024)(self._calculate_similarity)

        self.n_texts = 0
        self.n_lines = 0
        self._processing_task: asyncio.Task | None = None
        self.prefix_dict: dict[str, dict[str, set[HistoryPosition]]] = defaultdict(
            lambda: defaultdict(set)
        )

    def process_history(self) -> None:
        """Schedule history processing if not already running."""
        from euporie.notebook.current import get_app

        if self._processing_task is not None and not self._processing_task.done():
            return

        # Schedule the actual processing to run when idle
        self._processing_task = get_app().create_background_task(
            self._process_history_async()
        )

    async def _process_history_async(self) -> None:
        """Process the entire history and store in prefix_dict."""
        texts = self.history._loaded_strings
        if not (texts := texts[: len(texts) - self.n_texts]):
            return
        # log.debug("Indexing %d history items", len(texts))

        n_lines = self.n_lines
        prefix_dict = self.prefix_dict

        for i, text in enumerate(reversed(texts)):
            lines = text.splitlines(keepends=True)
            max_line = len(lines) - 1

            positions = [0]
            for line in lines:
                positions.append(positions[-1] + len(line))
                n_lines += 1

            for line_idx, line in enumerate(
                iterable=lines[-self._max_item_lines :],
                start=max(0, len(lines) - self._max_item_lines),
            ):
                if not (stripped_line := line.strip()):
                    continue

                hist_pos = HistoryPosition(
                    idx=i,
                    context_start=positions[max(0, line_idx - self._context_lines)],
                    context_end=positions[min(line_idx + self._context_lines, max_line)]
                    + 1,
                )

                for j in range(min(len(stripped_line), self._max_line_len)):
                    prefix, suffix = stripped_line[:j], stripped_line[j:]
                    prefix_dict[prefix][suffix].add(hist_pos)

            # Add tiny sleep to prevent blocking
            await asyncio.sleep(0.001)

        self.n_lines = n_lines
        self.n_texts += len(texts)
        # log.debug("Added %d history items to index", len(texts))

    def _calculate_similarity(self, text_1: str, text_2: str) -> float:
        """Calculate and cache the similarity between two texts."""
        return SequenceMatcher(None, text_1, text_2).quick_ratio()

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        """Get a line completion suggestion."""
        line = document.current_line.lstrip()
        if len(line) > self._max_line_len:
            return None

        # Schedule indexing any new history items
        self.process_history()

        # Find matches
        if not (suffixes := self.prefix_dict[line]):
            return None

        texts = self.history._loaded_strings
        best_score = 0.0
        best_suffix = ""

        # Rank candidates
        max_count = max([1, *(len(x) for x in suffixes.values())])
        for suffix, positions in suffixes.items():
            count = len(positions)
            for i, pos in enumerate(positions):
                # Process up to 10 instances of this prefix
                if i == 10:
                    break
                # Get the text using the stored positions
                text = texts[pos.idx]
                context = text[pos.context_start : pos.context_end]
                context_similarity = self.calculate_similarity(document.text, context)
                score = (
                    # Number of instances in history
                    0.3 * count / max_count
                    # Recentness
                    + 0.3 * pos.idx / len(texts)
                    # Similarity of context to document
                    + 0.4 * context_similarity
                )

                if score > 0.9:
                    return Suggestion(suffix)
                if score > best_score:
                    best_score = score
                    best_suffix = suffix

        if best_suffix:
            return Suggestion(best_suffix)
        return None


# class KernelAutoSuggest(AutoSuggest):
#     """Suggest line completions from kernel history."""

#     def __init__(self, kernel: Kernel) -> None:
#         """Set the kernel instance in initialization."""
#         self.kernel = kernel

#     def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
#         """Doe nothing."""
#         return None

#     async def get_suggestion_async(
#         self, buff: Buffer, document: Document
#     ) -> Suggestion | None:
#         """Return suggestions based on matching kernel history."""
#         line = document.current_line.strip()
#         if line:
#             suggestions = await self.kernel.history_(f"*{line}*")
#             log.debug("Suggestor got suggestions %s", suggestions)
#             if suggestions:
#                 _, _, text = suggestions[0]
#                 # Find matching line
#                 for hist_line in text.split("\n"):
#                     hist_line = hist_line.strip()
#                     if hist_line.startswith(line):
#                         # Return from the match to end from the history line
#                         suggestion = hist_line[len(line) :]
#                         log.debug("Suggesting %s", suggestion)
#                         return Suggestion(suggestion)
#         return None


class ConditionalAutoSuggestAsync(ConditionalAutoSuggest):
    """Auto suggest that can be turned on and of according to a certain condition."""

    def __init__(self, auto_suggest: AutoSuggest, filter: bool | Filter) -> None:
        """Create a new asynchronous conditional autosuggestion wrapper.

        Args:
            auto_suggest: The :class:`AutoSuggest` to use to retrieve suggestions
            filter: The filter use to determine if autosuggestions should be retrieved

        """
        self.auto_suggest = auto_suggest
        self.filter = to_filter(filter)

    async def get_suggestion_async(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None:
        """Get suggestions asynchronously if the filter allows."""
        if self.filter():
            return await self.auto_suggest.get_suggestion_async(buffer, document)

        return None
