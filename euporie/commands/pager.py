"""Defines commands for the pager."""

import logging

from euporie.app.current import get_base_app as get_app
from euporie.commands.registry import add
from euporie.filters import pager_has_focus

log = logging.getLogger(__name__)


@add(keys=["escape", "q"], filter=pager_has_focus, group="pager")
def close_pager() -> "None":
    """Close the pager."""
    app = get_app()
    if app.notebook is not None:
        app.notebook.hide_pager()
        previous_control = app.layout.previous_control
        if previous_control in app.layout.find_all_controls():
            app.layout.focus(previous_control)
