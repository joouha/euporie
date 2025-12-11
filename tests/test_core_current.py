"""Tests for get_app."""

from __future__ import annotations

from unittest.mock import Mock

from euporie.apptk.application.current import get_app_session, set_app

from euporie.core.app.app import BaseApp
from euporie.core.app.current import get_app


def test_get_app_with_running_session() -> None:
    """Test get_app when there is a running session."""
    app = Mock(spec=BaseApp)
    with set_app(app):
        assert get_app() is app


def test_get_app_without_running_session() -> None:
    """Test get_app when there is no running session."""
    assert get_app_session().app is None
    app = get_app()
    assert isinstance(app, BaseApp)
