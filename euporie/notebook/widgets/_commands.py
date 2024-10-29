"""Define commands for widgets."""

from euporie.core.commands import add_cmd


@add_cmd()
def _toggle_side_bar_pane() -> None:
    """Open or close the current side-bar pane."""
    from euporie.notebook.current import get_app

    get_app().side_bar.toggle_pane()
