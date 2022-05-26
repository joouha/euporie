"""Contains a registry of Comm target classes."""
from typing import TYPE_CHECKING

from euporie.comm.base import UnimplementedComm
from euporie.comm.ipywidgets import open_comm_ipywidgets

if TYPE_CHECKING:
    from typing import Any, Dict, Sequence

    from euporie.comm.base import Comm
    from euporie.tabs.notebook import KernelNotebook

TARGET_CLASSES = {"jupyter.widget": open_comm_ipywidgets}


def open_comm(
    nb: "KernelNotebook", content: "Dict[str, Any]", buffers: "Sequence[bytes]"
) -> "Comm":
    """Creates a new object respsenting a Comm.

    The class used to represent the Comm is determined by the "target_class" given in
    the ``comm_open`` message.

    Args:
        nb: The notebook this comm belongs to
        content: The content of the ``comm_open`` message
        buffers: A list of binary data buffers sent with the ``comm_open`` message

    Returns:
        A class representing the comm

    """
    target_name = content.get("target_name", "")
    return TARGET_CLASSES.get(target_name, UnimplementedComm)(
        nb=nb,
        comm_id=str(content.get("comm_id")),
        data=content.get("data", {}),
        buffers=buffers,
    )
