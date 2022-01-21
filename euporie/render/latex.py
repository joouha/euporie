"""Contains renderer classes which render LaTeX."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.render.base import DataRenderer
from euporie.render.mixin import PythonRenderMixin

if TYPE_CHECKING:
    from typing import Any, Union

__all__ = ["LatexRenderer", "latex_sympy_py", "latex_flatlatex_py"]

log = logging.getLogger(__name__)


class LatexRenderer(DataRenderer):
    """Collection of renderers for LaTeX."""


class latex_sympy_py(PythonRenderMixin, LatexRenderer):
    """Renders LaTeX using :py:mod:`sympy`."""

    priority = 0
    modules = ["sympy", "antlr4"]

    def process(self, data: "str") -> "Union[bytes, str]":
        """Converts LaTeX code to a unicode string.

        Args:
            data: An LaTeX string.

        Returns:
            An ANSI string representing the rendered input.

        """
        from sympy import pretty  # type: ignore
        from sympy.parsing.latex import parse_latex  # type: ignore
        from sympy.parsing.latex.errors import LaTeXParsingError  # type: ignore

        from euporie.log import log_to_stdout

        with log_to_stdout(log):
            try:
                parsed = parse_latex(data.strip("$"))
            except LaTeXParsingError:
                parsed = data
        return pretty(parsed)


class latex_flatlatex_py(PythonRenderMixin, LatexRenderer):
    """Renders LaTeX using :py:mod:`flatlatex`."""

    priority = 1
    modules = ["flatlatex"]

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Initiates the renderer."""
        import flatlatex  # type: ignore

        super().__init__(*args, **kwargs)
        self.convertor = flatlatex.converter()

    def process(self, data: "str") -> "Union[bytes, str]":
        """Converts LaTeX code to a unicode string.

        Args:
            data: An LaTeX string.

        Returns:
            An ANSI string representing the rendered input.

        """
        return self.convertor.convert(data.strip("$"))
