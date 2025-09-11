"""Contain function which convert data to rich format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core.convert.registry import register
from euporie.core.filters import have_modules

if TYPE_CHECKING:
    from typing import Any

    from rich.markdown import Markdown

    from euporie.core.convert.datum import Datum


@register(
    from_="markdown",
    to="rich",
    filter_=have_modules("rich"),
)
async def markdown_to_rich_py(
    datum: Datum,
    cols: int | None = None,
    rows: int | None = None,
    fg: str | None = None,
    bg: str | None = None,
    **kwargs: Any,
) -> Markdown:
    """Convert base64 encoded data to bytes."""
    from rich.markdown import Markdown

    data = datum.data
    markup = data.decode() if isinstance(data, bytes) else data
    return Markdown(
        markup,
        # code_theme=str(config.syntax_theme),
        # inline_code_theme=str(config.syntax_theme),
    )
