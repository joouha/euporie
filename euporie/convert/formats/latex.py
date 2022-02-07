"""Contains function which convert LaTeXs to other formats."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.convert.base import register
from euporie.convert.util import commands_exist, have_modules

if TYPE_CHECKING:
    from typing import Optional

log = logging.getLogger(__name__)


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("flatlatex"),
)
def latex_to_ansi_py_flatlatex(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert LaTeX to ANSI using :py:mod:`flatlatex`."""
    import flatlatex  # type: ignore

    return flatlatex.converter().convert(data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("pylatexenc"),
)
def latex_to_ansi_py_pylatexenc(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert LaTeX to ANSI using :py:mod:`flatlatex`."""
    from pylatexenc.latex2text import LatexNodes2Text  # type: ignore

    return LatexNodes2Text().latex_to_text(data.strip().strip("$").strip())


@register(
    from_="latex",
    to="ansi",
    filter_=have_modules("sympy", "antlr4"),
)
def latex_to_ansi_py_sympy(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "str":
    """Convert LaTeX to ANSI using :py:mod:`sympy`."""
    from sympy import pretty  # type: ignore
    from sympy.parsing.latex import parse_latex  # type: ignore
    from sympy.parsing.latex.errors import LaTeXParsingError  # type: ignore

    from euporie.log import log_to_stdout

    with log_to_stdout(log):
        try:
            parsed = parse_latex(data.strip().strip("$").strip())
        except LaTeXParsingError:
            parsed = data
    return pretty(parsed)


@register(
    from_="latex",
    to="png",
    filter_=commands_exist("dvipng") & have_modules("IPython"),
)
def latex_to_png_py_ipython_dvipng(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Converts LaTeX data to PNG bytes with :py:mod:`IPython` & :command:`dvipng`."""
    from IPython.lib.latextools import latex_to_png  # type: ignore

    return latex_to_png(
        data, encode=False, backend="dvipng", **({"color": fg} if fg else {})
    )


@register(
    from_="latex",
    to="png",
    filter_=have_modules("IPython", "matplotlib"),
)
def latex_to_png_py_ipython_mpl(
    data: "str",
    width: "Optional[int]" = None,
    height: "Optional[int]" = None,
    fg: "Optional[str]" = None,
    bg: "Optional[str]" = None,
) -> "bytes":
    """Converts LaTeX data to PNG bytes with :py:mod:`IPython` & :py:mod:`matplotlib`."""
    from IPython.lib.latextools import latex_to_png  # type: ignore

    return latex_to_png(
        data, encode=False, backend="dvipng", **({"color": fg} if fg else {})
    )
