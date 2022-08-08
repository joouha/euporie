"""Contains a registry of Comm target classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core.comm.base import UnimplementedComm
from euporie.core.comm.ipywidgets import open_comm_ipywidgets

if TYPE_CHECKING:
    from typing import Any, Sequence

    from euporie.core.comm.base import Comm, KernelTab

TARGET_CLASSES = {"jupyter.widget": open_comm_ipywidgets}


def open_comm(
    comm_container: "KernelTab",
    content: "dict[str, Any]",
    buffers: "Sequence[bytes]",
) -> "Comm":
    """Creates a new object respsenting a Comm.

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
    return TARGET_CLASSES.get(target_name, UnimplementedComm)(
        comm_container=comm_container,
        comm_id=str(content.get("comm_id")),
        data=content.get("data", {}),
        buffers=buffers,
    )
