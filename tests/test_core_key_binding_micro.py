from __future__ import annotations
from __future__ import annotations

from unittest.mock import Mock

from prompt_toolkit.application.current import set_app

from euporie.core.app.dummy import DummyApp
from euporie.core.key_binding.bindings.micro import _comment_prefix_for_language


def _make_app(language: str) -> DummyApp:
    """Build a dummy app with a language-aware tab.

    Args:
        language: The language to assign to the current input.

    Returns:
        A dummy app wired with a mock tab.
    """
    app = DummyApp()
    tab = Mock()
    current_input = Mock()
    current_input.language = language
    tab.current_input = current_input
    app.tabs = [tab]
    app._tab_idx = 0
    return app


def test_comment_prefix_for_known_languages() -> None:
    """Use mapped comment prefixes for known languages."""
    app = _make_app("javascript")
    with set_app(app):
        assert _comment_prefix_for_language() == "// "

    app = _make_app("LUA")
    with set_app(app):
        assert _comment_prefix_for_language() == "-- "

    app = _make_app("python")
    with set_app(app):
        assert _comment_prefix_for_language() == "# "


def test_comment_prefix_fallback() -> None:
    """Fall back to hash comments for unknown languages."""
    app = _make_app("unknownlang")
    with set_app(app):
        assert _comment_prefix_for_language() == "# "

    app = DummyApp()
    with set_app(app):
        assert _comment_prefix_for_language() == "# "
