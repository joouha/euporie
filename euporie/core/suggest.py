"""Suggests line completions from kernel history."""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

from prompt_toolkit.auto_suggest import AutoSuggest, ConditionalAutoSuggest, Suggestion
from prompt_toolkit.filters import to_filter

if TYPE_CHECKING:
    from typing import Deque, Optional, Union

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.document import Document
    from prompt_toolkit.filters import Filter
    from prompt_toolkit.history import History

    from euporie.core.kernel import Kernel

log = logging.getLogger(__name__)


class HistoryAutoSuggest(AutoSuggest):
    """Suggests line completions from a :class:`History` object."""

    def __init__(self, history: "History", cache_size: "int" = 100_000) -> "None":
        """Sets the kernel instance in initialization."""
        self.history = history

        self.cache_size = cache_size
        self.cache_keys: "Deque[str]" = deque()
        self.cache: "dict[str, Suggestion]" = {}

    def get_suggestion(
        self, buffer: "Buffer", document: "Document"
    ) -> Suggestion | None:
        """Get a line completion suggestion."""
        result: "Optional[Suggestion]" = None
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

    def lookup_suggestion(self, line: "str") -> "Optional[Suggestion]":
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

    '''
    def lookup_suggestion(self, line: "str") -> "Optional[Suggestion]":
         ""Suggest most commonly used line."""
        results = {}
        pat = re.compile(f"^\\s*{re.escape(line)}(.*)$", re.MULTILINE)
        for text in self.history.get_strings():
            if line in text:
                for hist_line in text.splitlines()[::-1]:
                    hist_line = hist_line.strip()
                    if hist_line.startswith(line):
                        # Return from the match to end from the history line
                        suggestion = hist_line[len(line) :]
                        if suggestion not in results:
                            results[suggestion] = 1
                        else:
                            results[suggestion] += 1
        return Suggestion(
            {b: a for a, b in results.items()}[max(results.values())]
        )
    '''


class KernelAutoSuggest(AutoSuggest):
    """Suggests line completions from kernel history."""

    def __init__(self, kernel: "Kernel") -> "None":
        """Sets the kernel instance in initialization."""
        self.kernel = kernel

    def get_suggestion(
        self, buffer: "Buffer", document: "Document"
    ) -> Suggestion | None:
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
