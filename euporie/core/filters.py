"""Defines common filters."""

import os
from functools import lru_cache

from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import (
    Condition,
    emacs_insert_mode,
    emacs_mode,
    to_filter,
    vi_insert_mode,
    vi_mode,
    vi_replace_mode,
)

from euporie.core.key_binding.micro_state import MicroInputMode


@Condition
@lru_cache
def have_black() -> "bool":
    """Determine if black is available."""
    try:
        import black.const  # noqa F401
    except ModuleNotFoundError:
        return False
    else:
        return True


@Condition
@lru_cache
def have_isort() -> "bool":
    """Determine if isort is available."""
    try:
        import isort  # noqa F401
    except ModuleNotFoundError:
        return False
    else:
        return True


@Condition
@lru_cache
def have_ssort() -> "bool":
    """Determine if ssort is available."""
    try:
        import ssort  # noqa F401
    except ModuleNotFoundError:
        return False
    else:
        return True


# Determine if we have at least one formatter
have_formatter = have_black | have_isort | have_ssort

# Determine if euporie is running inside tmux.
in_tmux = to_filter(os.environ.get("TMUX") is not None)


@Condition
def cursor_in_leading_ws() -> "bool":
    """Determine if the cursor of the current buffer is in leading whitespace."""
    from prompt_toolkit.application.current import get_app

    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


@Condition
def has_suggestion() -> "bool":
    """Determine if the current buffer can display a suggestion."""
    from prompt_toolkit.application.current import get_app

    app = get_app()
    return (
        app.current_buffer.suggestion is not None
        and len(app.current_buffer.suggestion.text) > 0
        and app.current_buffer.document.is_cursor_at_the_end_of_line
    )


@Condition
def has_dialog() -> "bool":
    """Determine if a dialog is being displayed."""
    from euporie.core.app import get_app

    return get_app().has_dialog


@Condition
def has_menus() -> "bool":
    """Determine if a menu is being displayed."""
    from prompt_toolkit.widgets.menus import MenuContainer

    from euporie.edit.app import get_app

    app = get_app()
    if isinstance(app.layout.container, MenuContainer):
        return app.layout.current_window == app.layout.container.window
    return False


@Condition
def tab_has_focus() -> "bool":
    """Determine if there is a currently focused tab."""
    from euporie.core.app import get_app

    return get_app().tab is not None


@Condition
def notebook_has_focus() -> "bool":
    """Determine if there is a currently focused notebook."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import Notebook

    return isinstance(get_app().tab, Notebook)


@Condition
def in_edit_mode() -> "bool":
    """Determine if there is a currently focused notebook."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import Notebook

    nb = get_app().tab
    if isinstance(nb, Notebook):
        return nb.edit_mode
    return False


@Condition
def pager_has_focus() -> "bool":
    """Determine if there is a currently focused notebook."""
    from euporie.core.app import get_app

    app = get_app()
    pager = app.pager
    if pager is not None:
        return app.layout.has_focus(pager)
    return False


@Condition
def cell_has_focus() -> "bool":
    """Determine if there is a currently focused cell."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import EditNotebook

    nb = get_app().tab
    if isinstance(nb, EditNotebook):
        return nb.cell is not None
    return False


@Condition
def multiple_cells_selected() -> "bool":
    """Determine if there is more than one selected cell."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import EditNotebook

    nb = get_app().tab
    if isinstance(nb, EditNotebook):
        return len(nb.page.selected_indices) > 1
    return False


@Condition
def deleted_cells() -> "bool":
    """Determine if there ares cell in the undo buffer."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import EditNotebook

    nb = get_app().tab
    if isinstance(nb, EditNotebook):
        return bool(nb.undo_buffer)
    return False


@Condition
def display_has_focus() -> "bool":
    """Determine if there is a currently focused cell."""
    from euporie.core.app import get_app
    from euporie.core.widgets.display import DisplayControl

    return isinstance(get_app().layout.current_control, DisplayControl)


@Condition
def code_cell_selected() -> "bool":
    """Determine if a code cell is selected."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import EditNotebook

    nb = get_app().tab
    if isinstance(nb, EditNotebook):
        for cell in nb.cells:
            if cell.cell_type == "code":
                return True
    return False


@Condition
def buffer_is_empty() -> "bool":
    """Determine if the current buffer contains nothing."""
    from euporie.core.app import get_app

    return not get_app().current_buffer.text


@Condition
def buffer_is_code() -> "bool":
    """Determine if the current buffer contains code."""
    from euporie.core.app import get_app

    return get_app().current_buffer.name == "code"


@Condition
def buffer_is_markdown() -> "bool":
    """Determine if the current buffer contains markdown."""
    from euporie.core.app import get_app

    return get_app().current_buffer.name == "code"


@Condition
def micro_mode() -> "bool":
    """When the micro key-bindings are active."""
    from euporie.core.app import get_app

    return get_app().editing_mode == EditingMode.MICRO  # type: ignore


@Condition
def micro_replace_mode() -> "bool":
    """Determine if the editor is in overwrite mode."""
    from euporie.core.app import get_app

    app = get_app()
    return app.micro_state.input_mode == MicroInputMode.REPLACE


@Condition
def micro_insert_mode() -> "bool":
    """Determine if the editor is in insert mode."""
    from euporie.core.app import get_app

    app = get_app()
    return app.micro_state.input_mode == MicroInputMode.INSERT


@Condition
def micro_recording_macro() -> "bool":
    """Determine if a micro macro is being recorded."""
    from euporie.core.app import get_app

    return get_app().micro_state.current_recording is not None


@Condition
def is_returnable() -> "bool":
    """Determine if the current buffer has an accept handler."""
    from euporie.core.app import get_app

    return get_app().current_buffer.is_returnable


@Condition
def cursor_at_start_of_line() -> "bool":
    """Determine if the cursor is at the start of a line."""
    from euporie.core.app import get_app

    return get_app().current_buffer.document.cursor_position_col == 0


@Condition
def cursor_on_first_line() -> "bool":
    """Determine if the cursor is on the first line of a buffer."""
    from euporie.core.app import get_app

    return get_app().current_buffer.document.on_first_line


@Condition
def cursor_on_last_line() -> "bool":
    """Determine if the cursor is on the last line of a buffer."""
    from euporie.core.app import get_app

    return get_app().current_buffer.document.on_last_line


@Condition
def kernel_is_python() -> "bool":
    """Determine if the current notebook has a python kernel."""
    from euporie.core.app import get_app
    from euporie.core.tabs.notebook import Notebook

    nb = get_app().tab
    if isinstance(nb, Notebook):
        return (
            nb is not None
            and nb.json.get("metadata", {}).get("kernelspec", {}).get("language")
            == "python"
        )
    return False


"""Determine if any binding style is in insert mode."""
insert_mode = (
    (vi_mode & vi_insert_mode)
    | (emacs_mode & emacs_insert_mode)
    | (micro_mode & micro_insert_mode)
)

"""Determine if any binding style is in replace mode."""
replace_mode = micro_replace_mode | vi_replace_mode


@Condition
def is_searching() -> "bool":
    """Determine if the app is in search mode."""
    from euporie.core.app import get_app

    app = get_app()
    return (
        app.search_bar is not None and app.search_bar.control in app.layout.search_links
    )


@Condition
def at_end_of_buffer() -> "bool":
    """Determine if the cursor is at the end of the current buffer."""
    from prompt_toolkit.application.current import get_app

    buffer = get_app().current_buffer
    return buffer.cursor_position == len(buffer.text)
