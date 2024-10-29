"""Allow access to the current running application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import _current_app_session

if TYPE_CHECKING:
    from euporie.core.app.app import BaseApp


def get_app() -> BaseApp:
    """Get the current active (running) Application."""
    from euporie.core.app.app import BaseApp

    session = _current_app_session.get()
    if isinstance(session.app, BaseApp):
        return session.app

    # Create a dummy application if we really need one
    from euporie.core.app.dummy import DummyApp

    return DummyApp()


def get_app_cls(name: str) -> BaseApp:
    """Load a euporie app by name."""
    from euporie.core.__main__ import available_apps

    return available_apps()[name].load()
