"""Define input history loaders."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.history import History

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Iterable

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
