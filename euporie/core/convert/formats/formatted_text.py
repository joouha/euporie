"""Contain functions which convert data to formatted text."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.formatted_text import to_formatted_text

from euporie.core.convert.core import register
from euporie.core.formatted_text.ansi import ANSI
from euporie.core.formatted_text.utils import strip_one_trailing_newline
from euporie.core.lexers import detect_lexer

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples

    from euporie.core.formatted_text.html import HTML, CssSelectors

log = logging.getLogger(__name__)

_html_cache: SimpleCache[int, HTML] = SimpleCache(maxsize=20)


@register(
    from_="html",
    to="formatted_text",
)
def html_to_ft(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    css: CssSelectors | None = None,
    browser_css: CssSelectors | None = None,
) -> StyleAndTextTuples:
    """Convert markdown to formatted text."""
    from euporie.core.formatted_text.html import HTML

    markup = data.decode() if isinstance(data, bytes) else data
    html = _html_cache.get(
        hash(markup),
        partial(
            HTML,
            markup,
            width=width,
            base=path,
            collapse_root_margin=True,
            css=css,
            browser_css=browser_css,
        ),
    )

    if (
        width is not None
        and height is not None
        and (html.width != width or html.height != height)
    ):
        html.render(width, height)

    return to_formatted_text(html)


@register(
    from_="markdown",
    to="formatted_text",
)
def markdown_to_ft(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
) -> StyleAndTextTuples:
    """Convert markdown to formatted text, injecting a custom CSS style-sheet."""
    from euporie.core.convert.formats.html import markdown_to_html_markdown_it
    from euporie.core.formatted_text.markdown import _MARKDOWN_CSS

    css = _MARKDOWN_CSS

    # If we are rendering a file rather than a snippet, apply margins to the root
    if path is not None:
        from prompt_toolkit.filters.utils import _always

        from euporie.core.formatted_text.html import CssSelector

        css = {
            _always: {
                **_MARKDOWN_CSS[_always],
                ((CssSelector(item="::root"),),): {
                    "max_width": "100em",
                    "margin_left": "auto",
                    "margin_right": "auto",
                },
            }
        }

    return html_to_ft(
        markdown_to_html_markdown_it(
            path=path, bg=bg, fg=fg, height=height, width=width, data=data
        ),
        width=width,
        height=height,
        fg=fg,
        bg=bg,
        path=path,
        css=css,
    )


_BLACKLISTED_LEXERS = {
    "CBM BASIC V2",
    "Tera Term macro",
}


@register(
    from_="ansi",
    to="formatted_text",
)
def ansi_to_ft(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
) -> StyleAndTextTuples:
    """Convert ANSI text to formatted text."""
    markup = data.decode() if isinstance(data, bytes) else data
    ft: StyleAndTextTuples
    if "\x1b" in markup or "\r" in markup:
        ft = to_formatted_text(ANSI(markup.strip()))
    else:
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
