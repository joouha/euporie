"""Contains function which convert :py:mod:`rich` renderables to other formats."""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich

from euporie.convert.base import register
from euporie.convert.util import have_modules

if TYPE_CHECKING:
    from typing import Optional

    from rich.console import RenderableType


@register(
    from_="rich",
    to="ansi",
    filter_=have_modules("rich"),
)
def markdown_to_rich_py(
    data: "RenderableType",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Converts base64 encoded data to bytes."""
    console = rich.get_console()
    options = console.options
    if width is not None:
        options = options.update(max_width=width)
    buffer = console.render(data, options)
    rendered_lines = console._render_buffer(buffer)
    return rendered_lines
