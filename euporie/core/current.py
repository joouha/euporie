"""Allows access to the current running application."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app_or_none

if TYPE_CHECKING:
    from euporie.core.app import BaseApp


def get_app() -> "BaseApp":
    """Get the current application."""
    app = get_app_or_none()
    if app is None:
        from euporie.core.app import BaseApp

        app = BaseApp()
    return cast("BaseApp", app)
