"""Defines functions which allow access to typed version of the current application."""

from typing import TYPE_CHECKING, cast

from prompt_toolkit.application import get_app

if TYPE_CHECKING:
    from euporie.app.base import EuporieApp
    from euporie.app.dump import DumpApp
    from euporie.app.tui import TuiApp


def get_base_app() -> "EuporieApp":
    """Get the current application."""
    return cast("EuporieApp", get_app())


def get_dump_app() -> "DumpApp":
    """Get the current application."""
    return cast("DumpApp", get_app())


def get_tui_app() -> "TuiApp":
    """Get the current application."""
    return cast("TuiApp", get_app())
