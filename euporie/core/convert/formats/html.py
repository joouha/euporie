"""Contains functions which convert data to html format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from mdit_py_plugins.amsmath import amsmath_plugin
from mdit_py_plugins.dollarmath.index import dollarmath_plugin
from mdit_py_plugins.texmath.index import texmath_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from euporie.core.convert.base import register
from euporie.core.current import get_app

if TYPE_CHECKING:
    from typing import Optional

    from upath import UPath

log = logging.getLogger(__name__)


class MarkdownParser(MarkdownIt):
    """Subclass the markdown parser to allow ``file:`` URIs."""

    def validateLink(self, url: "str") -> "bool":
        """Allows all link URIs."""
        return True


markdown_parser = (
    (
        MarkdownParser(
            options_update={
                "highlight": lambda text, language, lang_args: highlight(
                    text,
                    get_lexer_by_name(language),
                    HtmlFormatter(
                        nowrap=True,
                        noclasses=True,
                        style=app.config.syntax_theme
                        if hasattr((app := get_app()), "config")
                        else "default",
                    ),
                )
            }
        )
        .enable("linkify")
        .enable("table")
        .enable("strikethrough")
    )
    .use(texmath_plugin)
    .use(dollarmath_plugin)
    .use(amsmath_plugin)
    # .use(tasklists_plugin)
)


@register(from_="markdown", to="html")
def markdown_to_html_markdown_it(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "str":
    """Convert markdown to HTML using :py:mod:`markdownit_py`."""
    assert markdown_parser is not None
    markup = data.decode() if isinstance(data, bytes) else data
    return markdown_parser.render(markup)
