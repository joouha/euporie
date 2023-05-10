"""Tests for Comm registry."""

from __future__ import annotations

from unittest.mock import Mock

from euporie.core.comm.base import UnimplementedComm
from euporie.core.comm.ipywidgets import IpyWidgetComm
from euporie.core.comm.registry import TARGET_CLASSES, open_comm
from euporie.core.tabs.base import KernelTab


def test_open_comm_ipywidgets() -> None:
    """`open_comm_ipywidgets` returns an instance of IpyWidgetComm."""
    comm_container = Mock(KernelTab)
    content = {
        "target_name": "jupyter.widget",
        "comm_id": "123",
        "data": {},
        "buffers": [],
    }
    result = open_comm(comm_container, content, [])
    assert isinstance(result, IpyWidgetComm)


def test_open_comm_with_target_class() -> None:
    """`open_comm` returns an instance of the specified target class."""

    class TestComm(UnimplementedComm):
        pass

    TARGET_CLASSES["test.target"] = TestComm
    comm_container = Mock(KernelTab)
    content = {
        "target_name": "test.target",
        "comm_id": "123",
        "data": {},
        "buffers": [],
    }
    result = open_comm(comm_container, content, [])
    assert isinstance(result, TestComm)
    del TARGET_CLASSES["test.target"]


def test_open_comm_with_no_target_class() -> None:
    """`open_comm` returns an UnimplementedComm when no target class specified."""
    comm_container = Mock(KernelTab)
    content = {"comm_id": "123", "data": {}, "buffers": []}
    result = open_comm(comm_container, content, [])
    assert isinstance(result, UnimplementedComm)
