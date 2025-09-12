"""Contain functions which convert data to html format."""

from __future__ import annotations

import logging
from functools import cache
from typing import TYPE_CHECKING

from euporie.core.app.current import get_app
from euporie.core.convert.registry import register
from euporie.core.lexers import detect_lexer

if TYPE_CHECKING:
    from typing import Any

    from markdown_it import MarkdownIt

    from euporie.core.convert.datum import Datum

log = logging.getLogger(__name__)


@cache
def markdown_parser() -> MarkdownIt:
    """Lazy-load a markdown parser."""
    from markdown_it import MarkdownIt
    from mdit_py_plugins.amsmath import amsmath_plugin
    from mdit_py_plugins.dollarmath.index import dollarmath_plugin
    from pygments import highlight
    from pygments.formatters import HtmlFormatter

    class MarkdownParser(MarkdownIt):
        """Subclas the markdown parser to allow ``file:`` URIs."""

        def validateLink(self, url: str) -> bool:
            """Allow all link URIs."""
            return True

    return (
        MarkdownParser(
            options_update={
                "highlight": lambda text, language, lang_args: highlight(
                    text,
                    detect_lexer(text, language=language),
                    HtmlFormatter(
                        nowrap=True,
                        noclasses=True,
                        style=(
                            app.syntax_theme
                            if hasattr((app := get_app()), "syntax_theme")
                            else "default"
                        ),
                    ),
                )
            }
        )
        .enable("linkify")
        .enable("table")
        .enable("strikethrough")
        .use(dollarmath_plugin, allow_space=True, double_inline=True)
        .use(amsmath_plugin)
        # .use(tasklists_plugin)
    )


@register(from_="markdown", to="html")
async def markdown_to_html_markdown_it(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> str:
    """Convert markdown to HTML using :py:mod:`markdownit_py`."""
    parser = markdown_parser()
    data = datum.data
    markup = data.decode() if isinstance(data, bytes) else data
    return parser.render(markup)
