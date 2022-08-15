"""Contains functions which convert data to html format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.core.convert.base import register
from euporie.core.convert.utils import have_modules

if TYPE_CHECKING:
    from typing import Optional

log = logging.getLogger(__name__)

# Check for markdown-it-py
markdown_parser: "Optional[MarkdownIt]" = None

try:
    from markdown_it import MarkdownIt
except ModuleNotFoundError:
    pass
else:

    class MarkdownParser(MarkdownIt):
        """Subclass the markdown parser to allow ``file:`` URIs."""

        def validateLink(self, url: "str") -> "bool":
            """Allows all link URIs."""
            return True

    markdown_parser = (
        MarkdownParser().enable("linkify").enable("table").enable("strikethrough")
    )

# Check for markdown-it-py plugins
try:
    import mdit_py_plugins  # noqa F401
except ModuleNotFoundError:
    pass
else:
    from mdit_py_plugins.amsmath import amsmath_plugin
    from mdit_py_plugins.dollarmath.index import dollarmath_plugin
    from mdit_py_plugins.texmath.index import texmath_plugin

    # from mdit_py_plugins.tasklists import tasklists_plugin

    if markdown_parser is not None:
        markdown_parser.use(texmath_plugin)
        markdown_parser.use(dollarmath_plugin)
        markdown_parser.use(amsmath_plugin)
        # markdown_parser.use(tasklists_plugin)


@register(from_="markdown", to="html", filter_=have_modules("markdown_it"))
def markdown_to_html_markdown_it(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert markdown to HTML using :py:mod:`markdownit_py`."""
    assert markdown_parser is not None
    # Give markdown tables borders
    html = "<style>table{border-width:1}th{border-width:3;font-weight:bold}</style>"
    html += markdown_parser.render(data)
    return html
