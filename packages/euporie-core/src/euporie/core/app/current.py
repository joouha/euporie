"""Allow access to the current running application."""

from __future__ import annotations

from functools import cache
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from euporie.apptk.application.current import _current_app_session

if TYPE_CHECKING:
    from euporie.core.app.app import BaseApp

    from importlib.metadata import EntryPoint, EntryPoints

APP_ALIASES: dict[str, str] = {"edit": "notebook"}


@cache
def available_apps() -> dict[str, str]:
    """Return a list of loadable euporie apps from console_scripts."""

    eps: dict | EntryPoints
    try:
        eps = entry_points(group="console_scripts")
    except TypeError:
        eps = entry_points()
    if isinstance(eps, dict):
        points = eps.get("console_scripts", [])
    else:
        points = eps.select(group="console_scripts")

    apps: dict[str, EntryPoint] = {}
    for ep in points:
        # Match euporie-* console scripts
        if ep.name.startswith("euporie-"):
            app_name = ep.name.removeprefix("euporie-")
            apps[app_name] = ep.value

    # Add aliases
    for alias, app in APP_ALIASES.items():
        apps[alias] = apps[app]

    return apps


def get_app() -> BaseApp:
    """Get the current active (running) Application."""
    from euporie.core.app.app import BaseApp

    session = _current_app_session.get()
    if isinstance(session.app, BaseApp):
        return session.app

    # Create a dummy application if we really need one
    from euporie.core.app.dummy import DummyApp

    return DummyApp()
