import logging
from abc import ABCMeta, abstractmethod
from weakref import WeakKeyDictionary

from euporie.widgets.display import Display

log = logging.getLogger(__name__)


class Comm(metaclass=ABCMeta):
    """A base-class for all comm objects, which support syncing traits with the kernel."""

    def __init__(self, nb: "Notebook", comm_id: "str", data: "dict") -> "None":
        self.nb = nb
        self.comm_id = comm_id
        self.data = data

        self.views = WeakKeyDictionary()

    @abstractmethod
    def process_data(self, data):
        ...

    def _create_view(self, cell: "Cell"):
        return Display(self.comm_id, format_="ansi")

    def create_view(self, cell: "Cell") -> "AnyContainer":
        view = self._create_view(cell)
        self.views[view] = cell
        return view

    def update_view(self, container):
        pass

    def update_views(self):
        for container, cell in self.views.items():
            self.update_view(cell, container)
            cell.trigger_refresh(now=False)
        self.nb.app.invalidate()


class UnimplementedComm(Comm):
    ...
