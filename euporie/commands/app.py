"""Define commands at the application level."""

import logging

from prompt_toolkit.filters import Condition, buffer_has_focus

from euporie.app.current import get_tui_app as get_app
from euporie.commands.registry import add
from euporie.config import config
from euporie.filters import tab_has_focus

log = logging.getLogger(__name__)


@add(
    keys="c-n",
    group="File",
)
def new_notebook() -> "None":
    """Create a new file."""
    get_app().ask_new_file()


@add(
    keys="c-o",
    group="File",
)
def open_file() -> "None":
    """Open a file."""
    get_app().ask_open_file()


@add(
    keys="c-w",
    filter=tab_has_focus,
    group="File",
)
def close_file() -> None:
    """Close the current file."""
    get_app().close_tab()


@add(
    keys="c-q",
    name="quit",
    group="File",
)
def quit() -> "None":
    """Quit euporie."""
    get_app().exit()


@add(
    keys="c-pageup",
    filter=tab_has_focus,
    group="App",
)
def next_tab() -> "None":
    """Switch to the next tab."""
    get_app().tab_idx += 1


@add(
    keys="c-pagedown",
    filter=tab_has_focus,
    group="App",
)
def previous_tab() -> "None":
    """Switch to the previous tab."""
    get_app().tab_idx -= 1


@add(
    keys="tab",
    group="App",
    filter=~buffer_has_focus,
)
@add(
    keys="tab",
    group="App",
    filter=~buffer_has_focus,
)
def focus_next() -> "None":
    """Focus the next control."""
    get_app().layout.focus_next()


@add(
    keys="s-tab",
    group="App",
    filter=~buffer_has_focus,
)
def focus_previous() -> "None":
    """Focus the previous control."""
    get_app().layout.focus_previous()


@add(
    keys="l",
    filter=~buffer_has_focus,
    group="Config",
    toggled=Condition(lambda: config.line_numbers),
)
def show_line_numbers() -> "None":
    """Toggle the visibility of line numbers."""
    config.toggle("line_numbers")


@add(
    filter=~buffer_has_focus,
    group="Config",
)
def switch_background_pattern() -> "None":
    """Switch between different background patterns."""
    config.toggle("background_pattern")


@add(
    filter=~buffer_has_focus,
    group="Config",
    toggled=Condition(lambda: config.show_cell_borders),
)
def show_cell_borders() -> "None":
    """Toggle the visibility of the borders of unselected cells."""
    config.toggle("show_cell_borders")


@add(
    keys="w",
    filter=~buffer_has_focus,
    group="Config",
    toggled=Condition(lambda: config.expand),
)
def use_full_width() -> "None":
    """Toggle whether cells should extend across the full width of the screen."""
    config.toggle("expand")


@add(
    title="Completions as you type",
    filter=~buffer_has_focus,
    toggled=Condition(lambda: bool(config.autocomplete)),
)
def autocomplete() -> "None":
    """Toggle whether completions should be shown automatically."""
    config.toggle("autocomplete")


@add(
    title="Suggest lines from history",
    group="Config",
    toggled=Condition(lambda: bool(config.autosuggest)),
)
def autosuggest() -> "None":
    """Toggle whether to suggest line completions from the kernel's history."""
    config.toggle("autosuggest")


@add(
    title="Run cell after external edit",
    group="Config",
    toggled=Condition(lambda: bool(config.run_after_external_edit)),
)
def run_after_external_edit() -> "None":
    """Toggle whether cells should run automatically after editing externally."""
    config.toggle("run_after_external_edit")


@add(
    group="Config",
    toggled=Condition(lambda: bool(config.show_status_bar)),
)
def show_status_bar() -> "None":
    """Toggle the visibility of the status bar."""
    config.toggle("show_status_bar")


@add(group="help")
def keyboard_shortcuts() -> "None":
    """Show the currently bound keyboard shortcuts."""
    get_app().help_keys()


@add(group="help")
def view_logs() -> "None":
    """Open the logs in a new tab."""
    get_app().help_logs()


@add(group="help")
def about() -> "None":
    """Show the about dialog."""
    get_app().help_about()
