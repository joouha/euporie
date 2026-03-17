"""Define input history loaders."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apptk.history import History

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Iterable, Sequence

    from euporie.core.kernel.base import BaseKernel

log = logging.getLogger(__name__)


class KernelHistory(History):
    """Load the kernel's command history."""

    def __init__(
        self, kernel: BaseKernel | Callable[[], BaseKernel], n: int = 1000
    ) -> None:
        """Create a new instance of the kernel history loader."""
        super().__init__()
        self._kernel = kernel
        # How many items to load
        self.n = n
        self.n_loaded = 0
        self.loading = False

    @property
    def kernel(self) -> BaseKernel:
        """Return the current kernel."""
        if callable(self._kernel):
            return self._kernel()
        return self._kernel

    async def load(self) -> AsyncGenerator[str]:
        """Load the history and yield all entries, most recent history first.

        This method can be called multiple times from the `Buffer` to
        repopulate the history when prompting for a new input. So we are
        responsible here for both caching, and making sure that strings that
        were were appended to the history will be incorporated next time this
        method is called.

        Yields:
            Each history string
        """
        if not self.loading and not self._loaded and self.kernel:
            self.loading = True
            items = await self.kernel.history_async(n=self.n, hist_access_type="tail")
            if items:
                self._loaded_strings = [item[2] for item in reversed(items)]
                # Remove sequential duplicates
                self._loaded_strings = [
                    v
                    for i, v in enumerate(self._loaded_strings)
                    if i == 0 or v != self._loaded_strings[i - 1]
                ]
                self._loaded = True
                self.n_loaded = len(self._loaded_strings)
                log.debug(
                    "Loaded %s items from kernel history", len(self._loaded_strings)
                )
            self.loading = False

        for item in self._loaded_strings:
            yield item

    def load_history_strings(self) -> Iterable[str]:
        """Not used to load history, as we load it asynchronously."""
        while False:
            yield

    def store_string(self, string: str) -> None:
        """Don't store strings in persistent storage: they are stored by the kernel."""

    @property
    def recent(self) -> list[str]:
        """Return new items added since history was initially loaded."""
        return self._loaded_strings[: -self.n_loaded]


class StateHistory(History):
    """History class that stores entries in an application state variable.

    This persists buffer history across sessions by reading from and writing to
    a state variable managed by the application's configuration system.

    Args:
        state_key: The attribute name on the application's state object used
            to store history entries.
        max_entries: The maximum number of history entries to retain.
    """

    def __init__(self, state_key: str, max_entries: int = 100) -> None:
        """Create a new instance of the state history loader."""
        super().__init__()
        self.state_key = state_key
        self.max_entries = max_entries

    def _get_state_entries(self) -> list[str]:
        """Read history entries from the application state.

        Returns:
            A list of history strings in chronological order (oldest first).
        """
        from euporie.core.app.current import get_app

        try:
            app = get_app()
        except Exception:
            return []

        entries: Sequence[str] = getattr(app.state, self.state_key, [])
        return list(entries)

    def _set_state_entries(self, entries: list[str]) -> None:
        """Write history entries to the application state.

        Args:
            entries: A list of history strings in chronological order
                (oldest first).
        """
        from euporie.core.app.current import get_app

        try:
            app = get_app()
        except Exception:
            return

        setattr(app.state, self.state_key, entries[-self.max_entries :])

    def load_history_strings(self) -> Iterable[str]:
        """Load history strings from the application state.

        Yields the most recent items first.

        Returns:
            An iterable of history strings, most recent first.
        """
        return reversed(self._get_state_entries())

    def store_string(self, string: str) -> None:
        """Store a string in the application state.

        Appends the string to the state entries and enforces the maximum
        entry limit.

        Args:
            string: The history string to store.
        """
        entries = self._get_state_entries()
        entries.append(string)
        self._set_state_entries(entries)
