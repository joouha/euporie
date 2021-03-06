"""Contains main format conversion function."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.cache import FastDictCache, SimpleCache
from prompt_toolkit.filters import to_filter

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, Iterable, List, Optional, Union

    from prompt_toolkit.filters import Filter, FilterOrBool

log = logging.getLogger(__name__)


class Converter(NamedTuple):
    """Holds a conversion function and its weight."""

    func: Callable
    filter_: Filter
    weight: int = 1


converters: "dict[str, dict[str, list[Converter]]]" = {}

_CONVERSION_CACHE: "SimpleCache" = SimpleCache(maxsize=20)
_FILTER_CACHE: "SimpleCache" = SimpleCache()


def register(
    from_: "Union[Iterable[str], str]",
    to: "str",
    filter_: "FilterOrBool" = True,
    weight: "int" = 1,
) -> "Callable":
    """Adds a converter to the centralized format conversion system."""
    if isinstance(from_, str):
        from_ = (from_,)

    def decorator(func: "Callable") -> "Callable":
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


def find_route(from_: "str", to: "str") -> "Optional[list]":
    """Finds the shortest conversion path between two formats."""
    if from_ == to:
        return [from_]

    chains = []

    def find(start: "str", chain: "list[str]") -> "None":
        if chain[0] == start:
            chains.append(chain)
        sources: "Dict[str, List[Converter]]" = converters.get(chain[0], {})
        for link in sources:
            if link not in chain:
                if any(
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
                    for step_a, step_b in zip(chain, chain[1:])
                ]
            ),
        )[0]
    else:
        return None


_CONVERTOR_ROUTE_CACHE: "FastDictCache[tuple[str, str], Optional[list]]" = (
    FastDictCache(find_route)
)


def convert(
    data: "Any",
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
        # log.debug("Converting from '%s' to '%s' using route: %s", from_, to, route)
        if route is None:
            raise NotImplementedError(f"Cannot convert from `{from_}` to `{to}`")
        for stage_a, stage_b in zip(route, route[1:]):
            # Find converter with lowest weight
            func = sorted(
                [
                    conv
                    for conv in converters[stage_b][stage_a]
                    if _FILTER_CACHE.get((conv,), conv.filter_)
                ],
                key=lambda x: x.weight,
            )[0].func
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
