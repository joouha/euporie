"""Test completions."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

from prompt_toolkit.completion import CompleteEvent, Completion
from prompt_toolkit.document import Document

from euporie.core.completion import KernelCompleter
from euporie.core.kernel.base import BaseKernel


def test_kernel_completer_init() -> None:
    """The kernel completer saves a reference to the passed kernel on init."""
    kernel = Mock(spec=BaseKernel)
    completer = KernelCompleter(kernel)
    assert completer.kernel == kernel


def test_kernel_completer_get_completions() -> None:
    """The synchronous "get_completions" method yields nothing."""
    kernel = Mock(spec=BaseKernel)
    completer = KernelCompleter(kernel)
    document = Document("print(", cursor_position=6)
    completions = list(completer.get_completions(document, CompleteEvent()))
    assert not completions


def test_kernel_completer_get_completions_async() -> None:
    """The asynchronous "get_completions" method yields completions."""

    async def mock_complete_async(
        source: str, cursor_pos: int, timeout: int = 60
    ) -> list[dict]:
        return [{"text": "print"}]

    kernel = Mock(spec=BaseKernel, complete_async=mock_complete_async)
    completer = KernelCompleter(kernel)
    document = Document("prin", cursor_position=4)

    async def get_results() -> list[Completion]:
        return [
            result
            async for result in completer.get_completions_async(
                document, CompleteEvent()
            )
        ]

    completions = asyncio.run(get_results())

    assert list(completions) == [
        Completion(
            text="print",
            start_position=0,
            display=[("", "print")],
        )
    ]
