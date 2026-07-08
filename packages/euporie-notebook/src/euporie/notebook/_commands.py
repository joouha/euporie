"""Commands for the notebook app."""

from apptk.commands import add_cmd
from apptk.filters.environment import have_modules

from euporie.core.widgets.minimap import MiniMap


@add_cmd(aliases=["n"], icon="", style="class:orange", keys=["c-n"])
def _new_notebook() -> None:
    """Create a new notebook file."""
    from euporie.notebook.current import get_app
    from euporie.notebook.panes.notebook import Notebook

    app = get_app()
    app.add_tab(tab := Notebook(app, None))
    tab.focus()


@add_cmd(aliases=["nc"], icon="", style="class:primary")
def _new_console() -> None:
    """Create a console tab."""
    from euporie.notebook.current import get_app
    from euporie.notebook.panes.console import Console

    app = get_app()
    app.add_tab(tab := Console(app, None))
    tab.focus()


@add_cmd(aliases=["nt"], icon="", style="class:success")
def _new_text_file() -> None:
    """Create a text file."""
    from euporie.notebook.current import get_app
    from euporie.notebook.panes.edit import EditorPane

    app = get_app()
    app.add_tab(tab := EditorPane(app, None))
    tab.focus()


have_ptterm = have_modules("ptterm")


@add_cmd(
    aliases=["nx"],
    icon="$",
    style="class:pink",
    filter=have_ptterm,
    hidden=~have_ptterm,
)
def _new_terminal() -> None:
    """Create a text file."""
    from euporie.notebook.current import get_app
    from euporie.notebook.panes.terminal import TerminalPane

    app = get_app()
    app.add_tab(tab := TerminalPane(app, None))
    tab.focus()


@add_cmd(menu_title="Documentation", icon="", style="class:success")
def _view_documentation() -> None:
    """Open the documentation in a web-view tab."""
    from apptk.application.current import get_app
    from upath import UPath

    get_app().open_file(UPath("https://euporie.readthedocs.io/"))


@add_cmd(keys=["c-b"])
def _toggle_side_bar_pane() -> None:
    """Open or close the current side-bar pane."""
    from euporie.notebook.current import get_app

    get_app().side_bar.toggle_pane()


def _get_minimap() -> MiniMap | None:
    """Return the MiniMap widget from the notebook app's side bar."""
    from euporie.notebook.current import get_app

    for panel in get_app().side_bar.panels:
        if isinstance(panel, MiniMap):
            return panel
    return None


@add_cmd()
def _zoom_minimap_in(amount: int = 1) -> None:
    """Zoom the minimap in."""
    if (minimap := _get_minimap()) is not None:
        minimap.zoom(amount)


@add_cmd()
def _zoom_minimap_out(amount: int = 1) -> None:
    """Zoom the minimap out."""
    if (minimap := _get_minimap()) is not None:
        minimap.zoom(-amount)


@add_cmd(icon="", style="class:primary")
def _tile_tabs() -> None:
    """Arrange all open tabs in a spiral tiled layout."""
    from euporie.notebook.current import get_app

    app = get_app()
    if app.docking_split is not None:
        app.docking_split.tile_panels()


@add_cmd(icon="", style="class:primary")
def _stack_tabs() -> None:
    """Collapse all open tabs into a single tabbed group."""
    from euporie.notebook.current import get_app

    app = get_app()
    if app.docking_split is not None:
        app.docking_split.stack_panels()


@add_cmd(title="Open configuration file")
def _open_config_file() -> None:
    """Open the configuration file in a new tab."""
    from upath import UPath

    from euporie.notebook.current import get_app
    from euporie.notebook.panes.edit import EditorPane

    app = get_app()
    config_path = UPath(app.config._config_path)
    # Create the config file if it doesn't exist
    if not config_path.exists():
        config_path.write_text("{}\n")
    app.add_tab(tab := EditorPane(app, config_path))
    tab.focus()
