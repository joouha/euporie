"""Define common filters."""

from __future__ import annotations

from apptk.enums import EditingMode
from apptk.filters.app import (
    emacs_insert_mode,
    emacs_mode,
    vi_insert_mode,
    vi_mode,
    vi_navigation_mode,
    vi_replace_mode,
)
from apptk.filters.base import Condition
from apptk.key_binding.helix_state import InputMode as HelixInputMode
from apptk.key_binding.micro_state import MicroInputMode

__all__ = [
    "helix_insert_mode",
    "helix_mode",
    "helix_navigation_mode",
    "helix_replace_mode",
    "insert_mode",
    "is_searching",
    "micro_insert_mode",
    "micro_mode",
    "micro_recording_macro",
    "micro_replace_mode",
    "replace_mode",
]


@Condition
def helix_mode() -> bool:
    """When the helix key-bindings are active."""
    from apptk.application.current import get_app

    return get_app().editing_mode == EditingMode.HELIX


@Condition
def helix_insert_mode() -> bool:
    """Determine if the editor is in helix insert mode."""
    from apptk.application.current import get_app

    app = get_app()
    return app.helix_state.input_mode == HelixInputMode.INSERT


@Condition
def helix_navigation_mode() -> bool:
    """Determine if the editor is in helix navigation mode."""
    from apptk.application.current import get_app

    app = get_app()
    return app.helix_state.input_mode == HelixInputMode.NAVIGATION


@Condition
def helix_replace_mode() -> bool:
    """Determine if the editor is in helix replace mode."""
    from apptk.application.current import get_app

    app = get_app()
    return app.helix_state.input_mode in (
        HelixInputMode.REPLACE,
        HelixInputMode.REPLACE_SINGLE,
    )


@Condition
def micro_mode() -> bool:
    """When the micro key-bindings are active."""
    from apptk.application.current import get_app

    return get_app().editing_mode == EditingMode.MICRO


@Condition
def micro_replace_mode() -> bool:
    """Determine if the editor is in overwrite mode."""
    from apptk.application.current import get_app

    app = get_app()
    return app.micro_state.input_mode == MicroInputMode.REPLACE


@Condition
def micro_insert_mode() -> bool:
    """Determine if the editor is in insert mode."""
    from apptk.application.current import get_app

    app = get_app()
    return app.micro_state.input_mode == MicroInputMode.INSERT


@Condition
def micro_recording_macro() -> bool:
    """Determine if a micro macro is being recorded."""
    from apptk.application.current import get_app

    return get_app().micro_state.current_recording is not None


"""Determine if any binding style is in insert mode."""
insert_mode = (
    (vi_mode & vi_insert_mode)
    | (emacs_mode & emacs_insert_mode)
    | (micro_mode & micro_insert_mode)
    | (helix_mode & helix_insert_mode)
)

"""Determine if any binding style is in replace mode."""
replace_mode = micro_replace_mode | vi_replace_mode | helix_replace_mode

"""Determine if any binding style is in navigation mode."""
navigation_mode = vi_navigation_mode | helix_navigation_mode


@Condition
def is_searching() -> bool:
    """Determine if the app is in search mode."""
    from apptk.application.current import get_app

    app = get_app()
    return (
        app.search_bar is not None and app.search_bar.control in app.layout.search_links
    )
