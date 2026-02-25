"""Define common filters."""

from __future__ import annotations

from functools import cache

from prompt_toolkit.filters.base import Condition

__all__ = [
    "at_end_of_buffer",
    "buffer_is_code",
    "buffer_is_empty",
    "buffer_is_markdown",
    "buffer_name_is",
    "char_after_cursor",
    "cursor_at_end_of_line",
    "cursor_at_start_of_line",
    "cursor_in_leading_ws",
    "cursor_on_first_line",
    "cursor_on_last_line",
    "has_matching_bracket",
    "has_suggestion",
    "is_returnable",
]


@Condition
def cursor_in_leading_ws() -> bool:
    """Determine if the cursor of the current buffer is in leading whitespace."""
    from euporie.apptk.application.current import get_app

    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


@Condition
def cursor_at_end_of_line() -> bool:
    """Determine if the cursor of the current buffer is in leading whitespace."""
    from euporie.apptk.application.current import get_app

    return get_app().current_buffer.document.is_cursor_at_the_end_of_line


@Condition
def has_suggestion() -> bool:
    """Determine if the current buffer can display a suggestion."""
    from euporie.apptk.application.current import get_app

    app = get_app()
    return (
        app.current_buffer.suggestion is not None
        and len(app.current_buffer.suggestion.text) > 0
        and app.current_buffer.document.is_cursor_at_the_end_of_line
    )


@Condition
def buffer_is_empty() -> bool:
    """Determine if the current buffer contains nothing."""
    from prompt_toolkit.application.current import get_app

    return not get_app().current_buffer.text


@cache
def buffer_name_is(name: str) -> Condition:
    """Determine if the focused tab is of a particular type."""
    from prompt_toolkit.application.current import get_app

    return Condition(lambda: get_app().current_buffer.name == name)


@Condition
def buffer_is_code() -> bool:
    """Determine if the current buffer contains code."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.name == "code"


@Condition
def buffer_is_markdown() -> bool:
    """Determine if the current buffer contains markdown."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.name == "markdown"


@Condition
def is_returnable() -> bool:
    """Determine if the current buffer has an accept handler."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.is_returnable


@Condition
def cursor_at_start_of_line() -> bool:
    """Determine if the cursor is at the start of a line."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.document.cursor_position_col == 0


@Condition
def cursor_on_first_line() -> bool:
    """Determine if the cursor is on the first line of a buffer."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.document.on_first_line


@Condition
def cursor_on_last_line() -> bool:
    """Determine if the cursor is on the last line of a buffer."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.document.on_last_line


@cache
def char_after_cursor(char: str) -> Condition:
    """Generate a condition to check for a character after the cursor."""
    from prompt_toolkit.application.current import get_app

    return Condition(
        lambda: bool(
            (post := get_app().current_buffer.document.text_after_cursor)
            and post[0] == char
        )
    )


@Condition
def has_matching_bracket() -> bool:
    """Determine if the bracket at the cursor has a matching pair."""
    from prompt_toolkit.application.current import get_app

    return bool(get_app().current_buffer.document.find_matching_bracket_position())


@Condition
def at_end_of_buffer() -> bool:
    """Determine if the cursor is at the end of the current buffer."""
    from euporie.apptk.application.current import get_app

    buffer = get_app().current_buffer
    return buffer.cursor_position == len(buffer.text)
