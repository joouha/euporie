"""Launch the euporie application."""


def main() -> "None":
    """Call the main entrypoint to the application."""
    from euporie.core import __main__

    __main__.main(__name__.split(".")[1])


if __name__ == "__main__":
    main()
