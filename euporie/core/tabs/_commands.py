"""Contains commands for tabs."""

from __future__ import annotations

import logging

from euporie.core.commands import add_cmd
from euporie.core.filters import tab_can_save, tab_has_focus

log = logging.getLogger(__name__)


@add_cmd(filter=tab_can_save, aliases=["w"])
def _save_file(path: str = "") -> None:
    """Save the current file."""
    from euporie.core.app.current import get_app

    if (tab := get_app().tab) is not None:
        from upath import UPath

        try:
            tab._save(UPath(path) if path else None)
        except NotImplementedError:
            pass


@add_cmd(aliases=["wq", "x"])
def _save_and_quit(path: str = "") -> None:
    """Save the current tab then quits euporie."""
    from euporie.core.app.current import get_app

    app = get_app()
    if (tab := app.tab) is not None:
        from upath import UPath

        try:
            tab.save(UPath(path) if path else None)
        except NotImplementedError:
            pass

    app.exit()


@add_cmd(
    menu_title="Save As…",
    filter=tab_can_save,
)
def _save_as(path: str = "") -> None:
    """Save the current file at a new location."""
    if path:
        _save_file(path)
    else:
        from euporie.core.app.current import get_app

        app = get_app()
        if dialog := app.get_dialog("save-as"):
            dialog.show(tab=app.tab)


@add_cmd(filter=tab_has_focus, title="Refresh the current tab")
def _refresh_tab() -> None:
    """Reload the tab contents and reset the tab."""
    from euporie.core.app.current import get_app

    if (tab := get_app().tab) is not None:
        tab.reset()


# Depreciated v2.5.0
@add_cmd(filter=tab_has_focus, title="Reset the current tab")
def _reset_tab() -> None:
    log.warning(
        "The `reset-tab` command was been renamed to `refresh-tab` in v2.5.0,"
        " and will be removed in a future version"
    )
    _refresh_tab()
