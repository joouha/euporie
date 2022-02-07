"""Contains main format conversion function."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import FastDictCache, SimpleCache
from prompt_toolkit.filters import to_filter

if TYPE_CHECKING:
    from typing import Any, Callable, Optional

    from prompt_toolkit.filters import FilterOrBool

log = logging.getLogger(__name__)


convertors: "dict[str, dict[str, list[Callable]]]" = {}


_CONVERSION_CACHE: "SimpleCache" = SimpleCache(maxsize=20)


def register(from_: "str", to: "str", filter_: "FilterOrBool") -> "Callable":
    """Adds a convertor to the centralized format conversion system."""

    def decorator(func: "Callable") -> "Callable":
        if to_filter(filter_)():
            if to not in convertors:
                convertors[to] = {}
            if from_ not in convertors[to]:
                convertors[to][from_] = []
            convertors[to][from_].append(func)
        return func

    return decorator


def convert(
    data: "str",
    from_: "str",
    to: "str",
    cols: "Optional[int]" = None,
    rows: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "Any":
    """Convert between formats."""
    data_hash = hash(data)

    def _convert(
        data: "str",
        from_: "str",
        to: "str",
        cols: "Optional[int]" = None,
        rows: "Optional[int]" = None,
        fg: "Optional[str]" = None,
        bg: "Optional[str]" = None,
    ) -> "Any":
        if from_ == to:
            return data
        route = _CONVERTOR_ROUTE_CACHE[(from_, to)]
        log.debug("Converting from '%s' to '%s' using route: %s", from_, to, route)
        if route is None:
            raise NotImplementedError(f"Cannot convert from `{from_}` to `{to}`")
        for stage_a, stage_b in zip(route, route[1:]):
            func = convertors[stage_b][stage_a][0]
            # Add intermediate steps to the cache
            data = _CONVERSION_CACHE.get(
                (data_hash, from_, stage_b, cols, rows, fg, bg),
                partial(func, data, cols, rows, fg, bg),
            )
        return data

    data = _CONVERSION_CACHE.get(
        (data_hash, from_, to, cols, rows, fg, bg),
        partial(_convert, data, from_, to, cols, rows, fg, bg),
    )

    return data


def find_route(from_: "str", to: "str") -> "Optional[list]":
    """Finds the shortest conversion path between two formats."""
    chains = []

    def find(start: "str", chain: "list[str]") -> "None":
        if chain[0] == start:
            chains.append(chain)
        for link in convertors.get(chain[0], []):
            if link not in chain:
                find(start, [link, *chain])

    find(from_, [to])

    if chains:
        return sorted(chains, key=len)[0]
    else:
        return None


_CONVERTOR_ROUTE_CACHE: "FastDictCache[tuple[str, str], Optional[list]]" = (
    FastDictCache(find_route)
)
