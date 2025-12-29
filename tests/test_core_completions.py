"""Test completions."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

from euporie.apptk.document import Document

from euporie.apptk.completion import CompleteEvent, Completion
from euporie.core.completion import KernelCompleter
from euporie.core.kernel.base import BaseKernel


def test_kernel_completer_init() -> None:
    """The kernel completer saves a reference to the passed kernel on init."""
    kernel = Mock(spec=BaseKernel)
    completer = KernelCompleter(lambda: kernel)
    assert completer.kernel == kernel


def test_kernel_completer_get_completions() -> None:
    """The synchronous "get_completions" method yields nothing."""
    kernel = Mock(spec=BaseKernel)
    completer = KernelCompleter(kernel)
    document = Document("print(", cursor_position=6)
    completions = list(completer.get_completions(document, CompleteEvent()))
    assert not completions


async def test_kernel_completer_get_completions_async() -> None:
    """The asynchronous "get_completions" method yields completions."""
    kernel = AsyncMock(spec=BaseKernel)
    kernel.complete_async = AsyncMock()
    kernel.complete_async.return_value = [{"text": "print"}]
    completer = KernelCompleter(lambda: kernel)
    document = Document("prin", cursor_position=4)

    completions = [
        result
        async for result in completer.get_completions_async(document, CompleteEvent())
    ]

    assert list(completions) == [
        Completion(
            text="print",
            start_position=0,
            display=[("", "print")],
        )
    ]
