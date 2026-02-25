"""Define custom inputs and outputs, and related methods."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, cast

from prompt_toolkit.input import vt100_parser as ptk_vt100_parser

from euporie.apptk.input.ansi_escape_sequences import ANSI_SEQUENCES

if TYPE_CHECKING:
    from typing import Any

    from euporie.apptk.keys import Keys


log = logging.getLogger(__name__)


class _IsPrefixOfLongerMatchCache(ptk_vt100_parser._IsPrefixOfLongerMatchCache):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Pattern for any ANSI escape sequence
        self._response_prefix_re = re.compile(
            r"""^\x1b(
                \][^\\\x07]*  # Operating System Commands
                |
                _[^\\]*  # Application Program Command
                |
                \[\?[\d;]*  # Primary device attribute responses
                |
                P[ -~]*(\x1b|x1b\\)?
            )\Z""",
            re.VERBOSE,
        )
        # Generate prefix matches for all known ansi escape sequences
        # This is faster than PTK's method
        self._ansi_sequence_prefixes = {
            seq[:i] for seq in ANSI_SEQUENCES for i in range(len(seq))
        }

    def __missing__(self, prefix: str) -> bool:
        """Check if the response might match an OSC or APC code, or DA response."""
        result = bool(
            # (hard coded) If this could be a prefix of a CPR response, return True.
            ptk_vt100_parser._cpr_response_prefix_re.match(prefix)
            # True if this could be a mouse event sequence
            or ptk_vt100_parser._mouse_event_prefix_re.match(prefix)
            # True if this could be the prefix of an expected escape sequence
            or prefix in self._ansi_sequence_prefixes
            # If this could be a prefix of any other escape sequence, return True
            or self._response_prefix_re.match(prefix)
        )
        self[prefix] = result
        return result


_IS_PREFIX_OF_LONGER_MATCH_CACHE = _IsPrefixOfLongerMatchCache()


class Vt100Parser(ptk_vt100_parser.Vt100Parser):
    """A Vt100Parser which checks input against additional key patterns."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create a new VT100 parser."""
        from euporie.apptk.keys import Keys

        super().__init__(*args, **kwargs)
        self.patterns: dict[Keys, re.Pattern] = {
            Keys.ColorsResponse: re.compile(
                r"^\x1b\](?P<c>(\d+;)?\d+)+;rgb:"
                r"(?P<r>[0-9A-Fa-f]{2,4})\/"
                r"(?P<g>[0-9A-Fa-f]{2,4})\/"
                r"(?P<b>[0-9A-Fa-f]{2,4})"
                # Allow BEL or ST as terminator
                r"(?:\x1b\\|\x9c|\x07)"
            ),
            Keys.PaletteDsrResponse: re.compile(r"^\x1b\[\?997;(?P<mode>\d)n"),
            Keys.PixelSizeResponse: re.compile(r"^\x1b\[4;(?P<y>\d+);(?P<x>\d+)t"),
            Keys.KittyGraphicsStatusResponse: re.compile(
                r"^\x1b_Gi=(4294967295|0);(?P<status>OK)\x1b\\"
            ),
            Keys.DeviceAttributesResponse: re.compile(r"^\x1b\[\?(?P<attrs>[\d;]*)c"),
            Keys.ItermGraphicsStatusResponse: re.compile(
                r"^\x1bP>\|(?P<term>[^\x1b]+)\x1b\\"
            ),
            Keys.SgrPixelStatusResponse: re.compile(r"^\x1b\[\?1016;(?P<Pm>\d)\$"),
            Keys.ClipboardDataResponse: re.compile(
                r"^\x1b\]52;(?:c|p)?;(?P<data>[A-Za-z0-9+/=]+)\x1b\\"
            ),
        }

    def _get_match(self, prefix: str) -> None | Keys | tuple[Keys, ...]:
        """Check for additional key matches first."""
        for key, pattern in self.patterns.items():
            if pattern.match(prefix):
                return cast("Keys", key)

        return super()._get_match(prefix)
