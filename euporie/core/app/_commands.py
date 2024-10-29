"""Contains commands common to all euporie applications."""

from prompt_toolkit.filters import buffer_has_focus

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd
from euporie.core.filters import tab_has_focus


@add_cmd()
def _quit() -> None:
    """Quit euporie."""
    get_app().exit()


@add_cmd(
    name="close-tab",
    filter=tab_has_focus,
    menu_title="Close File",
)
def _close_tab() -> None:
    """Close the current tab."""
    get_app().close_tab()


@add_cmd(filter=tab_has_focus)
def _next_tab() -> None:
    """Switch to the next tab."""
    get_app().tab_idx += 1


@add_cmd(filter=tab_has_focus)
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
