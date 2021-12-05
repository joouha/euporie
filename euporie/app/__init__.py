# -*- coding: utf-8 -*-
from euporie.config import config

if config.dump:
    from euporie.app.dump import DumpApp as App
else:
    from euporie.app.tui import TuiApp as App
