"""Buffer processors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from euporie.apptk.layout.utils import explode_text_fragments

from euporie.apptk.layout.processors import Processor, Transformation

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.formatted_text.base import StyleAndTextTuples

    from euporie.apptk.diagnostics import Report
    from euporie.apptk.layout.processors import TransformationInput


log = logging.getLogger(__name__)


class DiagnosticProcessor(Processor):
    """Highlight diagnostics."""

    def __init__(
        self,
        report: Report | Callable[[], Report],
        style: str = "underline",
    ) -> None:
        """Create a new processor instance."""
        self._report = report
        self.style = style

    @property
    def report(self) -> Report:
        """Return the current diagnostics report."""
        if callable(self._report):
            return self._report()
        return self._report

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """Underline the text ranges relating to diagnostics in the report."""
        line = ti.lineno
        fragments = ti.fragments
        self_style = self.style
        for item in self.report:
            if item.lines.start < line < item.lines.stop - 1:
                fragments = cast(
                    "StyleAndTextTuples",
                    [
                        (f"{style} {self.style}", text, *rest)
                        for style, text, *rest in fragments
                    ],
                )
            elif line == item.lines.start or line == item.lines.stop - 1:
                fragments = explode_text_fragments(fragments)
                start = item.chars.start if line == item.lines.start else 0
                end = (
                    item.chars.stop - 1
                    if line == item.lines.stop - 1
                    else len(fragments)
                )
                for i in range(start, min(len(fragments), end)):
                    fragments[i] = (
                        f"{fragments[i][0]} {self_style}",
                        *fragments[i][1:],
                    )

        return Transformation(fragments)
