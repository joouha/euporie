"""Contains functions which convert data to formatted text."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import to_formatted_text

from euporie.core.convert.base import register
from euporie.core.formatted_text.ansi import ANSI

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples

MARKDOWN_ENHANCED = False

'''
@register(
    from_="markdown",
    to="formatted_text",
)
def markdown_to_ft(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "StyleAndTextTuples":
    """Converts markdown to formatted text."""
    global MARKDOWN_ENHANCED
    if not MARKDOWN_ENHANCED:
        from euporie.core.formatted_text.markdown_enhanced import (
            enable_enchanced_markdown,
        )

        enable_enchanced_markdown()
        MARKDOWN_ENHANCED = True

    from euporie.core.formatted_text.markdown import Markdown

    return to_formatted_text(Markdown(data, width=width))
'''


@register(
    from_="html",
    to="formatted_text",
)
def html_to_ft(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "StyleAndTextTuples":
    """Converts markdown to formatted text."""
    from euporie.core.formatted_text.html import HTML

    return to_formatted_text(HTML(data, width=width))


@register(
    from_="ansi",
    to="formatted_text",
)
def ansi_to_ft(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "StyleAndTextTuples":
    """Converts ANSI text to formatted text."""
    return to_formatted_text(ANSI(data.strip()))
