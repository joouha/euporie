"""Suggest line completions from kernel history."""

from __future__ import annotations

import logging
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING

from prompt_toolkit.auto_suggest import AutoSuggest, ConditionalAutoSuggest, Suggestion
from prompt_toolkit.filters import to_filter

if TYPE_CHECKING:
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.document import Document
    from prompt_toolkit.filters import Filter
    from prompt_toolkit.history import History


log = logging.getLogger(__name__)


class HistoryAutoSuggest(AutoSuggest):
    """Suggest line completions from a :class:`History` object."""

    def __init__(self, history: History) -> None:
        """Set the kernel instance in initialization."""
        self.history = history
        self.calculate_similarity = lru_cache(maxsize=1024)(self._calculate_similarity)

        self.n_texts = 0
        self.n_lines = 0
        self.prefix_dict: dict[str, dict[str, list[dict[str, int]]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def process_history(self) -> None:
        """Process the entire history and store in prefix_dict."""
        texts = self.history._loaded_strings
        if texts := texts[: len(texts) - self.n_texts]:
            n_lines = self.n_lines
            prefix_dict = self.prefix_dict
            for i, text in enumerate(reversed(texts)):
                for line in text.strip().splitlines():
                    n_lines += 1
                    line = line.strip()
                    for j in range(1, len(line)):
                        prefix, suffix = line[:j], line[j:]
                        prefix_dict[prefix][suffix].append(
                            {"index": -1 - i, "line": n_lines}
                        )
                        # for k in range(1, len(prefix)):
                        #     prefix_dict[prefix[-k:]] = prefix_dict[prefix]
            self.n_lines = n_lines
            self.n_texts += len(texts)

    def _calculate_similarity(self, text_1: str, text_2: str) -> float:
        """Calculate and cache the similarity between two texts."""
        return SequenceMatcher(None, text_1, text_2).quick_ratio()

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        """Get a line completion suggestion."""
        self.process_history()

        line = document.current_line.lstrip()
        if not line:
            return None

        suffixes = self.prefix_dict[line]

        texts = self.history._loaded_strings
        n_lines = self.n_lines

        best_score = 0.0
        best_suffix = ""

        # Rank candidates
        max_count = max([1, *(len(x) for x in suffixes.values())])
        for suffix, instances in suffixes.items():
            count = len(instances)
            for instance in instances:
                text = texts[instance["index"]]
                context_similarity = self.calculate_similarity(document.text, text)
                score = (
                    0
                    # Similarity of prefix to line
                    # 0.333 * len(line) / len(match.group("prefix"))
                    # NUmber of instances in history
                    + 0.3 * count / max_count
                    # Recentness
                    + 0.3 * instance["line"] / n_lines
                    # Similarity of context to document
                    + 0.4 * context_similarity
                )
                # log.debug("%s %r", score, suffix)
                if score > 0.95:
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
