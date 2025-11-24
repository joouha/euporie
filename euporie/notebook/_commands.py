"""Commands for the notebook app."""

from euporie.core.commands import add_cmd


@add_cmd(aliases=["n"], icon="", style="class:orange")
def _new_notebook() -> None:
    """Create a new notebook file."""
    from euporie.notebook.current import get_app
    from euporie.notebook.tabs.notebook import Notebook

    app = get_app()
    app.add_tab(tab := Notebook(app, None))
    tab.focus()


@add_cmd(aliases=["nc"], icon="", style="class:primary")
def _new_console() -> None:
    """Create a console tab."""
    from euporie.notebook.current import get_app
    from euporie.notebook.tabs.console import Console

    app = get_app()
    app.add_tab(tab := Console(app, None))
    tab.focus()


@add_cmd(aliases=["nt"], icon="", style="class:success")
def _new_text_file() -> None:
    """Create a text file."""
    from euporie.notebook.current import get_app
    from euporie.notebook.tabs.edit import EditorTab

    app = get_app()
    app.add_tab(tab := EditorTab(app, None))
    tab.focus()


@add_cmd(menu_title="Documentation", icon="", style="class:success")
def _view_documentation() -> None:
    """Open the documentation in a web-view tab."""
    from upath import UPath

    from euporie.core.app.current import get_app

    get_app().open_file(UPath("https://euporie.readthedocs.io/"))


@add_cmd()
def _toggle_side_bar_pane() -> None:
    """Open or close the current side-bar pane."""
    from euporie.notebook.current import get_app

    get_app().side_bar.toggle_pane()
