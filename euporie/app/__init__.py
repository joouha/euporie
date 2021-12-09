# -*- coding: utf-8 -*-
"""Load the app class to use depending on the configuration."""
from typing import TYPE_CHECKING

from euporie.config import config

if TYPE_CHECKING:
    from typing import Type

    from euporie.app.base import EuporieApp


App: "Type[EuporieApp]"

if config.dump:
    from euporie.app.dump import DumpApp

    App = DumpApp
else:
    from euporie.app.tui import TuiApp

    App = TuiApp

__all__ = ["App"]
