"""Contains renderer classes which convert markdown to displayable output."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.config import config
from euporie.markdown import Markdown
from euporie.render.base import DataRenderer
from euporie.render.rich import RichRenderer

if TYPE_CHECKING:
    from typing import Any, Union


__all__ = ["MarkdownRenderer", "markdown_rich"]

log = logging.getLogger(__name__)


class MarkdownRenderer(DataRenderer):
    """A grouping renderer for markdown."""


class markdown_rich(MarkdownRenderer):
    """A renderer for markdown text."""

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Creates a new markdown renderer using rich."""
        super().__init__(*args, **kwargs)
        self.rich_renderer = RichRenderer().select()

    @classmethod
    def validate(cls) -> "bool":
        """Always return `True` as `rich` is a dependency of `euporie`."""
        return True

    def process(self, data: "str") -> "Union[bytes, str]":
        """Renders markdown using :py:mod:`rich`.

        Args:
            data: An markdown string.

        Returns:
            An ANSI string representing the rendered input.

        """
        return self.rich_renderer.render(
            Markdown(
                data,
                code_theme=str(config.syntax_theme),
                inline_code_theme=str(config.syntax_theme),
            ),
            self.width,
            self.height,
        )
