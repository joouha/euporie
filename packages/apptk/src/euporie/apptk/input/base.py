"""Define additional dummy input which ignores all input."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.input.base import DummyInput, _dummy_context_manager

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager


log = logging.getLogger(__name__)


class IgnoredInput(DummyInput):
    """An input which ignores input but does not immediately close the app."""

    def attach(
        self, input_ready_callback: Callable[[], None]
    ) -> AbstractContextManager[None]:
        """Do not call the callback, so the input is never closed."""
        return _dummy_context_manager()
