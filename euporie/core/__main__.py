"""Main entry point into euporie.core."""

import importlib


def main() -> "None":
    """Loads and launches the application."""
    from euporie.core.config import config

    # Load the configuration
    config.load()
    # Import the configured app
    mod_name, _, class_name = config.app.rpartition(".")
    App = getattr(importlib.import_module(mod_name), class_name)
    # Launch the app
    App.launch()


if __name__ == "__main__":
    main()
