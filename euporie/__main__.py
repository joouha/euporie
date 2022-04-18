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

    # If on a dumb terminal, the TUI app won't work, so dump and notebooks instead
    if not config.dump:
        is_dumb_term = os.environ.get("TERM") == "dumb"
        have_tty = sys.stdin.isatty() or sys.stderr.isatty()
        # If interaction is not supported but dumping was not asked for, dump and page
        if is_dumb_term or not have_tty:
            config.defaults["dump"] = True
            config.defaults["page"] = True

    if config.dump:

        from euporie.app.dump import DumpApp

        App = DumpApp
    elif config.hub:
        from euporie.app.hub import HubApp

        App = HubApp
    else:
        from euporie.app.tui import TuiApp

        App = TuiApp

    App.launch()


if __name__ == "__main__":
    main()
