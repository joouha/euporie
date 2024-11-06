"""Defines a logo widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from prompt_toolkit.layout.containers import WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.core import __logo__
from euporie.core.filters import has_tabs
from euporie.core.layout.containers import Window

if TYPE_CHECKING:
    from typing import Any

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.layout.controls import UIControl
    from prompt_toolkit.layout.dimension import AnyDimension


class Logo(Window):
    """A widget to display the application's logo."""

    def __init__(
        self,
        content: UIControl | None = None,
        height: AnyDimension = 1,
        width: AnyDimension = 3,
        style: str | Callable[[], str] = "class:menu,logo",
        dont_extend_width: FilterOrBool = True,
        align: WindowAlign | Callable[[], WindowAlign] = WindowAlign.CENTER,
        **kwargs: Any,
    ) -> None:
        """Create a new window with defaults specified."""
        if content is None:
            content = FormattedTextControl(
                [("", f" {__logo__} ")],
                focusable=~has_tabs,
                show_cursor=False,
            )
        super().__init__(
            content=content,
            height=height,
            width=width,
            style=style,
            dont_extend_width=dont_extend_width,
            **kwargs,
        )
