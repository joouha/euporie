"""Launch the euporie notebook application."""


def main() -> None:
    """Call the main entrypoint to the application."""
    from euporie.notebook.app import NotebookApp

    NotebookApp.launch()


if __name__ == "__main__":
    main()
