"""Main entry point into euporie.core."""

from __future__ import annotations

from functools import cache
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint, EntryPoints


@cache
def available_apps() -> dict[str, EntryPoint]:
    """Return a list of loadable euporie apps."""
    eps: dict | EntryPoints
    try:
        eps = entry_points(group="euporie.apps")
    except TypeError:
        eps = entry_points()
    if isinstance(eps, dict):
        points = eps.get("euporie.apps")
    else:
        points = eps.select(group="euporie.apps")
    apps = {x.name: x for x in points} if points else {}
    return apps


def main(name: str = "launch") -> None:
    """Load and launches the application."""
    # Monkey-patch prompt_toolkit
    from euporie.core.layout import containers  # noqa: F401

    apps = available_apps()
    if entry := apps.get(name):
        return entry.load().launch()
    else:
        raise ModuleNotFoundError(f"Euporie app `{name}` not installed")


if __name__ == "__main__":
    main()
