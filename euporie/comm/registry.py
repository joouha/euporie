from euporie.comm.base import UnimplementedComm
from euporie.comm.ipywidgets import open_comm_ipywidgets

TARGET_CLASSES = {"jupyter.widget": open_comm_ipywidgets}


def open_comm(nb, content) -> "Comm":
    target_name = content.get("target_name")
    return TARGET_CLASSES.get(target_name, UnimplementedComm)(
        nb=nb,
        comm_id=content.get("comm_id"),
        data=content.get("data"),
    )
