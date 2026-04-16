import re
from collections.abc import Callable, Iterable, Iterator
from re import Match as RegexMatch
from re import Pattern
from typing import (
    TypeVar,
    overload,
)

from .regex_parser import (
    Node,
    Variable,
)

_INVALID_TRAILING_INPUT = "invalid_trailing"
EscapeFuncDict = dict[str, Callable[[str], str]]
_T = TypeVar("_T")

__all__ = [
    "Match",
    "Variables",
    "compile",
]

def compile(
    expression: str,
    escape_funcs: EscapeFuncDict | None = None,
    unescape_funcs: EscapeFuncDict | None = None,
) -> _CompiledGrammar: ...

class _CompiledGrammar:
    root_node: Node
    escape_funcs: EscapeFuncDict | None
    unescape_funcs: EscapeFuncDict | None
    _group_names_to_nodes: dict[str, str]
    _re_pattern = f"^{self._transform(root_node, create_group_func)}$"
    _re_prefix_patterns = list(self._transform_prefix(root_node, create_group_func))
    _re = re.compile(self._re_pattern, flags)
    _re_prefix = [re.compile(t, flags) for t in self._re_prefix_patterns]
    _re_prefix_with_trailing_input = [
        re.compile(
            "(?:{})(?P<{}>.*?)$".format(t.rstrip("$"), _INVALID_TRAILING_INPUT), flags
        )
        for t in self._re_prefix_patterns
    ]
    def __init__(
        self,
        root_node: Node,
        escape_funcs: EscapeFuncDict | None = None,
        unescape_funcs: EscapeFuncDict | None = None,
    ) -> None: ...
    def escape(self, varname: str, value: str) -> str: ...
    def unescape(self, varname: str, value: str) -> str: ...
    @classmethod
    def _transform(
        cls,
        root_node: Node,
        create_group_func: Callable[[Variable], str],
    ) -> str: ...
    @classmethod
    def _transform_prefix(
        cls,
        root_node: Node,
        create_group_func: Callable[[Variable], str],
    ) -> Iterable[str]: ...
    def match(self, string: str) -> Match | None: ...
    def match_prefix(self, string: str) -> Match | None: ...

class Match:
    string: str
    _re_matches: list[tuple[Pattern[str], RegexMatch[str]]]
    _group_names_to_nodes: dict[str, str]
    _unescape_funcs: dict[str, Callable[[str], str]]
    def __init__(
        self,
        string: str,
        re_matches: list[tuple[Pattern[str], RegexMatch[str]]],
        group_names_to_nodes: dict[str, str],
        unescape_funcs: dict[str, Callable[[str], str]],
    ) -> None: ...
    def _nodes_to_regs(self) -> list[tuple[str, tuple[int, int]]]: ...
    def _nodes_to_values(self) -> list[tuple[str, str, tuple[int, int]]]: ...
    def _unescape(self, varname: str, value: str) -> str: ...
    def variables(self) -> Variables: ...
    def trailing_input(self) -> MatchVariable | None: ...
    def end_nodes(self) -> Iterable[MatchVariable]: ...

class Variables(Generic[_T]):
    _tuples: list[tuple[str, str, tuple[int, int]]]
    def __init__(self, tuples: list[tuple[str, str, tuple[int, int]]]) -> None: ...
    def __repr__(self) -> str: ...
    @overload
    def get(self, key: str) -> str | None: ...
    @overload
    def get(self, key: str, default: str | _T) -> str | _T: ...
    def get(self, key: str, default: str | _T | None = None) -> str | _T | None: ...
    def getall(self, key: str) -> list[str]: ...
    def __getitem__(self, key: str) -> str | None: ...
    def __iter__(self) -> Iterator[MatchVariable]: ...

class MatchVariable:
    varname: str
    value: str
    slice: tuple[int, int]
    start = self.slice[0]
    stop = self.slice[1]
    def __init__(self, varname: str, value: str, slice: tuple[int, int]) -> None: ...
    def __repr__(self) -> str: ...
