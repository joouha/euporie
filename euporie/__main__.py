"""Main entry point into euporie."""

import importlib


def main() -> "None":
    """Loads and launches the application."""
    from euporie.config import config

    config.load()
    mod_name, _, class_name = config.app.rpartition(".")
    App = getattr(importlib.import_module(mod_name), class_name)
    App.launch()


if __name__ == "__main__":
    main()
