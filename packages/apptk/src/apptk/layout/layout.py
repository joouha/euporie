"""Wrapper for the layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.application.current import get_app_or_none
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.layout import FocusableElement
from prompt_toolkit.layout.layout import Layout as PtkLayout
from prompt_toolkit.utils import Event

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from prompt_toolkit.layout.containers import Container
    from prompt_toolkit.layout.controls import UIControl


__all__ = [
    "Layout",
]


class _Traversal(NamedTuple):
    """The result of walking the layout tree once."""

    containers: list[Container]
    windows: list[Window]
    controls: list[UIControl]
    parents: dict[Container, Container]


class Layout(PtkLayout):
    """Extended layout that fires an event when focus changes.

    This subclass adds an :attr:`on_focus_changed` event that is triggered
    whenever the focused window changes.

    It also caches the result of walking the layout tree for the duration of a
    render pass.  Summary work such as collecting the controls for key binding
    lookups, rebuilding the child-to-parent map and collecting invalidation
    events all need the same traversal, and they used to repeat it several
    times per keystroke.  The cache is keyed by the application's render
    counter, so a single traversal is shared by all of those consumers within
    one render, and the tree is re-walked after it has been rendered again
    (which is when containers can have been added or removed).
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the layout."""
        self.on_focus_changed = Event(self)
        self._traversal_cache: tuple[tuple[int, int], _Traversal] | None = None
        # Incremented whenever the set of controls in the layout changes, so
        # that consumers can cheaply detect whether cached work is stale.
        self.controls_generation = 0
        self._previous_controls: list[UIControl] = []
        super().__init__(*args, **kwargs)

    def _build_traversal(self) -> _Traversal:
        """Walk the layout tree and collect containers, windows and parents."""
        containers: list[Container] = []
        windows: list[Window] = []
        controls: list[UIControl] = []
        parents: dict[Container, Container] = {}

        def collect(container: Container) -> None:
            containers.append(container)
            if isinstance(container, Window):
                windows.append(container)
                controls.append(container.content)
            for child in container.get_children():
                parents[child] = container
                collect(child)

        collect(self.container)
        return _Traversal(containers, windows, controls, parents)

    def _traversal(self) -> _Traversal:
        """Return the layout traversal, cached for the current render."""
        app = get_app_or_none()
        if app is None:
            return self._build_traversal()
        key = (id(app), app.render_counter)
        if self._traversal_cache is not None and self._traversal_cache[0] == key:
            return self._traversal_cache[1]
        traversal = self._build_traversal()
        self._traversal_cache = (key, traversal)
        return traversal

    def clear_traversal_cache(self) -> None:
        """Forget the cached layout traversal."""
        self._traversal_cache = None

    def find_all_windows(self) -> Generator[Window, None, None]:
        """Find all the :class:`.Window` objects in this layout."""
        yield from self._traversal().windows

    def find_all_controls(self) -> Iterable[UIControl]:
        """Find all the :class:`.UIControl` objects in this layout."""
        yield from self._traversal().controls

    def focus(self, value: FocusableElement) -> None:
        """Focus the given UI element."""
        try:
            super().focus(value)
        except ValueError:
            # The layout might have changed since the traversal was cached.
            self.clear_traversal_cache()
            super().focus(value)

    def update_parents_relations(self) -> None:
        """Update child->parent relationships mapping."""
        traversal = self._build_traversal()
        app = get_app_or_none()
        if app is not None:
            self._traversal_cache = ((id(app), app.render_counter), traversal)
        self._child_to_parent = traversal.parents

        controls = traversal.controls
        if controls != self._previous_controls:
            self._previous_controls = controls
            self.controls_generation += 1

    def reset(self) -> None:
        """Reset the layout."""
        self.clear_traversal_cache()
        super().reset()

    @property
    def current_window(self) -> Window:
        """Return the :class:`.Window` object that is currently focused."""
        return self._stack[-1]

    @current_window.setter
    def current_window(self, value: Window) -> None:
        """Set the :class:`.Window` object to be currently focused."""
        previous = self._stack[-1] if self._stack else None
        self._stack.append(value)
        if value != previous:
            self.on_focus_changed.fire()
