"""Allows access to the current running application."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as get_app_ptk

if TYPE_CHECKING:
    from euporie.core.app import BaseApp


def get_app() -> "BaseApp":
    """Get the current application."""
    return cast("BaseApp", get_app_ptk())
