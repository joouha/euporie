"""Define a status-bar widget."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.layout import containers
from prompt_toolkit.layout.containers import ConditionalContainer, WindowAlign
from prompt_toolkit.layout.containers import (
    to_container as ptk_to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.core.app.current import get_app
from euporie.core.filters import has_toolbar
from euporie.core.layout.containers import VSplit, Window

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from prompt_toolkit.filters.base import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.formatted_text.base import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer, Container

    StatusBarFields = tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]

log = logging.getLogger(__name__)


_CONTAINER_STATUSES: WeakKeyDictionary[
    Container, Callable[[], StatusBarFields | None]
] = WeakKeyDictionary()


def to_container(container: AnyContainer) -> Container:
    """Monkey-patch `to_container` to collect container status functions."""
    result = ptk_to_container(container)
    if hasattr(container, "__pt_status__"):
        _CONTAINER_STATUSES[result] = container.__pt_status__
    return result


containers.to_container = to_container


class StatusContainer:
    """A container which allows attaching a status function."""

    def __init__(
        self, body: AnyContainer, status: Callable[[], StatusBarFields | None]
    ) -> None:
        """Initiate a new instance with a body and status function."""
        self.body = body
        self.status = status

    def __pt_status__(self) -> StatusBarFields | None:
        """Return the status fields."""
        return self.status()

    def __pt_container__(self) -> AnyContainer:
        """Return the body container."""
        return self.body


class StatusBar:
    """A status bar which shows the status of the current tab."""

    def __init__(
        self, extra_filter: FilterOrBool = True, default: StatusBarFields | None = None
    ) -> None:
        """Create a new status bar instance."""
        self.default: StatusBarFields = default or ([], [])
        self._status_cache: FastDictCache[tuple[int], list[StyleAndTextTuples]] = (
            FastDictCache(self._status, size=1)
        )
        self.container = ConditionalContainer(
            content=VSplit(
                [
                    Window(
                        FormattedTextControl(
                            lambda: self._status_cache[get_app().render_counter,][0]
                        ),
                        style="class:status",
                    ),
                    Window(
                        FormattedTextControl(
                            lambda: self._status_cache[get_app().render_counter,][1]
                        ),
                        style="class:status.right",
                        align=WindowAlign.RIGHT,
                    ),
                ],
                height=1,
            ),
            filter=get_app().config.filters.show_status_bar
            & ~has_toolbar
            & to_filter(extra_filter),
        )

    def _status(self, render_counter: int = 0) -> list[StyleAndTextTuples]:
        """Load and format the current status bar entries."""
        layout = get_app().layout

        # entries = self.default
        entries: tuple[list[AnyFormattedText], list[AnyFormattedText]] = ([], [])

        current: Container | None = layout.current_window
        while current:
            if (
                callable(
                    func := (
                        _CONTAINER_STATUSES.get(current)
                        or getattr(current, "__pt_status__", None)
                    )
                )
                and (result := func()) is not None
            ):
                # Add parent entries to start of left side
                entries[0][0:0] = result[0]
                # Add parent entries to end of right side
                entries[1].extend(result[1])

            # If current window has no parent, update child to parent map, as layout
            # might have changed since the last render
            if current not in layout._child_to_parent:
                layout.update_parents_relations()
            current = layout._child_to_parent.get(current)

        # Format the status entries
        output: list[StyleAndTextTuples] = []
        for entry in entries:
            output.append([])
            for field in entry:
                if field:
                    output[-1] += [
                        ("class:status-sep", "▌"),
                        *to_formatted_text(field, style="class:status-field"),
                        ("class:status-sep", "▐"),
                    ]
        return output

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container
