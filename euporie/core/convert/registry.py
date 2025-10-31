"""Contain main format conversion function."""

from __future__ import annotations

import logging
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.cache import FastDictCache, SimpleCache
from prompt_toolkit.filters import to_filter

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from prompt_toolkit.filters import Filter, FilterOrBool

log = logging.getLogger(__name__)


class Converter(NamedTuple):
    """Hold a conversion function and its weight."""

    func: Callable
    filter_: Filter
    weight: int = 1


converters: dict[str, dict[str, list[Converter]]] = {}

_FILTER_CACHE: SimpleCache = SimpleCache()


def register(
    from_: Iterable[str] | str,
    to: str,
    filter_: FilterOrBool = True,
    weight: int = 1,
) -> Callable:
    """Add a converter to the centralized format conversion system."""
    if isinstance(from_, str):
        from_ = (from_,)

    def decorator(func: Callable) -> Callable:
        if to not in converters:
            converters[to] = {}
        for from_format in from_:
            if from_format not in converters[to]:
                converters[to][from_format] = []
            converters[to][from_format].append(
                Converter(func=func, filter_=to_filter(filter_), weight=weight)
            )
        return func

    return decorator


def _find_route(from_: str, to: str) -> list | None:
    """Find the shortest conversion path between two formats."""
    from euporie.core.convert import formats  # noqa: F401

    if from_ == to:
        return [from_]

    chains = []

    def find(start: str, chain: list[str]) -> None:
        if chain[0] == start:
            chains.append(chain)
        sources: dict[str, list[Converter]] = converters.get(chain[0], {})
        for link in sources:
            if link not in chain and any(
                _FILTER_CACHE.get((conv,), conv.filter_)
                for conv in sources.get(link, [])
            ):
                find(start, [link, *chain])

    find(from_, [to])

    if chains:
        # Find chain with shortest weighted length
        return sorted(
            chains,
            key=lambda chain: sum(
                [
                    min(
                        [
                            conv.weight
                            for conv in converters.get(step_b, {}).get(step_a, [])
                            if _FILTER_CACHE.get((conv,), conv.filter_)
                        ]
                    )
                    for step_a, step_b in pairwise(chain)
                ]
            ),
        )
    else:
        return None


_CONVERTOR_ROUTE_CACHE: FastDictCache[tuple[str, str], list | None] = FastDictCache(
    _find_route
)


def find_route(from_: str, to: str) -> list | None:
    """Find and cache conversion routes."""
    return _CONVERTOR_ROUTE_CACHE[from_, to]
