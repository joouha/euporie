"""Launch the euporie application."""


def main() -> "None":
    """Call the main entrypoint to the application."""
    import sys

    from euporie.core import __main__

    __main__.main(str(sys.modules[__name__].__package__).rpartition(".")[2])


if __name__ == "__main__":
    main()
