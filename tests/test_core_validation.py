"""Ensure the kernel validator works as expected."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from euporie.core.validation import KernelValidator

if TYPE_CHECKING:
    from euporie.core.kernel import Kernel


@pytest.fixture
def kernel() -> Kernel:
    """Return a mock kernel object."""
    return Mock()


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
    kernel.is_complete_ = AsyncMock(return_value={"status": "incomplete"})

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
    kernel.is_complete_ = AsyncMock(return_value={"status": "complete"})

    await validator.validate_async(document)  # Should not raise ValidationError
