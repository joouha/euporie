"""Contain dpdated ANSI parsing and Formatted Text processing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.apptk.filters import to_filter
from euporie.apptk.formatted_text import (
    fragment_list_to_text,
    split_lines,
    to_formatted_text,
)
from euporie.apptk.layout.margins import ConditionalMargin, NumberedMargin
from euporie.apptk.layout.processors import DynamicProcessor, Processor, Transformation
from euporie.apptk.widgets import TextArea

if TYPE_CHECKING:
    from typing import Any

    from euporie.apptk.filters import FilterOrBool
    from euporie.apptk.formatted_text import AnyFormattedText, StyleAndTextTuples
    from euporie.apptk.layout.processors import TransformationInput

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
    """Display formatted text in a read-only TextArea."""

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
            args: Arguments to pass to `euporie.apptk.widgets.TextArea`.
            line_numbers: Determines if line numbers are shown.
            kwargs: Key-word arguments to pass to `euporie.apptk.widgets.TextArea`.

        """
        self._formatted_text: AnyFormattedText = formatted_text
        self._processor: FormattedTextProcessor | None = None
        self.line_numbers = to_filter(line_numbers)

        input_processors = [
            DynamicProcessor(self.get_processor),
            *kwargs.get("input_processors", []),
        ]

        kwargs.update(
            {
                "text": fragment_list_to_text(to_formatted_text(formatted_text)),
                "input_processors": input_processors,
                "read_only": True,
                "line_numbers": False,
            }
        )
        super().__init__(*args, **kwargs)

        self.window.left_margins.append(
            ConditionalMargin(NumberedMargin(), self.line_numbers)
        )

    @property
    def formatted_text(self) -> StyleAndTextTuples:
        """The formatted text."""
        return to_formatted_text(self._formatted_text)

    @formatted_text.setter
    def formatted_text(self, value: AnyFormattedText) -> None:
        """Set the formatted text and sync plain text."""
        self._formatted_text = value
        self._processor = None  # Invalidate cached processor
        self.text = fragment_list_to_text(to_formatted_text(value))

    def get_processor(self) -> FormattedTextProcessor:
        """Generate or return cached processor for the formatted text."""
        if self._processor is None:
            self._processor = FormattedTextProcessor(self.formatted_text)
        return self._processor
