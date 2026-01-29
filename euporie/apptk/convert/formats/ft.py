"""Contain functions which convert data to formatted text."""

from __future__ import annotations

import logging
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING

from euporie.apptk.cache import SimpleCache
from euporie.apptk.convert.registry import register
from euporie.apptk.formatted_text import to_formatted_text
from euporie.apptk.formatted_text.ansi import ANSI
from euporie.apptk.formatted_text.utils import strip_one_trailing_newline
from euporie.apptk.lexers.utils import detect_lexer

if TYPE_CHECKING:
    from typing import Any

    from euporie.apptk.formatted_text.base import StyleAndTextTuples

    from euporie.apptk.convert.datum import Datum
    from euporie.apptk.formatted_text.html import HTML, CssSelectors

log = logging.getLogger(__name__)

_html_cache: SimpleCache[tuple[str | Any, ...], HTML] = SimpleCache(maxsize=20)


@register(
    from_="html",
    to="ft",
)
async def html_to_ft(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    extend: bool = True,
    css: CssSelectors | None = None,
    **kwargs: Any,
) -> StyleAndTextTuples:
    """Convert HTML to formatted text."""
    from euporie.apptk.formatted_text.html import HTML

    data = datum.data
    markup = data.decode() if isinstance(data, bytes) else data

    css = defaultdict(dict, css or {})
    if datum.root.format == "markdown":
        from euporie.apptk.css import MARKDOWN_CSS

        for k, v in MARKDOWN_CSS.items():
            css[k].update(v)

    html = _html_cache.get(
        (datum.hash, *kwargs.items()),
        partial(
            HTML,
            markup,
            width=cols,
            css=css,
            base=datum.path,
            collapse_root_margin=True,
            fill=extend,
        ),
    )
    return await html._render(cols, rows)


_WHITELISTED_LEXERS = {
    "python",
    "markdown",
    "javascript",
    "json",
}


@register(
    from_="ansi",
    to="ft",
)
async def ansi_to_ft(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    lex: bool = False,
    **kwargs: Any,
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
            lex
            and (lexer := detect_lexer(markup, path=datum.path)) is not None
            and lexer.name in _WHITELISTED_LEXERS
        ):
            from euporie.apptk.lexers.pygments import _token_cache

            log.debug('Lexing output using "%s" lexer', lexer.name)
            ft = [
                (_token_cache[t], v) for _, t, v in lexer.get_tokens_unprocessed(markup)
            ]

        else:
            ft = to_formatted_text(markup)
    return to_formatted_text(strip_one_trailing_newline(ft))
