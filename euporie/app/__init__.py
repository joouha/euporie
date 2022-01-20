"""Load the app class to use depending on the configuration."""

from typing import TYPE_CHECKING

from euporie.config import config

if TYPE_CHECKING:
    from typing import Callable, Type

    from euporie.app.base import EuporieApp


App: "Type[EuporieApp]"
get_app: "Callable[[], EuporieApp]"

if config.dump:
    from euporie.app.current import get_dump_app as get_app  # noqa F811
    from euporie.app.dump import DumpApp

    App = DumpApp
else:
    from euporie.app.current import get_tui_app as get_app  # noqa F811
    from euporie.app.tui import TuiApp

    App = TuiApp

__all__ = ["App", "get_app"]
