"""Contain function which convert data to rich format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core.convert.core import register
from euporie.core.convert.utils import have_modules

if TYPE_CHECKING:
    from pathlib import Path

    from rich.markdown import Markdown


@register(
    from_="markdown",
    to="rich",
    filter_=have_modules("rich"),
)
async def markdown_to_rich_py(
    data: str | bytes,
    width: int | None = None,
    height: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    path: Path | None = None,
    initial_format: str = "",
) -> Markdown:
    """Convert base64 encoded data to bytes."""
    from rich.markdown import Markdown

    markup = data.decode() if isinstance(data, bytes) else data
    return Markdown(
        markup,
        # code_theme=str(config.syntax_theme),
        # inline_code_theme=str(config.syntax_theme),
    )
