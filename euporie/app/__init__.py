# -*- coding: utf-8 -*-
"""Load the app class to use depending on the configuration."""
from euporie.config import config

if config.dump:
    from euporie.app.dump import DumpApp as App
else:
    from euporie.app.tui import TuiApp as App

__all__ = ["App"]
