# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

from typing import AsyncGenerator, Iterable

from prompt_toolkit.completion.base import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from euporie.kernel import NotebookKernel


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
        """An asynchronous generator of `Completions`, as returned by the kernel."""
        async for kwargs in self.kernel._complete(
            code=document.text,
            cursor_pos=document.cursor_position,
        ):
            if completion_type := kwargs.get("display_meta"):
                kwargs["style"] = f"class:completion-{completion_type}"
                kwargs[
                    "selected_style"
                ] = f"class:completion-selected-{completion_type}"
            yield Completion(**kwargs)
