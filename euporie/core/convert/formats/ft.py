"""Contain functions which convert data to formatted text."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text import to_formatted_text

from euporie.core.convert.registry import register
from euporie.core.ft.ansi import ANSI
from euporie.core.ft.utils import strip_one_trailing_newline
from euporie.core.lexers import detect_lexer

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples

    from euporie.core.convert.datum import Datum
    from euporie.core.ft.html import HTML

log = logging.getLogger(__name__)

_html_cache: SimpleCache[str, HTML] = SimpleCache(maxsize=20)


@register(
    from_="html",
    to="ft",
)
async def html_to_ft(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
) -> StyleAndTextTuples:
    """Convert markdown to formatted text."""
    from euporie.core.ft.html import HTML

    data = datum.data
    markup = data.decode() if isinstance(data, bytes) else data
    html = _html_cache.get(
        datum.hash,
        partial(
            HTML,
            markup,
            width=cols,
            base=datum.path,
            collapse_root_margin=True,
            _initial_format=datum.root.format,
        ),
    )
    return await html._render(cols, rows)


_BLACKLISTED_LEXERS = {
    "CBM BASIC V2",
    "Tera Term macro",
    "Text only",
    "GDScript",
}


@register(
    from_="ansi",
    to="ft",
)
async def ansi_to_ft(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
) -> StyleAndTextTuples:
    """Convert ANSI text to formatted text, lexing & formatting automatically."""
    data = datum.data
    markup = data.decode() if isinstance(data, bytes) else data
    ft: StyleAndTextTuples
    if "\x1b" in markup or "\r" in markup:
        ft = to_formatted_text(ANSI(markup.strip()))
    else:
        # Replace tabs with spaces
        markup = markup.expandtabs()
        # Use lexer whitelist
        if (
            lexer := detect_lexer(markup, path=datum.path)
        ) is not None and lexer.name not in _BLACKLISTED_LEXERS:
            from prompt_toolkit.lexers.pygments import _token_cache

            log.debug('Lexing output using "%s" lexer', lexer.name)
            ft = [
                (_token_cache[t], v) for _, t, v in lexer.get_tokens_unprocessed(markup)
            ]

        else:
            ft = to_formatted_text(markup)
    return to_formatted_text(strip_one_trailing_newline(ft))
