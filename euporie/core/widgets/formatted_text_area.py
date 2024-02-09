"""Contain dpdated ANSI parsing and Formatted Text processing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters import to_filter
from prompt_toolkit.formatted_text import (
    fragment_list_to_text,
    split_lines,
    to_formatted_text,
)
from prompt_toolkit.layout.margins import ConditionalMargin
from prompt_toolkit.layout.processors import DynamicProcessor, Processor, Transformation
from prompt_toolkit.widgets import TextArea

from euporie.core.margins import NumberedMargin

if TYPE_CHECKING:
    from typing import Any

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.layout.processors import TransformationInput

log = logging.getLogger(__name__)


class FormattedTextProcessor(Processor):
    """Apply formatted text to a TextArea."""

    def __init__(self, formatted_text: StyleAndTextTuples) -> None:
        """Initiate the processor.

        Args:
            formatted_text: The text in a buffer but with formatting applied.

        """
        self.formatted_lines: list[StyleAndTextTuples] = []
        self.formatted_text = formatted_text
        super().__init__()

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        """Apply text formatting to a line in a buffer."""
        if not self.formatted_lines:
            self.formatted_lines = list(split_lines(self.formatted_text))
        lineno = transformation_input.lineno
        max_lineno = len(self.formatted_lines) - 1
        if lineno > max_lineno:
            lineno = max_lineno
        line = self.formatted_lines[lineno]
        return Transformation(line)


class FormattedTextArea(TextArea):
    """Apply formatted text to a TextArea."""

    _formatted_text: AnyFormattedText

    def _set_formatted_text(self, value: AnyFormattedText) -> None:
        self._formatted_text = value
        self.text = fragment_list_to_text(self.formatted_text)

    def __init__(
        self,
        formatted_text: AnyFormattedText,
        *args: Any,
        line_numbers: FilterOrBool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize a `FormattedTextArea` instance.

        Args:
            formatted_text: A list of `(style, text)` tuples to display.
            line_numbers: Determines if line numbers are shown,
            args: Arguments to pass to `prompt_toolkit.widgets.TextArea`.
            kwargs: Key-word arguments to pass to `prompt_toolkit.widgets.TextArea`.

        """
        self._formatted_text = formatted_text
        self.line_numbers = to_filter(line_numbers)
        input_processors = kwargs.pop("input_processors", [])
        input_processors.append(DynamicProcessor(self.get_processor))
        # The following is not type checked due to a currently open mypy bug
        # https://github.com/python/mypy/issues/6799
        super().__init__(
            *args,
            input_processors=input_processors,
            **kwargs,
        )  # type: ignore
        # Set the left margins
        self.window.left_margins = [
            ConditionalMargin(
                NumberedMargin(),
                self.line_numbers,
            )
        ]
        # Set the formatted text to display
        self._set_formatted_text(formatted_text)

    @property
    def formatted_text(self) -> StyleAndTextTuples:
        """The formatted text."""
        ft = to_formatted_text(self._formatted_text)
        text = fragment_list_to_text(ft)
        if self.text != text:
            self.text = text
        return ft

    @formatted_text.setter
    def formatted_text(self, value: AnyFormattedText) -> None:
        """Set the formatted text."""
        self._set_formatted_text(value)

    def get_processor(self) -> FormattedTextProcessor:
        """Generate a processor for the formatted text."""
        return FormattedTextProcessor(self.formatted_text)
