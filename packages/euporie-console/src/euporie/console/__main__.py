"""Launch the euporie console application."""


def main() -> None:
    """Call the main entrypoint to the application."""
    from euporie.console.app import ConsoleApp

    ConsoleApp.launch()


if __name__ == "__main__":
    main()
