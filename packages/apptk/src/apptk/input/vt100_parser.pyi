import logging
import re
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING

from apptk.input import vt100_parser as ptk_vt100_parser
from apptk.input.ansi_escape_sequences import ANSI_SEQUENCES

from ..key_binding.key_processor import KeyPress
from ..keys import Keys
from .ansi_escape_sequences import ANSI_SEQUENCES

if TYPE_CHECKING:
    from typing import Any

    from apptk.keys import Keys

_cpr_response_re = re.compile("^" + re.escape("\x1b[") + r"\d+;\d+R\Z")
_mouse_event_re = re.compile("^" + re.escape("\x1b[") + r"(<?[\d;]+[mM]|M...)\Z")
_cpr_response_prefix_re = re.compile("^" + re.escape("\x1b[") + r"[\d;]*\Z")
_mouse_event_prefix_re = re.compile("^" + re.escape("\x1b[") + r"(<?[\d;]*|M.{0,2})\Z")
_IS_PREFIX_OF_LONGER_MATCH_CACHE = _IsPrefixOfLongerMatchCache()
log = logging.getLogger(__name__)

__all__ = [
    "Vt100Parser",
]

class _Flush: ...

class _IsPrefixOfLongerMatchCache(ptk_vt100_parser._IsPrefixOfLongerMatchCache):
    _response_prefix_re = re.compile(
        "^\\x1b(\n                \\][^\\\\\\x07]*  # Operating System Commands\n                |\n                _[^\\\\]*  # Application Program Command\n                |\n                \\[\\?[\\d;]*  # Primary device attribute responses\n                |\n                P[ -~]*(\\x1b|x1b\\\\)?\n            )\\Z",
        re.VERBOSE,
    )
    _ansi_sequence_prefixes = {
        seq[:i] for seq in ANSI_SEQUENCES for i in range(len(seq))
    }
    def __missing__(self, prefix: str) -> bool: ...
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class Vt100Parser(ptk_vt100_parser.Vt100Parser):
    feed_key_callback: Callable[[KeyPress], None]
    _in_bracketed_paste = False
    _input_parser = self._input_parser_generator()
    _paste_buffer = ""
    patterns: dict[Keys, re.Pattern]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def reset(self, request: bool = False) -> None: ...
    def _start_parser(self) -> None: ...
    def _get_match(self, prefix: str) -> None | Keys | tuple[Keys, ...]: ...
    def _input_parser_generator(self) -> Generator[None, str | _Flush]: ...
    def _call_handler(
        self,
        key: str | Keys | tuple[Keys, ...],
        insert_text: str,
    ) -> None: ...
    def feed(self, data: str) -> None: ...
    def flush(self) -> None: ...
    def feed_and_flush(self, data: str) -> None: ...
