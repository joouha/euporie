"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncGenerator, Iterable

from prompt_toolkit.completion.base import CompleteEvent, Completer, Completion

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from euporie.core.kernel import Kernel

log = logging.getLogger(__name__)


class KernelCompleter(Completer):
    """A prompt_toolkit completer which provides completions from a Jupyter kernel."""

    def __init__(self, kernel: Kernel) -> None:
        """Instantiate the completer for a given notebook.

        Args:
            kernel: A `Notebook` instance

        """
        self.kernel = kernel

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Doe nothing as completions are retrieved asynchronously."""
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        """Retrieve completions from a :class:`Kernel`."""
        for kwargs in await self.kernel.complete_(
            code=document.text,
            cursor_pos=document.cursor_position,
        ):
            if completion_type := kwargs.get("display_meta"):
                completion_type = completion_type.replace(" ", "-")
                kwargs["style"] = f"class:completion-{completion_type}"
            yield Completion(**kwargs)
