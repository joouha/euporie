# -*- coding: utf-8 -*-
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition, emacs_insert_mode, vi_insert_mode

from euporie.key_binding.micro_state import InputMode


@Condition
def cursor_in_leading_ws() -> "bool":
    """Determine if the cursor of the current buffer is in leading whitespace."""
    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


@Condition
def has_suggestion() -> "bool":
    app = get_app()
    return (
        app.current_buffer.suggestion is not None
        and len(app.current_buffer.suggestion.text) > 0
        and app.current_buffer.document.is_cursor_at_the_end_of_line
    )


@Condition
def tab_has_focus() -> "bool":
    return get_app().tab is not None


@Condition
def notebook_has_focus() -> "bool":
    return get_app().notebook is not None


@Condition
def cell_has_focus() -> "bool":
    return get_app().cell is not None


@Condition
def cell_in_edit_mode() -> "bool":
    return get_app().cell is not None


@Condition
def cell_is_code() -> "bool":
    return get_app().cell.json.get("cell_type") == "code"


@Condition
def micro_mode() -> "bool":
    "When the micro key-bindings are active."
    return get_app().editing_mode == "MICRO"


@Condition
def micro_replace_mode() -> "bool":
    "When the editor is in insert mode."
    app = get_app()
    return app.micro_state.input_mode == InputMode.REPLACE


@Condition
def micro_insert_mode() -> "bool":
    "When the editor is in insert mode."
    app = get_app()
    return app.micro_state.input_mode == InputMode.INSERT


@Condition
def micro_recording_macro() -> "bool":
    return app.micro_state.current_recording is not None


@Condition
def is_returnable() -> "bool":
    return get_app().current_buffer.is_returnable


@Condition
def cursor_at_start_of_line() -> "bool":
    return get_app().current_buffer.document.current_line_before_cursor == ""


insert_mode = vi_insert_mode | emacs_insert_mode | micro_insert_mode
