"""Argument parser utilities for the configuration system."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from typing import TextIO

    from _typeshed import SupportsWrite


class MetavarTypeHelpFormatter(argparse.MetavarTypeHelpFormatter):
    """A help formatter that handles actions with no type."""

    def _get_default_metavar_for_positional(self, action: argparse.Action) -> str:
        """Return metavar for positional arguments."""
        if action.type is None:
            return action.dest.upper()
        return super()._get_default_metavar_for_positional(action)


class ArgumentParser(argparse.ArgumentParser):
    """An argument parser that formats help with syntax highlighting."""

    def __init__(
        self, *args: Any, syntax_theme: str = "euporie", **kwargs: Any
    ) -> None:
        """Initialize the parser.

        Args:
            *args: Positional arguments for ArgumentParser.
            syntax_theme: Pygments theme for help formatting.
            **kwargs: Keyword arguments for ArgumentParser.
        """
        super().__init__(*args, **kwargs)
        self.syntax_theme = syntax_theme
        # Prevent coloring in the help message on 3.14+ (we do it ourselves)
        self.color = False

    def _print_message(
        self, message: str, file: SupportsWrite[str] | None = None
    ) -> None:
        """Print a message with syntax highlighting.

        Args:
            message: The message to print.
            file: The file to write to.
        """
        from apptk.formatted_text.base import FormattedText
        from apptk.lexers.pygments import _token_cache
        from apptk.shortcuts.utils import print_formatted_text
        from apptk.styles.pygments import style_from_pygments_cls
        from euporie.core.pygments import ArgparseLexer
        from euporie.core.style import get_style_by_name

        if message:
            file = cast("TextIO | None", file)
            style = style_from_pygments_cls(get_style_by_name(self.syntax_theme))
            print_formatted_text(
                FormattedText(
                    [
                        (_token_cache[t], v)
                        for _, t, v in ArgparseLexer().get_tokens_unprocessed(
                            message.rstrip("\n")
                        )
                    ]
                ),
                file=file,
                style=style,
                include_default_pygments_style=False,
            )
