"""Launch the euporie hub application."""


def main() -> None:
    """Call the main entrypoint to the application."""
    from euporie.hub.app import HubApp

    HubApp.launch()


if __name__ == "__main__":
    main()
