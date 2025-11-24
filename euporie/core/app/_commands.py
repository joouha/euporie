"""Contains commands common to all euporie applications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.filters import buffer_has_focus

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd
from euporie.core.filters import tab_has_focus, tab_type_has_focus

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent


@add_cmd(aliases=["q"])
def _quit() -> None:
    """Quit euporie."""
    get_app().exit()


@add_cmd(aliases=["q!"])
def _force_quit() -> None:
    """Quit euporie without saving any changes."""
    from prompt_toolkit.application.application import Application

    Application.exit(get_app())


@add_cmd(menu_title="Open File…", aliases=["o"], icon="", style="class:purple")
def _open_file(path: str = "") -> None:
    """Open a file."""
    from euporie.core.app.current import get_app

    if path:
        from upath import UPath

        get_app().open_file(UPath(path))
    else:
        if dialog := get_app().get_dialog("open-file"):
            dialog.show()


@add_cmd(aliases=["bc"], filter=tab_has_focus, menu_title="Close File")
def _close_tab() -> None:
    """Close the current tab."""
    get_app().close_tab()


@add_cmd(aliases=["bn"], filter=tab_has_focus)
def _next_tab() -> None:
    """Switch to the next tab."""
    get_app().tab_idx += 1


@add_cmd(aliases=["bp"], filter=tab_has_focus)
def _previous_tab() -> None:
    """Switch to the previous tab."""
    get_app().tab_idx -= 1


@add_cmd(filter=~buffer_has_focus)
def _focus_next() -> None:
    """Focus the next control."""
    get_app().layout.focus_next()


@add_cmd(filter=~buffer_has_focus)
def _focus_previous() -> None:
    """Focus the previous control."""
    get_app().layout.focus_previous()


@add_cmd()
def _clear_screen() -> None:
    """Clear the screen."""
    get_app().renderer.clear()


@add_cmd(hidden=True, aliases=[""])
def _go_to(event: KeyPressEvent, index: int = 0) -> None:
    """Go to a line or cell by number."""
    index = max(0, index - 1)
    if buffer_has_focus():
        buffer = get_app().current_buffer
        buffer.cursor_position = len("".join(buffer.text.splitlines(True)[:index]))
    elif tab_type_has_focus("euporie.notebook.tabs.notebook:Notebook")():
        from euporie.notebook.tabs.notebook import Notebook

        if isinstance(nb := get_app().tab, Notebook):
            nb.select(index)
