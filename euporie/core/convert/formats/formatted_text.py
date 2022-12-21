"""Contains functions which convert data to formatted text."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text import to_formatted_text

from euporie.core.convert.base import register
from euporie.core.formatted_text.ansi import ANSI
from euporie.core.lexers import detect_lexer

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from upath import UPath

    from euporie.core.formatted_text.html import HTML

_html_cache: "SimpleCache[int, HTML]" = SimpleCache(maxsize=20)


@register(
    from_="html",
    to="formatted_text",
)
def html_to_ft(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "StyleAndTextTuples":
    """Converts markdown to formatted text."""
    from euporie.core.formatted_text.html import HTML

    markup = data.decode() if isinstance(data, bytes) else data
    html = _html_cache.get(hash(markup), partial(HTML, markup, width=width, base=path))
    if (
        width is not None
        and height is not None
        and (html.width != width or html.height != height)
    ):
        html.render(width, height)
    return to_formatted_text(html)


@register(
    from_="ansi",
    to="formatted_text",
)
def ansi_to_ft(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "StyleAndTextTuples":
    """Converts ANSI text to formatted text."""
    markup = data.decode() if isinstance(data, bytes) else data
    ft: "StyleAndTextTuples"
    if "\x1b" in markup:
        ft = to_formatted_text(ANSI(markup.strip()))
    elif (lexer := detect_lexer(markup, path)) is not None:
        from prompt_toolkit.lexers.pygments import _token_cache

        ft = [(_token_cache[t], v) for _, t, v in lexer.get_tokens_unprocessed(markup)]
    else:
        ft = to_formatted_text(markup)
    return ft
