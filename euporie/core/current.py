"""Allow access to the current running application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import _current_app_session

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.app import BaseApp


def get_app() -> BaseApp:
    """Get the current active (running) Application."""
    session = _current_app_session.get()
    if session.app is not None:
        return session.app

    # Use a baseapp as our "DummyApplication"
    from euporie.core.app import BaseApp

    return BaseApp()
