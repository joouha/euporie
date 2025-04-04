"""Custom validators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.validation import ValidationError, Validator

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from euporie.core.kernel.base import BaseKernel


class KernelValidator(Validator):
    """Validate kernel input using a kernel code completeness call."""

    def __init__(self, kernel: BaseKernel) -> None:
        """Initialize the validator."""
        self.kernel = kernel

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
