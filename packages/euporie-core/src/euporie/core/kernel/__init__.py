"""Concerns the interaction with kernels."""

from __future__ import annotations

from importlib.util import find_spec
from pkgutil import resolve_name
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any, Literal

    from euporie.core.kernel.base import BaseKernel, KernelInfo, MsgCallbacks
    from euporie.core.tabs.kernel import KernelTab

KERNEL_REGISTRY = {
    "none": "euporie.core.kernel.base:NoKernel",
    "local": "euporie.core.kernel.local:LocalPythonKernel",
}
if find_spec("jupyter_client"):
    KERNEL_REGISTRY["jupyter"] = "euporie.core.kernel.jupyter:JupyterKernel"


def list_kernels() -> Generator[KernelInfo]:
    """Get specifications for all available kernel types.

    Returns:
        A dictionary mapping kernel type names to their specifications.
    """
    for type_path in KERNEL_REGISTRY.values():
        yield from resolve_name(type_path).variants()


def create_kernel(
    type_name: Literal["jupyter", "local"],
    kernel_tab: KernelTab,
    default_callbacks: MsgCallbacks | None = None,
    allow_stdin: bool = False,
    **kwargs: Any,
) -> BaseKernel:
    """Create and return appropriate kernel instance."""
    type_path = KERNEL_REGISTRY.get(type_name)
    if type_path is not None:
        type_class = resolve_name(type_path)
        return type_class(
            kernel_tab=kernel_tab,
            default_callbacks=default_callbacks,
            allow_stdin=allow_stdin,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown kernel type: {type_name}")
