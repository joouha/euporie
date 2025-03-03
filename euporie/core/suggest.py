"""Suggest line completions from kernel history."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from difflib import SequenceMatcher
from functools import lru_cache, partial
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.auto_suggest import AutoSuggest, ConditionalAutoSuggest, Suggestion
from prompt_toolkit.cache import SimpleCache
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


class SmartHistoryAutoSuggest(AutoSuggest):
    """Suggest line completions from a :class:`History` object."""

    _context_lines = 10
    _max_line_len = 200
    _max_item_lines = 1000

    def __init__(self, history: History) -> None:
        """Set the kernel instance in initialization."""
        self.history = history

        self.n_texts = 0
        self._processing_task: asyncio.Task | None = None
        # Index storage
        self.prefix_tree: dict[str, list[int]] = defaultdict(list)
        self.suffix_data: list[tuple[str, HistoryPosition]] = []
        # Caches
        self.calculate_similarity = lru_cache(maxsize=128)(self._calculate_similarity)
        self.match_cache: SimpleCache[tuple[str, int, int], Suggestion | None] = (
            SimpleCache(maxsize=128)
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
        # Only process new history items
        if not (texts := texts[: -self.n_texts or None]):
            return

        prefix_tree = self.prefix_tree
        suffix_data = self.suffix_data
        context_lines = self._context_lines
        max_item_lines = self._max_item_lines
        max_line_len = self._max_line_len

        for i, text in enumerate(texts):
            # Add tiny sleep to prevent blocking
            if i > 1:
                await asyncio.sleep(0.001)

            lines = text.splitlines(keepends=True)
            # Calculate positions of newlines
            line_pos = [0]
            for line in lines:
                line_pos.append(line_pos[-1] + len(line))
            # Index each line
            for j, line in enumerate(lines[:max_item_lines]):
                context_start = line_pos[max(0, j - context_lines)]
                context_end = line_pos[min(j + context_lines, len(lines))]
                hist_pos = HistoryPosition(
                    idx=i, context_start=context_start, context_end=context_end
                )
                line = line.strip()
                # Create prefix/suffix combinations
                for k in range(min(len(line), max_line_len)):
                    prefix, suffix = line[:k], line[k:]
                    prefix_tree[prefix].append(len(suffix_data))
                    suffix_data.append((suffix, hist_pos))

        self.n_texts += len(texts)

    def _calculate_similarity(self, text_1: str, text_2: str) -> float:
        """Calculate and cache the similarity between two texts."""
        return SequenceMatcher(None, text_1, text_2).quick_ratio()

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        """Get a line completion suggestion."""
        # Only return suggestions if cursor is at end of line
        if not document.is_cursor_at_the_end_of_line:
            return None

        line = document.current_line.lstrip()

        # Skip empty and very long lines
        if not line or len(line) > self._max_line_len:
            return None

        # Schedule indexing any new history items
        self.process_history()

        # Find matches
        key = line, hash(document.text), len(self.suffix_data)
        return self.match_cache.get(key, partial(self._find_match, line, document.text))

    def _find_match(self, line: str, document_text: str) -> Suggestion | None:
        if not (suffix_indices := self.prefix_tree[line]):
            return None

        texts = self.history._loaded_strings
        best_score = 0.0
        best_suffix = None

        # Rank candidates
        max_count = max(1, len(suffix_indices))
        suffix_groups: dict[str, list[HistoryPosition]] = defaultdict(list)

        # Group suffixes and their positions
        for idx in suffix_indices:
            suffix, pos = self.suffix_data[idx]
            suffix_groups[suffix].append(pos)

        # Evaluate each unique suffix
        for suffix, positions in suffix_groups.items():
            count = len(positions)
            for pos in positions[:10]:
                # Get the text using the stored positions
                text = texts[pos.idx]
                context = text[pos.context_start : pos.context_end]
                context_similarity = self.calculate_similarity(document_text, context)
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


class SimpleHistoryAutoSuggest(AutoSuggest):
    """Suggest line completions from a :class:`History` object."""

    def __init__(self, history: History, cache_size: int = 100_000) -> None:
        """Set the kernel instance in initialization."""
        self.history = history

        self.cache_size = cache_size
        self.cache_keys: deque[str] = deque()
        self.cache: dict[str, Suggestion] = {}

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        """Get a line completion suggestion."""
        result: Suggestion | None = None
        line = document.current_line.lstrip()
        if line:
            if line in self.cache:
                result = self.cache[line]
            else:
                result = self.lookup_suggestion(line)
                if result:
                    if len(self.cache) > self.cache_size:
                        key_to_remove = self.cache_keys.popleft()
                        if key_to_remove in self.cache:
                            del self.cache[key_to_remove]

                    self.cache_keys.append(line)
                    self.cache[line] = result
        return result

    def lookup_suggestion(self, line: str) -> Suggestion | None:
        """Find the most recent matching line in the history."""
        # Loop history, most recent item first
        for text in self.history._loaded_strings:
            if line in text:
                # Loop over lines of item in reverse order
                for hist_line in text.splitlines()[::-1]:
                    hist_line = hist_line.strip()
                    if hist_line.startswith(line):
                        # Return from the match to end from the history line
                        suggestion = hist_line[len(line) :]
                        return Suggestion(suggestion)
        return None


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
