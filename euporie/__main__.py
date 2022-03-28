"""Main entry point into euporie."""
import os
import sys
from typing import Type


def main() -> "None":
    """Loads and launches the application."""
    from euporie.app.base import EuporieApp
    from euporie.config import config

    config.load()

    App: "Type[EuporieApp]"

    is_dumb_term = os.environ.get("TERM") == "dumb"
    if is_dumb_term and not config.dump:
        config.defaults["page"] = True
    if is_dumb_term:
        config.defaults["dump"] = True
    if not config.dump and not sys.stdin.isatty() and not sys.stderr.isatty():
        config.defaults["dump"] = True

    # If on a dumb terminal, the TUI app won't work, so dump and notebooks instead
    if config.dump:

        from euporie.app.dump import DumpApp

        App = DumpApp
    else:
        from euporie.app.tui import TuiApp

        App = TuiApp

    App.launch()


if __name__ == "__main__":
    main()
