"""Launch the euporie preview application."""


def main() -> None:
    """Call the main entrypoint to the application."""
    from euporie.preview.app import PreviewApp

    PreviewApp.launch()


if __name__ == "__main__":
    main()
