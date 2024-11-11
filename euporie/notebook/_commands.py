"""Commands for the notebook app."""

from euporie.core.commands import add_cmd


@add_cmd(aliases=["n"])
def _new_notebook() -> None:
    """Create a new file."""
    from euporie.notebook.current import get_app
    from euporie.notebook.tabs.notebook import Notebook

    app = get_app()
    app.add_tab(tab := Notebook(app, None))
    tab.focus()


@add_cmd()
def _view_documentation() -> None:
    """Open the documentation in a web-view tab."""
    from upath import UPath

    from euporie.core.app.current import get_app

    get_app().open_file(UPath("https://euporie.readthedocs.io/"))
