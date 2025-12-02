"""Contain tab base class."""

from __future__ import annotations

import asyncio
import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.layout.containers import Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd
from euporie.core.filters import tab_can_save, tab_has_focus
from euporie.core.key_binding.registry import (
    register_bindings,
)
from euporie.core.path import UntitledPath, parse_path

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

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

    def reset(self) -> None:
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

        self.app.create_background_task(asyncio.to_thread(self.save, path, _wrapped_cb))

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Save the current file."""
        if path is not None:
            self.path = path

        if (self.path is None or isinstance(self.path, UntitledPath)) and (
            dialog := self.app.get_dialog("save-as")
        ):
            dialog.show(tab=self, cb=cb)
            return

        path = self.path
        try:
            # Ensure parent path exists
            parent = path.parent
            parent.mkdir(exist_ok=True, parents=True)

            # Create backup if original file exists
            backup_path: Path | None = None
            if path.exists():
                name = f"{path.name}.bak"
                if not name.startswith("."):
                    name = f".{name}"
                backup_path = parent / name
                if self.app.config.backup_on_save:
                    try:
                        import shutil

                        shutil.copy2(path, backup_path)
                    except Exception as e:
                        log.error("Failed to create backup: %s", e)
                        raise

            # Write new content directly to original file
            try:
                self.write_file(path)
            except Exception as e:
                log.error("Failed to write file: %s", e)
                # Restore from backup if it exists
                if backup_path is not None:
                    log.info("Restoring backup")
                    backup_path.replace(path)
                raise

            self.dirty = False
            self.saving = False
            self.app.invalidate()
            log.debug("File saved successfully")

            # Run the callback
            if callable(cb):
                cb()

        except Exception:
            log.exception("An error occurred while saving the file")
            if dialog := self.app.get_dialog("save-as"):
                dialog.show(tab=self, cb=cb)

    def write_file(self, path: Path) -> None:
        """Write the tab's data to a path.

        Not implement in the base tab.

        Args:
            path: An path at which to save the file

        """
        raise NotImplementedError(
            f"File saving not implement for `{self.__class__.__name__}` tab"
        )

    def __pt_searchables__(self) -> Sequence[Window]:
        """Return a list of searchable buffer controls for this tab.

        Returns:
            A list of searchable buffer controls

        Raises:
            NotImplementedError: If the tab does not provide searchable buffers
        """
        raise NotImplementedError()

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
    @add_cmd(filter=tab_can_save, aliases=["w"])
    def _save_file(event: KeyPressEvent, path: str = "") -> None:
        """Save the current file."""
        if (tab := get_app().tab) is not None:
            try:
                tab._save(UPath(path) if path else None)
            except NotImplementedError:
                pass

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.tabs.base:Tab": {
                "save-file": "c-s",
                "refresh-tab": "f5",
            }
        }
    )
