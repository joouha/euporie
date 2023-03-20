"""Allow access to the current running application."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as ptk_get_app

if TYPE_CHECKING:
    from euporie.notebook.app import NotebookApp


def get_app() -> NotebookApp:
    """Get the current application."""
    return cast("NotebookApp", ptk_get_app())
