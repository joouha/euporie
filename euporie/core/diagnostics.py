"""Contains container classes for diagnostic information."""

from __future__ import annotations

import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from typing import Literal

log = logging.getLogger(__name__)


class Diagnostic(NamedTuple):
    """Represent a diagnostic item for code."""

    code: str
    message: str
    level: Literal[0, 1, 2, 3, 4, 5]  # Like Python logging debug levels
    link: str
    lines: slice
    chars: slice


class Report(list[Diagnostic], metaclass=ABCMeta):
    """Class for storing a diagnostic report."""

    @classmethod
    def from_lsp(cls, text: str, outputs: list[dict]) -> Report:
        """Create a diagnostic report from LSP output."""
        items = []
        for output in outputs:
            # Calculate slice from range
            range_ = output.get("range", {})
            start = range_.get("start", {})
            end = range_.get("end", {})
            desc = output.get("codeDescription", {})
            items.append(
                Diagnostic(
                    code=output.get("code", ""),
                    message=output.get("message", ""),
                    level=5 - output.get("severity", 2),
                    link=desc.get("href"),
                    lines=slice(start.get("line"), end.get("line") + 1),
                    chars=slice(start.get("character"), end.get("character") + 1),
                )
            )
        return cls(items)

    @classmethod
    def from_reports(cls, *reports: Report) -> Report:
        """Initialize a new report."""
        return cls([diagnostic for report in reports for diagnostic in report])
