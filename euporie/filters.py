"""Defines common filters."""

from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, emacs_insert_mode, vi_insert_mode

from euporie.app.current import get_tui_app as get_app
from euporie.key_binding.micro_state import InputMode

__all__ = [
    "cursor_in_leading_ws",
    "has_suggestion",
    "tab_has_focus",
    "notebook_has_focus",
    "cell_has_focus",
    "cell_is_code",
    "cell_is_markdown",
    "micro_mode",
    "micro_replace_mode",
    "micro_insert_mode",
    "micro_recording_macro",
    "is_returnable",
    "cursor_at_start_of_line",
    "insert_mode",
]


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
def tab_has_focus() -> "bool":
    """Determine if there is a currently focused tab."""
    return get_app().tab is not None


@Condition
def notebook_has_focus() -> "bool":
    """Determine if there is a currently focused notebook."""
    return get_app().notebook is not None


@Condition
def cell_has_focus() -> "bool":
    """Determine if there is a currently focused cell."""
    return get_app().cell is not None


@Condition
def cell_is_code() -> "bool":
    """Determine if the current cell is a code cell."""
    cell = get_app().cell
    if cell is None:
        return False
    return cell.json.get("cell_type") == "code"


@Condition
def cell_is_markdown() -> "bool":
    """Determine if the current cell is a markdown cell."""
    cell = get_app().cell
    if cell is None:
        return False
    return cell.json.get("cell_type") == "markdown"


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
    return get_app().current_buffer.document.current_line_before_cursor == ""


"""Determine if any binding style is in insert mode"""
insert_mode = vi_insert_mode | emacs_insert_mode | micro_insert_mode
