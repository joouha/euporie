"""Contains commands for tabs."""

from __future__ import annotations

import logging

from euporie.apptk.application.current import get_app

from euporie.apptk.commands import add_cmd
from euporie.apptk.filters import (
    buffer_has_focus,
)
from euporie.apptk.filters.app import display_has_focus
from euporie.apptk.filters.buffer import buffer_is_code, buffer_is_empty
from euporie.core.filters import (
    kernel_tab_has_focus,
    tab_can_save,
    tab_has_focus,
    tab_type_has_focus,
)
from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


@add_cmd(filter=tab_can_save, aliases=["w"], keys=["c-s"])
def _save_file(path: str = "") -> None:
    """Save the current file."""
    if (tab := get_app().tab) is not None:
        from upath import UPath

        try:
            tab._save(UPath(path) if path else None)
        except NotImplementedError:
            pass


@add_cmd(aliases=["wq", "x"])
def _save_and_quit(path: str = "") -> None:
    """Save the current tab then quits euporie."""
    app = get_app()
    if (tab := app.tab) is not None:
        from upath import UPath

        try:
            tab.save(UPath(path) if path else None)
        except NotImplementedError:
            pass

    app.exit()


@add_cmd(
    keys=["A-s"],
    menu_title="Save As…",
    filter=tab_can_save,
)
def _save_as(path: str = "") -> None:
    """Save the current file at a new location."""
    if path:
        _save_file(path)
    else:
        app = get_app()
        if dialog := app.get_dialog("save-as"):
            dialog.show(tab=app.tab)


@add_cmd(
    keys=["f5"],
    aliases=["reset-tab"],
    filter=tab_has_focus,
    title="Refresh the current tab",
)
def _refresh_tab() -> None:
    """Reload the tab contents and reset the tab."""
    if (tab := get_app().tab) is not None:
        tab.reset()


@add_cmd(
    bindings=[
        {
            "keys": [("i", "i")],
            "filter": kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
        },
        {
            "filter": buffer_is_code
            & buffer_is_empty
            & tab_type_has_focus("euporie.core.tabs.console:BaseConsole"),
            "keys": ["c-c", "<sigint>"],
        },
    ]
)
def _interrupt_kernel() -> None:
    """Interrupt the notebook's kernel."""
    if isinstance(kt := get_app().tab, KernelTab):
        kt.interrupt_kernel()


@add_cmd(
    keys=[("0", "0")],
    filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _restart_kernel() -> None:
    """Restart the notebook's kernel."""
    if isinstance(kt := get_app().tab, KernelTab):
        kt.restart_kernel()
