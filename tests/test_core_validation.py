"""Ensure the kernel validator works as expected."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, NonCallableMock

import pytest
from euporie.apptk.document import Document
from euporie.apptk.validation import ValidationError

from euporie.core.validation import KernelValidator

if TYPE_CHECKING:
    from euporie.core.kernel.base import BaseKernel


@pytest.fixture
def kernel() -> BaseKernel:
    """Return a mock kernel object."""
    return NonCallableMock()


def test_validate(kernel: Mock) -> None:
    """Test the validate method of KernelValidator."""
    validator = KernelValidator(kernel)
    document = Document("incomplete code")
    kernel.is_complete.return_value = {"status": "incomplete"}

    with pytest.raises(ValidationError):
        validator.validate(document)


async def test_validate_async(kernel: Mock) -> None:
    """Test the validate_async method of KernelValidator."""
    validator = KernelValidator(kernel)
    document = Document("incomplete code")
    kernel.is_complete_async = AsyncMock(return_value={"status": "incomplete"})

    with pytest.raises(ValidationError):
        await validator.validate_async(document)


def test_validate_complete(kernel: Mock) -> None:
    """Test the validate method of KernelValidator when the code is complete."""
    validator = KernelValidator(kernel)
    document = Document("complete code")
    kernel.is_complete.return_value = {"status": "complete"}

    validator.validate(document)  # Should not raise ValidationError


async def test_validate_async_complete(kernel: Mock) -> None:
    """Test the validate_async method of KernelValidator when the code is complete."""
    validator = KernelValidator(kernel)
    document = Document("complete code")
    kernel.is_complete_async = AsyncMock(return_value={"status": "complete"})

    await validator.validate_async(document)  # Should not raise ValidationError
