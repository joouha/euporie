"""Custom validators."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.validation import ValidationError, Validator

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompt_toolkit.document import Document

    from euporie.core.kernel.base import BaseKernel

log = logging.getLogger(__name__)


class KernelValidator(Validator):
    """Validate kernel input using a kernel code completeness call."""

    def __init__(self, kernel: BaseKernel | Callable[[], BaseKernel]) -> None:
        """Initialize the validator."""
        self._kernel = kernel

    @property
    def kernel(self) -> BaseKernel:
        """Get the current kernel instance."""
        if callable(self._kernel):
            return self._kernel()
        else:
            return self._kernel

    def validate(self, document: Document) -> None:
        """Validate the input synchronously."""
        completeness_status = self.kernel.is_complete(source=document.text).get(
            "status", "unknown"
        )
        if completeness_status == "incomplete":
            raise ValidationError

    async def validate_async(self, document: Document) -> None:
        """Return a `Future` which is set when the validation is ready."""
        completeness_status = (
            await self.kernel.is_complete_async(source=document.text)
        ).get("status", "unknown")
        if completeness_status == "incomplete":
            raise ValidationError
        return
