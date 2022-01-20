"""Contains the main class for a notebook file."""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Iterable

from prompt_toolkit.completion.base import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from euporie.kernel import NotebookKernel

__all__ = ["KernelCompleter"]

log = logging.getLogger(__name__)


class KernelCompleter(Completer):
    """A prompt_toolkit completer which provides completions from a Jupyter kernel."""

    def __init__(self, kernel: NotebookKernel) -> None:
        """Instantiate the completer for a given notebook.

        Args:
            kernel: A `Notebook` instance

        """
        self.kernel = kernel

    def get_completions(
        self, document: "Document", complete_event: "CompleteEvent"
    ) -> "Iterable[Completion]":
        """Does nothing as completions are retrieved asynchronously."""
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> "AsyncGenerator[Completion, None]":
        """Retrieves completions from a :class:`NotebookKernel`."""
        for kwargs in await self.kernel.complete_(
            code=document.text,
            cursor_pos=document.cursor_position,
        ):
            if completion_type := kwargs.get("display_meta"):
                kwargs["style"] = f"class:completion-menu.completion.{completion_type}"
                kwargs[
                    "selected_style"
                ] = f"class:completion-menu.completion.current.{completion_type}"
            yield Completion(**kwargs)
