"""Contain functions which convert data to formatted text."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text import to_formatted_text

from euporie.core.convert.core import register
from euporie.core.ft.ansi import ANSI
from euporie.core.ft.utils import strip_one_trailing_newline
from euporie.core.lexers import detect_lexer

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples

    from euporie.core.ft.html import HTML

log = logging.getLogger(__name__)

_html_cache: SimpleCache[int, HTML] = SimpleCache(maxsize=20)


@register(
    from_="html",
    to="ft",
)
async def html_to_ft(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> StyleAndTextTuples:
    """Convert markdown to formatted text."""
    from euporie.core.ft.html import HTML

    markup = data.decode() if isinstance(data, bytes) else data
    html = _html_cache.get(
        hash(markup),
        partial(
            HTML,
            markup,
            width=width,
            base=path,
            collapse_root_margin=True,
            _initial_format=initial_format,
        ),
    )
    return await html._render(width, height)


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
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> StyleAndTextTuples:
    """Convert ANSI text to formatted text, lexing & formatting automatically."""
    markup = data.decode() if isinstance(data, bytes) else data
    ft: StyleAndTextTuples
    if "\x1b" in markup or "\r" in markup:
        ft = to_formatted_text(ANSI(markup.strip()))
    else:
        # Replace tabs with spaces
        markup = markup.expandtabs()
        # Use lexer whitelist
        if (
            lexer := detect_lexer(markup, path=path)
        ) is not None and lexer.name not in _BLACKLISTED_LEXERS:
            from prompt_toolkit.lexers.pygments import _token_cache

            log.debug('Lexing output using "%s" lexer', lexer.name)
            ft = [
                (_token_cache[t], v) for _, t, v in lexer.get_tokens_unprocessed(markup)
            ]

        else:
            ft = to_formatted_text(markup)
    return strip_one_trailing_newline(ft)
