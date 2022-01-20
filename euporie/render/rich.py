"""Renderer for :py:mod:`rich` renderables."""

from typing import TYPE_CHECKING

import rich

from euporie.render.base import DataRenderer

if TYPE_CHECKING:
    from typing import Union

__all__ = ["RichRenderer"]


class RichRenderer(DataRenderer):
    """A mixin for processing `rich.console.RenderableType` objects."""

    console: "rich.console.Console"

    @classmethod
    def validate(cls) -> "bool":
        """Always return `True` as `rich` is a dependency of `euporie`."""
        return True

    def load(self, data: "rich.console.RenderableType") -> "None":
        """Get a `rich.console.Console` instance for rendering."""
        self.console = rich.get_console()

    def process(self, data: "rich.console.RenderableType") -> "Union[bytes, str]":
        """Render a `rich.console.RenderableType` to ANSI text.

        Args:
            data: An object renderable by `rich.console`.

        Returns:
            An ANSI string representing the rendered input.

        """
        buffer = self.console.render(
            data,
            self.console.options.update(max_width=self.width),
        )
        rendered_lines = self.console._render_buffer(buffer)
        return rendered_lines
