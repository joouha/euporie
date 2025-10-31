"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.completion.base import CompleteEvent, Completer, Completion

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Iterable
    from pathlib import Path

    from prompt_toolkit.document import Document

    from euporie.core.kernel.base import BaseKernel
    from euporie.core.lsp import LspClient

log = logging.getLogger(__name__)


class KernelCompleter(Completer):
    """A prompt_toolkit completer which provides completions from a kernel."""

    def __init__(self, kernel: BaseKernel | Callable[[], BaseKernel]) -> None:
        """Instantiate the completer for a given notebook.

        Args:
            kernel: A `Notebook` instance

        """
        self._kernel = kernel

    @property
    def kernel(self) -> BaseKernel:
        """Return the current kernel."""
        if callable(self._kernel):
            return self._kernel()
        return self._kernel

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Do nothing as completions are retrieved asynchronously."""
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion]:
        """Retrieve completions from a :class:`Kernel`."""
        for kwargs in await self.kernel.complete_async(
            source=document.text,
            cursor_pos=document.cursor_position,
        ):
            if completion_type := kwargs.get("display_meta"):
                completion_type = completion_type.replace(" ", "-")
                kwargs["style"] = f"class:completion-{completion_type}"
            yield Completion(**kwargs)


class LspCompleter(Completer):
    """A completer for documents using an LSP."""

    def __init__(self, lsp: LspClient, path: Path) -> None:
        """Instantiate the completer for a given notebook.

        Args:
            lsp: An instance of a client for a LSP server
            path: The path of the file the LSP server will complete
            language: The language of the document

        """
        self.lsp = lsp
        self.path = path

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Do nothing as completions are retrieved asynchronously."""
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion]:
        """Retrieve completions from an LSP server."""
        # Get completions
        text_preceding = document.current_line_before_cursor.lower()
        len_preceding = len(text_preceding)
        start = 0
        for kwargs in await self.lsp.complete_(
            path=self.path,
            line=document.cursor_position_row,
            char=document.cursor_position_col,
        ):
            # Style the completion type
            if completion_type := kwargs.get("display_meta"):
                completion_type = completion_type.replace(" ", "-")
                kwargs["style"] = f"class:completion-{completion_type}"
            # Estimate start position
            if start == 0:
                text_completion = kwargs["text"].lower()
                for i in range(max(len(text_completion), len_preceding)):
                    if text_preceding[-1 - i :] == text_completion[: i + 1]:
                        start = -1 - i
                        break
            # Set the start position
            kwargs["start_position"] = start
            yield Completion(
                text=kwargs["text"],
                start_position=kwargs.get("start_position", 0),
                display=kwargs.get("display"),
                display_meta=kwargs.get("display_meta"),
                style=kwargs.get("style", ""),
                selected_style=kwargs.get("selected_style", ""),
            )


class DeduplicateCompleter(Completer):
    """Asynchronous wrapper around a completer that removes duplicates.

    Only the first unique completions are kept. Completions are considered to be a
    duplicate if they result in the same document text when they would be applied.
    """

    def __init__(self, completer: Completer) -> None:
        """Create a new instance."""
        self.completer = completer

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Do nothing as completions are retrieved asynchronously."""
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion]:
        """Get completions from wrapped completer."""
        # Keep track of the document strings we'd get after applying any completion.
        found_so_far: set[str] = set()

        async for completion in self.completer.get_completions_async(
            document, complete_event
        ):
            text_if_applied = (
                document.text[: document.cursor_position + completion.start_position]
                + completion.text
                + document.text[document.cursor_position :]
            )

            if text_if_applied == document.text:
                # Don't include completions that don't have any effect at all.
                continue

            if text_if_applied in found_so_far:
                continue

            found_so_far.add(text_if_applied)
            yield completion
