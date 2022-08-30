"""Defines custom inputs and outputs, and related methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.input.base import DummyInput, _dummy_context_manager

if TYPE_CHECKING:
    from typing import Callable, ContextManager


class IgnoredInput(DummyInput):
    """An input which ignores input but does not immediately close the app."""

    def attach(
        self, input_ready_callback: "Callable[[], None]"
    ) -> "ContextManager[None]":
        """.Do not call the callback, so the input is never closed."""
        return _dummy_context_manager()
