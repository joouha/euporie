"""Contains function which convert data to rich format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core.convert.base import register
from euporie.core.convert.utils import have_modules

if TYPE_CHECKING:
    from typing import Optional

    from rich.markdown import Markdown
    from upath import UPath


@register(
    from_="markdown",
    to="rich",
    filter_=have_modules("rich"),
)
def markdown_to_rich_py(
    data: "str|bytes",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
    path: "Optional[UPath]" = None,
) -> "Markdown":
    """Converts base64 encoded data to bytes."""
    from rich.markdown import Markdown

    markup = data.decode() if isinstance(data, bytes) else data
    return Markdown(
        markup,
        # code_theme=str(config.syntax_theme),
        # inline_code_theme=str(config.syntax_theme),
    )
