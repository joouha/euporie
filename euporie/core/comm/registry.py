"""Contain a registry of Comm target classes."""

from __future__ import annotations

from pkgutil import resolve_name
from typing import TYPE_CHECKING

from euporie.core.comm.base import UnimplementedComm

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

    from euporie.core.comm.base import Comm, KernelTab

TARGET_CLASSES: dict[str, str] = {
    "jupyter.widget": "euporie.core.comm.ipywidgets:open_comm_ipywidgets"
}


def open_comm(
    comm_container: KernelTab,
    content: dict[str, Any],
    buffers: Sequence[bytes],
) -> Comm:
    """Create a new object respsenting a Comm.

    The class used to represent the Comm is determined by the "target_class" given in
    the ``comm_open`` message.

    Args:
        comm_container: The notebook this comm belongs to
        content: The content of the ``comm_open`` message
        buffers: A list of binary data buffers sent with the ``comm_open`` message

    Returns:
        A class representing the comm

    """
    target_name = content.get("target_name", "")
    if path := TARGET_CLASSES.get(target_name):
        TargetClass: Callable[[KernelTab, str, dict, Sequence[bytes]], Comm] = (
            resolve_name(path)
        )
    else:
        TargetClass = UnimplementedComm
    return TargetClass(
        # comm_container=
        comm_container,
        # comm_id=
        str(content.get("comm_id")),
        # data=
        content.get("data", {}),
        # buffers=
        buffers,
    )
