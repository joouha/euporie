"""Define a dummy application."""

from euporie.apptk.layout.containers import DummyContainer
from euporie.core.app.app import BaseApp


class DummyApp(BaseApp):
    """An empty application which does nothing."""

    def load_container(self) -> DummyContainer:
        """Load a dummy container as the root container."""
        return DummyContainer()
