"""Tests for ipywidget implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, call, patch

import pytest

from euporie.core.comm.ipywidgets import (
    WIDGET_MODELS,
    IpyWidgetComm,
    UnimplementedModel,
    _separate_buffers,
)
from euporie.core.kernel.jupyter import JupyterKernel
from euporie.core.tabs.kernel import KernelTab
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    from collections.abc import Generator

    from euporie.core.widgets.cell_outputs import OutputParent


@pytest.fixture
def kernel_tab() -> KernelTab:
    """Create a `Mock` instance of the `KernelTab` class.

    Returns:
        A `Mock` instance of the `KernelTab` class.
    """
    kt = Mock(spec=KernelTab)
    kt.kernel = Mock(spec=JupyterKernel)
    return kt


@pytest.fixture
def output_parent(kernel_tab: KernelTab) -> OutputParent:
    """Create a mocked parent for a comm view."""

    class MockOutputParent:
        """An output's parent."""

        kernel_tab = kernel_tab

        def refresh(self, now: bool = True) -> None:
            """Update the parent container."""

    return MockOutputParent()


@pytest.fixture
def icomm(kernel_tab: KernelTab) -> Generator[IpyWidgetComm, None, None]:
    """Create an `UnimplementedModel` instance of the `IpyWidgetComm` class.

    Args:
        kernel_tab: A `KernelTab` instance to use for the `IpyWidgetComm` object.

    Returns:
        An `UnimplementedModel` instance of the `IpyWidgetComm` class.
    """
    with patch.object(IpyWidgetComm, "update_views"):
        yield UnimplementedModel(kernel_tab, "test_comm_id", {}, [])


def test_separate_buffers() -> None:
    """Removes binary types from dicts and lists while keeping track of their paths."""
    test_state = {
        "a": memoryview(b"test"),
        "b": [bytearray(b"test1"), {"c": b"test2"}],
        "d": "string",
    }
    path: list[str | int] = ["x"]
    buffer_paths: list[list[str | int]] = []
    buffers: list[memoryview | bytearray | bytes] = []
    result = _separate_buffers(test_state, path, buffer_paths, buffers)
    assert result == {"b": [None, {}], "d": "string"}
    assert buffer_paths == [["x", "a"], ["x", "b", 0], ["x", "b", 1, "c"]]
    assert len(buffers) == 3
    assert all(isinstance(b, (memoryview, bytearray, bytes)) for b in buffers)


class TestIpyWidgetComm:
    """Test functionality of IpyWidgetComm."""

    def test_init(self, icomm: IpyWidgetComm) -> None:
        """An instance of IpyWidgetComm can be created successfully."""
        assert isinstance(icomm, IpyWidgetComm)

    def test_init_subclass(self) -> None:
        """A subclass of IpyWidgetComm is added to the registry when it is created."""

        class MyWidgetModel(IpyWidgetComm):
            pass

        assert MyWidgetModel.__name__ in WIDGET_MODELS

    def test_set_state(self, icomm: IpyWidgetComm) -> None:
        """The `_state` and `sync` attributes are set."""
        icomm.set_state(key="key", value="value")
        assert icomm.data["state"]["key"] == "value"

    def test_process_data(self, icomm: IpyWidgetComm) -> None:
        """Functionality of the `process_data` method."""
        data = {
            "state": {"key_1": "value_1", "key_3": {"nested_key_1": "nested_value"}},
            "buffer_paths": [["key_2"], ["key_3", "nested_key_2"]],
        }
        buffers = [b"buffer_1", b"buffer_2"]
        icomm.process_data(data, buffers)

        # Assert that buffers are added to data
        assert icomm.buffers == buffers
        assert icomm.data == {
            "state": {
                "key_1": "value_1",
                "key_2": b"buffer_1",
                "key_3": {"nested_key_1": "nested_value", "nested_key_2": b"buffer_2"},
            },
            "buffer_paths": data["buffer_paths"],
        }

        # Test with update method
        icomm.data["state"] = {"key_1": "value_1"}
        changes = {"key_1": "new_value", "key_2": "value_2"}
        data = {"method": "update", "state": changes}
        icomm.process_data(data, [])
        assert icomm.data["state"] == {"key_1": "new_value", "key_2": "value_2"}
        assert cast("Mock", icomm.update_views).call_args_list == [call(changes)]

    def test_get_embed_state(self, icomm: IpyWidgetComm) -> None:
        """The embedded output is a dictionary with the expected values."""
        # Set widget state to mock data
        icomm.data = {
            "state": {
                "_model_name": "test",
                "_model_module": "mymodule",
                "_model_module_version": "1.0.0",
                "value_1": "string",
                "value_2": b"bytes",
                "value_3": {"value_4": 1234},
            }
        }
        expected_output_state = {
            "_model_name": "test",
            "_model_module": "mymodule",
            "_model_module_version": "1.0.0",
            "value_1": "string",
            "value_3": {"value_4": 1234},
            "buffers": [
                {"encoding": "base64", "path": ["value_2"], "data": "Ynl0ZXM="}
            ],
        }

        # Call the _get_embed_state method and check the output
        output = icomm._get_embed_state()

        assert isinstance(output, dict)
        assert output["model_name"] == "test"
        assert output["model_module"] == "mymodule"
        assert output["model_module_version"] == "1.0.0"
        assert output["state"] == expected_output_state
        assert len(output["state"]["buffers"]) == 1


class TestUnimplementedModel:
    """Unimplemented model produces the desired views."""

    def test_create_view(
        self, icomm: UnimplementedModel, output_parent: OutputParent
    ) -> None:
        """`UnimplementedModel` creates a `CommView` with the expected container."""
        # Create an instance of UnimplementedModel and call its create_view method
        view = icomm.create_view(parent=output_parent)

        # Check that the CommView container is a Display widget with the expected text
        assert isinstance(view.container, Display)
        assert view.container.datum.data == "[Widget not implemented]"
        assert view.container.datum.format == "ansi"
