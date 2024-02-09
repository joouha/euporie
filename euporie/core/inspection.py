"""Show contextual help for the current item under the cursor."""

from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable, Sequence

    from prompt_toolkit.document import Document

    from euporie.core.kernel import Kernel
    from euporie.core.lsp import LspClient


class Inspector(metaclass=ABCMeta):
    """A class which provides contextual help on the item under the cursor."""

    @abstractmethod
    async def get_context(self, document: Document, auto: bool) -> dict[str, Any]:
        """Call to retrieve the contextual help."""
        ...


class KernelInspector(Inspector):
    """Inspector which retrieves contextual help from a Jupyter kernel."""

    def __init__(self, kernel: Kernel) -> None:
        """Initialize a new inspector which queries a Jupyter kernel."""
        self.kernel = kernel

    async def get_context(self, document: Document, auto: bool) -> dict[str, Any]:
        """Request contextual help from the kernel."""
        return await self.kernel.inspect_(document.text, document.cursor_position)


class LspInspector(Inspector):
    """Inspector which retrieves contextual help from a Language Server."""

    def __init__(self, lsp: LspClient, path: Path) -> None:
        """Initialize a new inspector which queries a Jupyter kernel."""
        self.lsp = lsp
        self.path = path

    async def get_context(self, document: Document, auto: bool) -> dict[str, Any]:
        """Request hover info from an LSP servers."""
        return await self.lsp.hover_(
            path=self.path,
            line=document.cursor_position_row,
            char=document.cursor_position_col,
        )


class FirstInspector(Inspector):
    """Return results of the first inspector to response."""

    def __init__(
        self, inspectors: Sequence[Inspector] | Callable[[], Sequence[Inspector]]
    ) -> None:
        """Initialize a new inspector which queries a Jupyter kernel."""
        self.inspectors = inspectors

    async def get_context(self, document: Document, auto: bool) -> dict[str, Any]:
        """Request hover info from an LSP servers."""
        inspectors = self.inspectors() if callable(self.inspectors) else self.inspectors

        for ready in asyncio.as_completed(
            [inspector.get_context(document, auto) for inspector in inspectors]
        ):
            if result := (await ready):
                return result
        return {}
