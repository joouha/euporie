"""Main entry point into euporie.core."""


def main(name: "str" = "launch") -> "None":
    """Load and launches the application."""
    try:
        from importlib.metedata import EntryPoint
    except ModuleNotFoundError:
        EntryPoint = None

    from importlib.metadata import entry_points

    eps = entry_points()  # group="euporie.apps")
    if isinstance(eps, dict):
        apps = {x.name: x for x in eps.get("euporie.apps")}
    else:
        apps = {x.name: x for x in eps.select(group="euporie.apps")}

    if entry := apps.get(name):
        return entry.load().launch()
    else:
        raise Exception(f"Euporie app `{name}` not installed")


if __name__ == "__main__":
    main()
