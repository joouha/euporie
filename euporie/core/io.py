"""Defines custom inputs and outputs, and related methods."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from prompt_toolkit.input import vt100_parser
from prompt_toolkit.input.base import DummyInput, _dummy_context_manager
from prompt_toolkit.output.vt100 import Vt100_Output as PtkVt100_Output

if TYPE_CHECKING:
    from typing import Any, Callable, ContextManager, Union

    from prompt_toolkit.keys import Keys

_response_prefix_re = re.compile(
    r"""^\x1b(
        \][^\\\x07]*  # Operating System Commands
        |
        _[^\\]*  # Application Program Command
        |
        \[\?[\d;]*  # Primary device attribute responses
    )\Z""",
    re.VERBOSE,
)


class _IsPrefixOfLongerMatchCache(vt100_parser._IsPrefixOfLongerMatchCache):
    def __missing__(self, prefix: "str") -> "bool":
        """Check if the response might match an OSC or APC code, or DA response."""
        result = super().__missing__(prefix)
        if not result:
            if _response_prefix_re.match(prefix):
                result = True
                self[prefix] = result
        return result


# Monkey patch the prefix cache
vt100_parser._IS_PREFIX_OF_LONGER_MATCH_CACHE = _IsPrefixOfLongerMatchCache()


class Vt100Parser(vt100_parser.Vt100Parser):
    """A Vt100Parser which checks input against additional key patterns."""

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Create a new VT100 parser."""
        super().__init__(*args, **kwargs)
        self.queries: "dict[Keys, re.Pattern]" = {}

    def _get_match(self, prefix: "str") -> "Union[None, Keys, tuple[Keys, ...]]":
        """Checks for additional key matches first."""
        for key, pattern in self.queries.items():
            if pattern.match(prefix):
                return key

        return super()._get_match(prefix)


class IgnoredInput(DummyInput):
    """An input which ignores input but does not immediately close the app."""

    def attach(
        self, input_ready_callback: "Callable[[], None]"
    ) -> "ContextManager[None]":
        """Do not call the callback, so the input is never closed."""
        return _dummy_context_manager()


class Vt100_Output(PtkVt100_Output):
    """A Vt100 output which enables SGR pixel mouse positioning."""

    def enable_mouse_support(self) -> "None":
        """Additionally enable SGR-pixel mouse positioning."""
        super().enable_mouse_support()
        self.write_raw("\x1b[?1016h")

    def disable_mouse_support(self) -> "None":
        """Additionally disable SGR-pixel mouse positioning."""
        super().disable_mouse_support()
        self.write_raw("\x1b[?1016l")
