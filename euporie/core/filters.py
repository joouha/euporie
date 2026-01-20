"""Define common filters."""

from __future__ import annotations

from functools import cache

from euporie.apptk.application.current import get_app

from euporie.apptk.filters import (
    Condition,
    has_completions,
)


@Condition
def has_tabs() -> bool:
    """Filter to show if any tabs are open in an app."""
    return bool(get_app().tabs)


@Condition
def has_dialog() -> bool:
    """Determine if a dialog is being displayed."""
    from euporie.apptk.layout.containers import ConditionalContainer

    app = get_app()
    for dialog in app.dialogs.values():
        if isinstance(dialog.content, ConditionalContainer) and dialog.content.filter():
            return True
    return False


@Condition
def has_menus() -> bool:
    """Determine if a menu is being displayed."""
    from euporie.apptk.layout.containers import ConditionalContainer
    from euporie.notebook.current import get_app

    app = get_app()
    for menu in app.menus.values():
        if isinstance(menu.content, ConditionalContainer) and menu.content.filter():
            return True
    return False


has_float = has_dialog | has_menus | has_completions


@Condition
def has_toolbar() -> bool:
    """Is there an active toolbar?"""
    from euporie.core.bars import BAR_BUFFERS

    return get_app().current_buffer.name in BAR_BUFFERS


@Condition
def tab_has_focus() -> bool:
    """Determine if there is a currently focused tab."""
    return get_app().tab is not None


@Condition
def kernel_tab_has_focus() -> bool:
    """Determine if there is a focused kernel tab."""
    from euporie.core.tabs.kernel import KernelTab

    return isinstance(get_app().tab, KernelTab)


@cache
def tab_type_has_focus(tab_class_path: str) -> Condition:
    """Determine if the focused tab is of a particular type."""
    from pkgutil import resolve_name

    tab_class = cache(resolve_name)

    return Condition(lambda: isinstance(get_app().tab, tab_class(tab_class_path)))


@Condition
def tab_can_save() -> bool:
    """Determine if the current tab can save it's contents."""
    from euporie.core.tabs.base import Tab

    return (
        tab := get_app().tab
    ) is not None and tab.__class__.write_file != Tab.write_file


@Condition
def pager_has_focus() -> bool:
    """Determine if there is a currently focused notebook."""
    app = get_app()
    pager = app.pager
    if pager is not None:
        return app.layout.has_focus(pager)
    return False


@Condition
def kernel_is_python() -> bool:
    """Determine if the current notebook has a python kernel."""
    from euporie.core.tabs.kernel import KernelTab

    kernel_tab = get_app().tab
    if isinstance(kernel_tab, KernelTab):
        return kernel_tab.language == "python"
    return False


@Condition
def multiple_cells_selected() -> bool:
    """Determine if there is more than one selected cell."""
    from euporie.core.tabs.notebook import BaseNotebook

    nb = get_app().tab
    if isinstance(nb, BaseNotebook):
        return len(nb.selected_indices) > 1
    return False
