"""Define common filters."""

from __future__ import annotations

import os

# from euporie.apptk.enums import EditingMode
from euporie.apptk.filters import (
    to_filter,
)

# Determine if euporie is running inside a multiplexer.
in_screen = to_filter(os.environ.get("TERM", "").startswith("screen"))
in_tmux = to_filter(os.environ.get("TMUX") is not None)
in_mplex = in_tmux | in_screen
