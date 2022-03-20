"""Main entry point into euporie."""
from typing import Type


def main() -> "None":
    """Loads and launches the application."""
    from euporie.app.base import EuporieApp
    from euporie.config import config

    config.load()

    App: "Type[EuporieApp]"

    if config.dump:
        from euporie.app.dump import DumpApp

        App = DumpApp
    else:
        from euporie.app.tui import TuiApp

        App = TuiApp

    App.launch()


if __name__ == "__main__":
    main()
