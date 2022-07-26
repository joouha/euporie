"""Main entry point into euporie.core."""


def main(name: "str" = "core") -> "None":
    """Loads and launches the application."""
    try:
        from importlib_metadata import entry_points
    except ImportError:
        from importlib.metadata import entry_points

    for entry in entry_points(group="euporie.apps"):
        if entry.name == name:
            return entry.load().launch()
    else:
        raise Exception(f"Euporie app `{name}` not installed")


if __name__ == "__main__":
    main()
