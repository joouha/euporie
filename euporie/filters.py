"""Defines common filters."""

import os

from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import (
    Condition,
    emacs_insert_mode,
    to_filter,
    vi_insert_mode,
)

from euporie.app.current import get_tui_app as get_app
from euporie.key_binding.micro_state import InputMode

__all__ = [
    "code_cell_selected",
    "have_formatter",
    "have_black",
    "have_isort",
    "have_ssort",
    "cursor_in_leading_ws",
    "has_suggestion",
    "has_menus",
    "has_dialog",
    "tab_has_focus",
    "notebook_has_focus",
    "cell_has_focus",
    "cell_output_has_focus",
    "cell_is_code",
    "cell_is_markdown",
    "micro_mode",
    "micro_replace_mode",
    "micro_insert_mode",
    "micro_recording_macro",
    "multiple_cells_selected",
    "is_returnable",
    "cursor_at_start_of_line",
    "cursor_on_first_line",
    "cursor_on_last_line",
    "insert_mode",
    "kernel_is_python",
]


# Determine if black is available
try:
    import black  # type: ignore  # noqa F401
except ModuleNotFoundError:
    have_black = to_filter(False)
else:
    have_black = to_filter(True)

# Determine if isort is available
try:
    import isort  # type: ignore  # noqa F401
except ModuleNotFoundError:
    have_isort = to_filter(False)
else:
    have_isort = to_filter(True)

# Determine if ssort is available
try:
    import ssort  # type: ignore  # noqa F401
except ModuleNotFoundError:
    have_ssort = to_filter(False)
else:
    have_ssort = to_filter(True)

# Determine if we have at least one formatter
have_formatter = have_black | have_isort | have_ssort

# Determine if euporie is running inside tmux.
in_tmux = to_filter(os.environ.get("TMUX") is not None)


@Condition
def cursor_in_leading_ws() -> "bool":
    """Determine if the cursor of the current buffer is in leading whitespace."""
    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


@Condition
def has_suggestion() -> "bool":
    """Determine if the current buffer can display a suggestion."""
    app = get_app()
    return (
        app.current_buffer.suggestion is not None
        and len(app.current_buffer.suggestion.text) > 0
        and app.current_buffer.document.is_cursor_at_the_end_of_line
    )


@Condition
def has_dialog() -> "bool":
    """Determine if a dialog is being displayed."""
    return get_app().has_dialog


@Condition
def has_menus() -> "bool":
    """Determine if a dialog is being displayed."""
    app = get_app()
    if hasattr(app, "menu_container"):
        return app.layout.current_window == app.menu_container.window
    else:
        return False


@Condition
def tab_has_focus() -> "bool":
    """Determine if there is a currently focused tab."""
    return get_app().tab is not None


@Condition
def notebook_has_focus() -> "bool":
    """Determine if there is a currently focused notebook."""
    return get_app().notebook is not None


@Condition
def pager_has_focus() -> "bool":
    """Determine if there is a currently focused notebook."""
    app = get_app()
    notebook = app.notebook
    if notebook is not None:
        return app.layout.has_focus(notebook.pager_content)
    return False


@Condition
def cell_has_focus() -> "bool":
    """Determine if there is a currently focused cell."""
    return get_app().cell is not None


@Condition
def multiple_cells_selected() -> "bool":
    """Determine if there is more than one selected cell."""
    nb = get_app().notebook
    if nb is not None:
        return len(nb.page.selected_indices) > 1
    return False


@Condition
def cell_output_has_focus() -> "bool":
    """Determine if there is a currently focused cell."""
    from euporie.output.control import OutputControl

    return isinstance(get_app().layout.current_control, OutputControl)


@Condition
def code_cell_selected() -> "bool":
    """Determine if a code cell is selected."""
    nb = get_app().notebook
    if nb is not None:
        for cell in nb.cells:
            if cell.cell_type == "code":
                return True
    return False


@Condition
def cell_is_code() -> "bool":
    """Determine if the current cell is a code cell."""
    cell = get_app().cell
    if cell is None:
        return False
    return cell.cell_type == "code"


@Condition
def cell_is_markdown() -> "bool":
    """Determine if the current cell is a markdown cell."""
    cell = get_app().cell
    if cell is None:
        return False
    return cell.cell_type == "markdown"


@Condition
def micro_mode() -> "bool":
    """When the micro key-bindings are active."""
    return get_app().editing_mode == EditingMode.MICRO  # type: ignore


@Condition
def micro_replace_mode() -> "bool":
    """Determine if the editor is in overwrite mode."""
    app = get_app()
    return app.micro_state.input_mode == InputMode.REPLACE


@Condition
def micro_insert_mode() -> "bool":
    """Determine if the editor is in insert mode."""
    app = get_app()
    return app.micro_state.input_mode == InputMode.INSERT


@Condition
def micro_recording_macro() -> "bool":
    """Determine if a micro macro is being recorded."""
    return get_app().micro_state.current_recording is not None


@Condition
def is_returnable() -> "bool":
    """Determine if the current buffer has an accept handler."""
    return get_app().current_buffer.is_returnable


@Condition
def cursor_at_start_of_line() -> "bool":
    """Determine if the cursor is at the start of a line."""
    return get_app().current_buffer.document.cursor_position_col == 0


@Condition
def cursor_on_first_line() -> "bool":
    """Determine if the cursor is on the first line of a buffer."""
    return get_app().current_buffer.document.on_first_line


@Condition
def cursor_on_last_line() -> "bool":
    """Determine if the cursor is on the last line of a buffer."""
    return get_app().current_buffer.document.on_last_line


@Condition
def kernel_is_python() -> "bool":
    """Determine if the current notebook has a python kernel."""
    notebook = get_app().notebook
    return (
        notebook is not None
        and notebook.json.get("metadata", {}).get("kernelspec", {}).get("language")
        == "python"
    )


"""Determine if any binding style is in insert mode"""
insert_mode = vi_insert_mode | emacs_insert_mode | micro_insert_mode
