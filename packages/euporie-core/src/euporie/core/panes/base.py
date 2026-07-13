"""Contain tab base class."""

from __future__ import annotations

import asyncio
import logging
from abc import ABCMeta
from io import UnsupportedOperation
from pathlib import PurePath
from typing import TYPE_CHECKING, ClassVar

from apptk.layout.containers import Window, WindowAlign
from apptk.layout.controls import FormattedTextControl
from apptk.utils import Event

from euporie.core.path import UntitledPath

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from typing import Any

    from apptk.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class Pane(metaclass=ABCMeta):
    """Base class for interface tabs."""

    _registry: ClassVar[set[type[Pane]]] = set()
    name: str | None = None
    weight: int = 0
    mime_types: ClassVar[set[str]] = set()
    file_extensions: ClassVar[dict[str, None]] = {}
    _untitled_count = 0

    container: AnyContainer

    commands = (
        "save-file",
        "refresh-tab",
        "pipe-tab",
    )

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        """Compile a registry of named tabs."""
        super().__init_subclass__(**kwargs)
        if cls.name:
            Pane._registry.add(cls)

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        self.app = app

        if path is None:
            self.__class__._untitled_count += 1
            ext = next(iter(self.file_extensions), "")
            path = UntitledPath(f"untitled:/untitled-{self._untitled_count}{ext}")
        elif not isinstance(path, PurePath):
            from apptk.path import parse_path

            path = parse_path(path)
        self.path = path

        self.container = Window(
            FormattedTextControl(
                [("fg:#888888", "\nLoading…")], show_cursor=False, focusable=True
            ),
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
            path.parent.mkdir(exist_ok=True, parents=True)

            # Write file (implementations handle atomicity and backups)
            self.write_file(path)

            self.dirty = False
            self.saving = False
            self.app.invalidate()
            log.debug("File saved successfully")

            # Run the callback
            if callable(cb):
                cb()

        except (OSError, NotImplementedError, UnsupportedOperation) as exc:
            # Path-related errors (permissions, missing dirs, read-only fs,
            # unsupported filesystem operations, etc.) can be resolved by
            # saving to a different location
            log.exception("An error occurred while saving the file")
            if dialog := self.app.get_dialog("save-as"):
                dialog.show(tab=self, cb=cb, error=str(exc))

    def write_file(self, path: Path) -> None:
        """Write the tab's data to a path.

        Not implement in the base tab.

        Args:
            path: An path at which to save the file

        """
        raise NotImplementedError(
            f"File saving not implement for `{self.__class__.__name__}` tab"
        )

    def read_file(self, path: Path) -> None:
        """Read the tab's data from a path.

        Not implemented in the base tab.

        Args:
            path: A path from which to read the file

        """
        raise NotImplementedError(
            f"File reading not implemented for `{self.__class__.__name__}` tab"
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


class LoadingPane(Pane):
    """A placeholder pane shown while a file is being resolved and opened."""

    name = None

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Create a loading placeholder pane."""
        super().__init__(app, path)
        self._title = path.name if path is not None else "Loading…"

    @property
    def title(self) -> str:
        """Return the tab title."""
        return self._title
