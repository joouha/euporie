"""Wrapper for the layout."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.layout.layout import Layout as PtkLayout

# from euporie.apptk.application.current import get_app
from euporie.apptk.cache import SimpleCache
from euporie.apptk.layout.containers import ConditionalContainer, Container

if TYPE_CHECKING:
    from collections.abc import Iterable

log = logging.getLogger(__name__)

# Module-level cache for walk results, keyed by container_id
# Value is tuple of (container, is_hidden) pairs
_walk_cache: SimpleCache[int, tuple[tuple[Container, bool], ...]] = SimpleCache(
    maxsize=256
)


def _invalidate_walk_cache() -> None:
    """Clear the walk cache. Should be called once per render cycle."""
    _walk_cache.clear()


def _walk_impl(
    container: Container, parent_hidden: bool = False
) -> Iterable[tuple[Container, bool]]:
    """Walk through layout, yielding (container, is_hidden) pairs."""
    is_hidden = parent_hidden or (
        isinstance(container, ConditionalContainer) and not container.filter()
    )

    yield container, is_hidden

    for c in container.get_children():
        yield from _walk_impl(c, parent_hidden=is_hidden)


def walk(container: Container, skip_hidden: bool = False) -> Iterable[Container]:
    """Walk through layout, starting at this container."""
    key = id(container)

    def getter() -> tuple[tuple[Container, bool], ...]:
        return tuple(_walk_impl(container))

    cached = _walk_cache.get(key, getter)

    log.debug((key, len(_walk_cache._data)))
    # When `skip_hidden` is set, don't go into disabled ConditionalContainer containers.
    if skip_hidden:
        return tuple(c for c, is_hidden in cached if not is_hidden)
        yield from (c for c, is_hidden in cached if not is_hidden)
    else:
        return tuple(c for c, _ in cached)
        yield from (c for c, _ in cached)


def walk__(container: Container, skip_hidden: bool = False) -> Iterable[Container]:
    """Walk through layout, starting at this container.
    """
    if (
        skip_hidden
        and isinstance(container, ConditionalContainer)
        and not container.filter()
    ):
        return

    yield container

    for c in container.get_children():
        # yield from walk(c)
        yield from walk(c, skip_hidden=skip_hidden)


class Layout(PtkLayout):
    def update_parents_relations(self) -> None:
        _invalidate_walk_cache()
