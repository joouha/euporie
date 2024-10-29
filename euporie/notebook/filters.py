"""Define filters used in the notebook app."""

from __future__ import annotations

from prompt_toolkit.filters import Condition

from euporie.core.app.current import get_app


@Condition
def notebook_has_focus() -> bool:
    """Determine if there is a currently focused notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    return isinstance(get_app().tab, Notebook)


@Condition
def deleted_cells() -> bool:
    """Determine if there ares cell in the undo buffer."""
    from euporie.notebook.tabs.notebook import Notebook

    nb = get_app().tab
    if isinstance(nb, Notebook):
        return bool(nb.undo_buffer)
    return False


@Condition
def code_cell_selected() -> bool:
    """Determine if a code cell is selected."""
    from euporie.notebook.tabs.notebook import Notebook

    nb = get_app().tab
    if isinstance(nb, Notebook):
        for cell in nb.cells:
            if cell.cell_type == "code":
                return True
    return False


@Condition
def cell_has_focus() -> bool:
    """Determine if there is a currently focused cell."""
    from euporie.notebook.tabs.notebook import Notebook

    nb = get_app().tab
    if isinstance(nb, Notebook):
        return nb.cell is not None
    return False


@Condition
def in_edit_mode() -> bool:
    """Determine if there is a currently focused notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    nb = get_app().tab
    if isinstance(nb, Notebook):
        return nb.edit_mode
    return False
