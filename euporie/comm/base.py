import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from prompt_toolkit.utils import Event

from euporie.widgets.display import Display

log = logging.getLogger(__name__)


class Comm(metaclass=ABCMeta):
    """A base-class for all comm objects, which support syncing traits with the kernel."""

    def __init__(
        self, nb: "Notebook", comm_id: "str", data: "dict", buffers: "List[memoryview]"
    ) -> "None":
        self.nb = nb
        self.comm_id = comm_id
        self.data = {}
        self.buffers = []
        self.views = WeakKeyDictionary()
        self.process_data(data, buffers)

    @abstractmethod
    def process_data(self, data, buffers: "List[memoryview]"):
        ...

    def create_view(self, cell: "Cell"):
        return Display(f"[Object cannot be rendered]", format_="ansi")

    def new_view(self, cell: "Cell") -> "AnyContainer":
        view = self.create_view(cell)
        self.views[view] = cell
        return view

    def update_views(self, changes):
        for view, cell in self.views.items():
            view.update(changes)
            cell.trigger_refresh(now=False)
        self.nb.app.invalidate()


class UnimplementedComm(Comm):
    ...


class CommView:
    """Holds a container and methods to update its attributes."""

    def __init__(
        self,
        container: "AnyContainer",
        setters: "Optional[Dict[str, Tuple[Object, str]]" = None,
    ):
        self.container = container
        self.setters = setters or {}

    def update(self, changes: "Dict[str, Any]") -> "None":
        for key, value in changes.items():
            if setter := self.setters.get(key):
                setter(value)

    def __pt_container__(self):
        return self.container
