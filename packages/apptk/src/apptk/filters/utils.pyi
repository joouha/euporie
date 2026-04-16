from .base import Always, Filter, FilterOrBool, Never

_always = Always()
_never = Never()
_bool_to_filter: dict[bool, Filter] = {
    True: _always,
    False: _never,
}

__all__ = [
    "is_true",
    "to_filter",
]

def to_filter(bool_or_filter: FilterOrBool) -> Filter: ...
def is_true(value: FilterOrBool) -> bool: ...
