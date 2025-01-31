"""Concerns the interaction with kernels."""

from typing import Any, Literal

from euporie.core.kernel.base import BaseKernel
from euporie.core.kernel.jupyter import JupyterKernel
from euporie.core.kernel.local import LocalPythonKernel


def create_kernel(
    kernel_type: Literal["jupyter", "local"], **kwargs: Any
) -> BaseKernel:
    """Create and return appropriate kernel instance."""
    if kernel_type == "jupyter":
        return JupyterKernel(**kwargs)
    elif kernel_type == "local":
        return LocalPythonKernel(**kwargs)
    else:
        raise ValueError(f"Unknown kernel type: {kernel_type}")
