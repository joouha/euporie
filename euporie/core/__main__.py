"""Main entry point into euporie.core."""


def main(name: "str" = "launch") -> "None":
    """Load and launches the application."""
    from importlib.metadata import entry_points

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
