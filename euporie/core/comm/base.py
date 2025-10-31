"""Define the base class for a Comm object and it's representation."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from euporie.core.app.current import get_app

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import Any

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.kernel.jupyter import JupyterKernel
    from euporie.core.tabs.kernel import KernelTab
    from euporie.core.widgets.cell_outputs import OutputParent


log = logging.getLogger(__name__)


class CommView:
    """Hold a container and methods to update its attributes."""

    def __init__(
        self,
        container: AnyContainer,
        setters: Mapping[str, Callable[..., None]] | None = None,
    ) -> None:
        """Create a new instance of the Comm vieew.

        Args:
            container: The main container to display when this Comm is to be visualised
            setters: A dictionary mapping state names to callback functions which should
                be called when the named state value changed.
        """
        self.container = container
        self.setters: dict[str, Callable[..., None]] = dict(setters or {})
        self.kernel: JupyterKernel | None = None

    def update(self, changes: dict[str, Any]) -> None:
        """Update the view to reflect changes in the Comm.

        Calls any setter functions defined for the changed keys with the changed values
        as arguments.

        Args:
            changes: A dictionary mapping changed key names to new values.

        """
        for key, value in changes.items():
            if setter := self.setters.get(key):
                setter(value)

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container for display."""
        return self.container


class Comm(metaclass=ABCMeta):
    """A base-class for all comm objects, which support syncing traits with the kernel."""

    def __init__(
        self,
        comm_container: KernelTab,
        comm_id: str,
        data: dict,
        buffers: Sequence[memoryview | bytearray | bytes],
    ) -> None:
        """Create a new instance of the Comm.

        Args:
            comm_container: The container this Comm belongs to
            comm_id: The ID of the Comm
            data: The data field from the ``comm_open`` message
            buffers: The buffers field from the ``comm_open`` message

        """
        self.comm_container = comm_container
        self.comm_id = comm_id
        self.data: dict[str, Any] = {}
        self.buffers: Sequence[bytes] = []
        self.views: WeakKeyDictionary[CommView, OutputParent] = WeakKeyDictionary()
        self.process_data(data, buffers)

    @abstractmethod
    def process_data(self, data: dict, buffers: Sequence[bytes]) -> None:
        """Process a comm_msg data / buffers."""

    def _get_embed_state(self) -> dict:
        return {}

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new :class:`CommView` for this Comm."""
        from euporie.core.convert.datum import Datum
        from euporie.core.widgets.display import Display

        return CommView(Display(Datum("[Object cannot be rendered]", format="ansi")))

    def new_view(self, parent: OutputParent) -> CommView:
        """Create and register a new :class:`CommView` for this Comm."""
        view = self.create_view(parent)
        self.views[view] = parent
        return view

    def update_views(self, changes: dict) -> None:
        """Update all the active views of this Comm."""
        for view, parent in self.views.items():
            view.update(changes)
            parent.refresh(now=False)
        get_app().invalidate()


class UnimplementedComm(Comm):
    """Represent a Comm object which is not implemented in euporie.core."""

    def process_data(self, data: dict, buffers: Sequence[bytes]) -> None:
        """Doe nothing when data is received."""
        self.data = data
        self.buffers = buffers
