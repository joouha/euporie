"""Contains function which convert data to rich format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.config import config
from euporie.convert.base import register
from euporie.convert.util import have_modules

if TYPE_CHECKING:
    from typing import Optional

    from rich.markdown import Markdown


@register(
    from_="markdown",
    to="rich",
    filter_=have_modules("rich"),
)
def markdown_to_rich_py(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "Markdown":
    """Converts base64 encoded data to bytes."""
    from rich.markdown import Markdown

    return Markdown(
        data,
        code_theme=str(config.syntax_theme),
        inline_code_theme=str(config.syntax_theme),
    )
