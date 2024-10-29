"""Define a dummy application."""

from euporie.core.app.app import BaseApp
from euporie.core.layout.containers import DummyContainer


class DummyApp(BaseApp):
    """An empty application which does nothing."""

    def load_container(self) -> DummyContainer:
        """Load a dummy container as the root container."""
        return DummyContainer()
