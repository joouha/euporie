"""Main entry point into euporie.core."""


def main(name: "str" = "launch") -> "None":
    """Load and launches the application."""
    from importlib.metadata import entry_points

    # Register extensions to external packages
    from euporie.core import (
        path,  # noqa F401
        pygments,  # noqa F401
    )

    # Monkey-patch prompt_toolkit
    from euporie.core.layout import containers  # noqa: F401

    eps = entry_points()  # group="euporie.apps")
    if isinstance(eps, dict):
        points = eps.get("euporie.apps")
    else:
        points = eps.select(group="euporie.apps")
    apps = {x.name: x for x in points} if points else {}

    if entry := apps.get(name):
        return entry.load().launch()
    else:
        raise Exception(f"Euporie app `{name}` not installed")


if __name__ == "__main__":
    main()
