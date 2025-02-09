"""Define common filters."""

from __future__ import annotations

import os
from functools import cache, partial, reduce
from importlib.util import find_spec
from shutil import which
from typing import TYPE_CHECKING

# from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import (
    Condition,
    emacs_insert_mode,
    emacs_mode,
    has_completions,
    to_filter,
    vi_insert_mode,
    vi_mode,
    vi_replace_mode,
)

from euporie.core.key_binding.micro_state import MicroInputMode

if TYPE_CHECKING:
    from prompt_toolkit.filters import Filter
    from prompt_toolkit.layout.containers import Window


@cache
def command_exists(*cmds: str) -> Filter:
    """Verify a list of external commands exist on the system."""
    filters = [
        Condition(partial(lambda x: bool(which(cmd)), cmd))  # noqa: B023
        for cmd in cmds
    ]
    return reduce(lambda a, b: a & b, filters, to_filter(True))


@cache
def have_modules(*modules: str) -> Filter:
    """Verify a list of python modules are importable."""

    def try_import(module: str) -> bool:
        loader = find_spec(module)
        return loader is not None

    filters = [Condition(partial(try_import, module)) for module in modules]
    return reduce(lambda a, b: a & b, filters, to_filter(True))


# Determine if euporie is running inside a multiplexer.
in_screen = to_filter(os.environ.get("TERM", "").startswith("screen"))
in_tmux = to_filter(os.environ.get("TMUX") is not None)
in_mplex = in_tmux | in_screen


@Condition
def cursor_in_leading_ws() -> bool:
    """Determine if the cursor of the current buffer is in leading whitespace."""
    from prompt_toolkit.application.current import get_app

    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


@Condition
def cursor_at_end_of_line() -> bool:
    """Determine if the cursor of the current buffer is in leading whitespace."""
    from prompt_toolkit.application.current import get_app

    return get_app().current_buffer.document.is_cursor_at_the_end_of_line


@Condition
def has_suggestion() -> bool:
    """Determine if the current buffer can display a suggestion."""
    from prompt_toolkit.application.current import get_app

    app = get_app()
    return (
        app.current_buffer.suggestion is not None
        and len(app.current_buffer.suggestion.text) > 0
        and app.current_buffer.document.is_cursor_at_the_end_of_line
    )


@Condition
def has_tabs() -> bool:
    """Filter to show if any tabs are open in an app."""
    from euporie.core.app.current import get_app

    return bool(get_app().tabs)


@Condition
def has_dialog() -> bool:
    """Determine if a dialog is being displayed."""
    from prompt_toolkit.layout.containers import ConditionalContainer

    from euporie.core.app.current import get_app

    app = get_app()
    for dialog in app.dialogs.values():
        if isinstance(dialog.content, ConditionalContainer) and dialog.content.filter():
            return True
    return False


@Condition
def has_menus() -> bool:
    """Determine if a menu is being displayed."""
    from prompt_toolkit.layout.containers import ConditionalContainer

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
    from euporie.core.app.current import get_app
    from euporie.core.bars import BAR_BUFFERS

    return get_app().current_buffer.name in BAR_BUFFERS


@Condition
def tab_has_focus() -> bool:
    """Determine if there is a currently focused tab."""
    from euporie.core.app.current import get_app

    return get_app().tab is not None


@Condition
def kernel_tab_has_focus() -> bool:
    """Determine if there is a focused kernel tab."""
    from euporie.core.app.current import get_app
    from euporie.core.tabs.kernel import KernelTab

    return isinstance(get_app().tab, KernelTab)


@cache
def tab_type_has_focus(tab_class_path: str) -> Condition:
    """Determine if the focused tab is of a particular type."""
    from pkgutil import resolve_name

    from euporie.core.app.current import get_app

    tab_class = cache(resolve_name)

    return Condition(lambda: isinstance(get_app().tab, tab_class(tab_class_path)))


@Condition
def tab_can_save() -> bool:
    """Determine if the current tab can save it's contents."""
    from euporie.core.app.current import get_app
    from euporie.core.tabs.base import Tab

    return (
        tab := get_app().tab
    ) is not None and tab.__class__.write_file != Tab.write_file


@Condition
def pager_has_focus() -> bool:
    """Determine if there is a currently focused notebook."""
    from euporie.core.app.current import get_app

    app = get_app()
    pager = app.pager
    if pager is not None:
        return app.layout.has_focus(pager)
    return False


@Condition
def display_has_focus() -> bool:
    """Determine if there is a currently focused cell."""
    from euporie.core.app.current import get_app
    from euporie.core.widgets.display import DisplayControl

    return isinstance(get_app().layout.current_control, DisplayControl)


@Condition
def buffer_is_empty() -> bool:
    """Determine if the current buffer contains nothing."""
    from euporie.core.app.current import get_app

    return not get_app().current_buffer.text


@Condition
def buffer_is_code() -> bool:
    """Determine if the current buffer contains code."""
    from euporie.core.app.current import get_app

    return get_app().current_buffer.name == "code"


@Condition
def buffer_is_markdown() -> bool:
    """Determine if the current buffer contains markdown."""
    from euporie.core.app.current import get_app

    return get_app().current_buffer.name == "markdown"


@Condition
def micro_mode() -> bool:
    """When the micro key-bindings are active."""
    from euporie.core.app.app import ExtraEditingMode
    from euporie.core.app.current import get_app

    return get_app().editing_mode == ExtraEditingMode.MICRO


@Condition
def micro_replace_mode() -> bool:
    """Determine if the editor is in overwrite mode."""
    from euporie.core.app.current import get_app

    app = get_app()
    return app.micro_state.input_mode == MicroInputMode.REPLACE


@Condition
def micro_insert_mode() -> bool:
    """Determine if the editor is in insert mode."""
    from euporie.core.app.current import get_app

    app = get_app()
    return app.micro_state.input_mode == MicroInputMode.INSERT


@Condition
def micro_recording_macro() -> bool:
    """Determine if a micro macro is being recorded."""
    from euporie.core.app.current import get_app

    return get_app().micro_state.current_recording is not None


@Condition
def is_returnable() -> bool:
    """Determine if the current buffer has an accept handler."""
    from euporie.core.app.current import get_app

    return get_app().current_buffer.is_returnable


@Condition
def cursor_at_start_of_line() -> bool:
    """Determine if the cursor is at the start of a line."""
    from euporie.core.app.current import get_app

    return get_app().current_buffer.document.cursor_position_col == 0


@Condition
def cursor_on_first_line() -> bool:
    """Determine if the cursor is on the first line of a buffer."""
    from euporie.core.app.current import get_app

    return get_app().current_buffer.document.on_first_line


@Condition
def cursor_on_last_line() -> bool:
    """Determine if the cursor is on the last line of a buffer."""
    from euporie.core.app.current import get_app

    return get_app().current_buffer.document.on_last_line


@cache
def char_after_cursor(char: str) -> Condition:
    """Generate a condition to check for a character after the cursor."""
    from euporie.core.app.current import get_app

    return Condition(
        lambda: bool(
            (post := get_app().current_buffer.document.text_after_cursor)
            and post[0] == char
        )
    )


@Condition
def has_matching_bracket() -> bool:
    """Determine if the bracket at the cursor has a matching pair."""
    from euporie.core.app.current import get_app

    return bool(get_app().current_buffer.document.find_matching_bracket_position())


"""Determine if any binding style is in insert mode."""
insert_mode = (
    (vi_mode & vi_insert_mode)
    | (emacs_mode & emacs_insert_mode)
    | (micro_mode & micro_insert_mode)
)

"""Determine if any binding style is in replace mode."""
replace_mode = micro_replace_mode | vi_replace_mode


@Condition
def is_searching() -> bool:
    """Determine if the app is in search mode."""
    from euporie.core.app.current import get_app

    app = get_app()
    return (
        app.search_bar is not None and app.search_bar.control in app.layout.search_links
    )


@Condition
def at_end_of_buffer() -> bool:
    """Determine if the cursor is at the end of the current buffer."""
    from prompt_toolkit.application.current import get_app

    buffer = get_app().current_buffer
    return buffer.cursor_position == len(buffer.text)


@Condition
def kernel_is_python() -> bool:
    """Determine if the current notebook has a python kernel."""
    from euporie.core.app.current import get_app
    from euporie.core.tabs.kernel import KernelTab

    kernel_tab = get_app().tab
    if isinstance(kernel_tab, KernelTab):
        return kernel_tab.language == "python"
    return False


@Condition
def multiple_cells_selected() -> bool:
    """Determine if there is more than one selected cell."""
    from euporie.core.app.current import get_app
    from euporie.core.tabs.notebook import BaseNotebook

    nb = get_app().tab
    if isinstance(nb, BaseNotebook):
        return len(nb.selected_indices) > 1
    return False


def scrollable(window: Window) -> Filter:
    """Return a filter which indicates if a window is scrollable."""
    return Condition(
        lambda: (
            window.render_info is not None
            and window.render_info.content_height > window.render_info.window_height
        )
    )
