"""Main entry point into euporie.core."""


def main(name: "str" = "launch") -> "None":
    """Loads and launches the application."""
    from importlib.metadata import entry_points

    for entry in entry_points()["euporie.apps"]:
        if entry.name == name:
            return entry.load().launch()
    else:
        raise Exception(f"Euporie app `{name}` not installed")


if __name__ == "__main__":
    main()
