"""Contain tab base class."""

from __future__ import annotations

import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.layout.containers import WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd
from euporie.core.filters import tab_has_focus
from euporie.core.key_binding.registry import (
    register_bindings,
)
from euporie.core.layout.containers import Window
from euporie.core.path import parse_path
from euporie.core.utils import run_in_thread_with_context

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.widgets.status import StatusBarFields

log = logging.getLogger(__name__)


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    _registry: ClassVar[set[type[Tab]]] = set()
    name: str | None = None
    weight: int = 0
    mime_types: ClassVar[set[str]] = set()
    file_extensions: ClassVar[dict[str, None]] = {}
    _untitled_count = 0

    container: AnyContainer

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        """Compile a registry of named tabs."""
        super().__init_subclass__(**kwargs)
        if cls.name:
            Tab._registry.add(cls)

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        self.app = app
        if path is None:
            self.__class__._untitled_count += 1
            ext = next(iter(self.file_extensions), "")
            path = UPath(f"untitled:/untitled-{self._untitled_count}{ext}")
        self.path = parse_path(path)
        self.container = Window(
            FormattedTextControl([("fg:#888888", "\nLoading…")], focusable=True),
            align=WindowAlign.CENTER,
        )

        self.on_close = Event(self)
        self.on_change = Event(self)
        self.before_save = Event(self)
        self.after_save = Event(self)

        self.dirty = False
        self.saving = False

    @property
    def title(self) -> str:
        """Return the tab title."""
        return ""

    def reset(self) -> "None":  # noqa B027
        """Reset the state of the tab."""

    def close(self, cb: Callable | None = None) -> None:
        """Close a tab with a callback.

        Args:
            cb: A function to call after the tab is closed.

        """
        # Run callback
        if callable(cb):
            cb()
        self.on_close.fire()

    def focus(self) -> None:
        """Focus the tab (or make it visible)."""
        self.app.focus_tab(self)

    def _save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Perform the file save in a background thread."""
        self.before_save.fire()

        def _wrapped_cb() -> None:
            """Wrap save callback to trigger post-save event."""
            if callable(cb):
                cb()
            self.after_save.fire()

        run_in_thread_with_context(self.save, path, _wrapped_cb)

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Save the current notebook."""
        raise NotImplementedError

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        return ([], [])

    def __pt_container__(self) -> AnyContainer:
        """Return the main container object."""
        return self.container

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=tab_has_focus, title="Refresh the current tab")
    def _refresh_tab() -> None:
        """Reload the tab contents and reset the tab."""
        if (tab := get_app().tab) is not None:
            tab.reset()

    # Depreciated v2.5.0
    @staticmethod
    @add_cmd(filter=tab_has_focus, title="Reset the current tab")
    def _reset_tab() -> None:
        log.warning(
            "The `reset-tab` command was been renamed to `refresh-tab` in v2.5.0,"
            " and will be removed in a future version"
        )
        Tab._refresh_tab()

    @staticmethod
    @add_cmd(filter=tab_has_focus)
    def _save_file() -> None:
        """Save the current file."""
        if (tab := get_app().tab) is not None:
            try:
                tab._save()
            except NotImplementedError:
                pass

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.tabs.base.Tab": {
                "save-file": "c-s",
                "refresh-tab": "f5",
            }
        }
    )
