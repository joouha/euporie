"""Defines functions which allow access to typed version of the current application."""

from typing import TYPE_CHECKING, cast

from prompt_toolkit.application import get_app

if TYPE_CHECKING:
    from euporie.app.base import EuporieApp
    from euporie.app.edit import EditApp
    from euporie.app.preview import PreviewApp


def get_base_app() -> "EuporieApp":
    """Get the current application."""
    return cast("EuporieApp", get_app())


def get_preview_app() -> "PreviewApp":
    """Get the current application."""
    return cast("PreviewApp", get_app())


def get_edit_app() -> "EditApp":
    """Get the current application."""
    return cast("EditApp", get_app())
