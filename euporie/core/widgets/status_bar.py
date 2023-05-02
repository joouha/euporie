"""Define a status-bar widget."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.layout import containers
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.containers import (
    to_container as ptk_to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.filters import is_searching

if TYPE_CHECKING:
    from typing import Callable, Sequence

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
        self._status_cache: FastDictCache[
            tuple[int], list[StyleAndTextTuples]
        ] = FastDictCache(self._status, size=1)
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
            filter=get_app().config.filter("show_status_bar")
            & ~is_searching
            & to_filter(extra_filter),
        )

    def _status(self, render_counter: int = 0) -> list[StyleAndTextTuples]:
        """Load and format the current status bar entries."""
        layout = get_app().layout
        current: Container = layout.current_window

        entries = self.default
        while True:
            if callable(
                func := (
                    _CONTAINER_STATUSES.get(current)
                    or getattr(current, "__pt_status__", None)
                )
            ):
                result = func()
                if result is not None:
                    entries = result
                    break
            elif current in layout._child_to_parent:
                current = layout._child_to_parent[current]
                continue
            break

        output: list[StyleAndTextTuples] = []
        # Show the tab's status fields
        for entry in entries:
            output.append([])
            for field in entry:
                if field:
                    if isinstance(field, tuple):
                        ft = [field]
                    else:
                        ft = to_formatted_text(field, style="class:status.field")
                    output[-1] += [
                        ("class:status.field", " "),
                        *ft,
                        ("class:status.field", " "),
                        ("class:status", " "),
                    ]
            if output[-1]:
                output[-1].pop()
        return output

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container

    # ################################### Settings ####################################

    add_setting(
        name="show_status_bar",
        flags=["--show-status-bar"],
        type_=bool,
        title="status bar",
        help_="Show the status bar",
        default=True,
        schema={
            "type": "boolean",
        },
        description="""
            Whether the status bar should be shown at the bottom of the screen.
        """,
    )
