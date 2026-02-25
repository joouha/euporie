"""Main entry point into euporie.core."""

from __future__ import annotations


def main() -> None:
    """Call the main entrypoint to the application."""
    from euporie.core.app.launch import LaunchApp

    LaunchApp.launch()


if __name__ == "__main__":
    main()
