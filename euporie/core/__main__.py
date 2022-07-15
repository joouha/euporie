"""Main entry point into euporie.core."""


def main(name: "str" = "core") -> "None":
    """Loads and launches the application."""
    from importlib.metadata import entry_points

    entry = {entry.name: entry for entry in entry_points(group="euporie.apps")}.get(
        name
    )
    if entry:
        return entry.load().launch()
    else:
        raise Exception(f"Euporie app `{name}` not installed")


if __name__ == "__main__":
    main()
