"""Test the Comm base classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, call, patch

import pytest
from prompt_toolkit.layout.containers import Window

from euporie.core.comm.base import Comm, CommView, UnimplementedComm
from euporie.core.tabs.base import KernelTab
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    pass


class MockOutputParent:
    """An output's parent."""

    kernel_tab = Mock(spec=KernelTab)

    def refresh(self, now: bool = True) -> None:
        """Update the parent container."""
        pass


@pytest.fixture
def comm() -> UnimplementedComm:
    """Create an `UnimplementedComm` instance of the `Comm` class."""
    comm_container = Mock(spec=KernelTab)
    comm_id = "1234"
    data = {"key": "value"}
    buffers = [b"buffer1", b"buffer2"]
    return UnimplementedComm(comm_container, comm_id, data, buffers)


class TestCommView:
    """`CommView` creation."""

    def test_init(self) -> None:
        """Attributes are set correctly."""
        # Create a CommView instance with a mocked container and setters
        container = Window()
        setters = {"key1": Mock(), "key2": Mock()}
        view = CommView(container, setters=setters)

        # Check the attributes are set correctly
        assert view.container == container
        assert view.setters == setters
        assert view.kernel is None

    def test_update(self) -> None:
        """Appropriate setter functions are called with the expected value."""
        # Create a CommView instance with a mocked container and setters
        container = Window()
        setters = {"key1": Mock(), "key2": Mock()}
        view = CommView(container, setters=setters)

        # Call the update method with a changes dictionary
        changes = {"key1": "new_value1", "key3": "new_value3"}
        view.update(changes)

        # Check that the setter functions for key1 are called with the expected value
        assert setters["key1"].call_count == 1
        assert setters["key1"].call_args[0] == ("new_value1",)

        # Check that the setter function for key2 is not called
        assert setters["key2"].call_count == 0

    def test_pt_container(self) -> None:
        """The `pt_container` magic method outputs the container argument."""
        # Create a CommView instance with a mocked container
        container = Window()
        view = CommView(container)

        # Call the __pt_container__ method and check the output
        assert view.__pt_container__() == container


class TestComm:
    """Comm class functionality."""

    def test_init(self, comm: Comm) -> None:
        """Initialize the Comm class and its properties."""
        assert isinstance(comm, Comm)
        assert comm.comm_container is not None
        assert comm.comm_id == "1234"
        assert comm.data == {"key": "value"}
        assert comm.buffers == [b"buffer1", b"buffer2"]

    def test_create_view(self, comm: Comm) -> None:
        """Create a CommView instance."""
        parent = Mock(spec=MockOutputParent)
        view = comm.create_view(parent)
        assert isinstance(view, CommView)
        assert isinstance(view.container, Display)
        assert view.container.format_ == "ansi"

    def test_new_view(self, comm: Comm) -> None:
        """Create a new CommView instance."""
        parent = Mock(spec=MockOutputParent)
        view = comm.new_view(parent)
        assert comm.views[view] == parent

    def test_update_views(self, comm: Comm) -> None:
        """Create a new CommView instance."""
        parent = Mock(spec=MockOutputParent)
        with patch.object(CommView, "update"):
            view = comm.new_view(parent)
            changes = {"key": "value"}
            comm.update_views(changes)
            assert cast("Mock", view.update).call_args_list == [call(changes)]
        parent.refresh.assert_called_once()

    def test_process_data(self, comm: Comm) -> None:
        """Processe data and buffers."""
        data = {"key_2": "value_2"}
        buffers = [b"buffer3", b"buffer4"]
        comm.process_data(data, buffers)
        assert comm.data == {"key_2": "value_2"}
        assert comm.buffers == [b"buffer3", b"buffer4"]
