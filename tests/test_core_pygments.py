"""Tests for Pygments lexers and styles."""

from __future__ import annotations

from pygments import highlight
from pygments.formatters.terminal256 import TerminalTrueColorFormatter
from pygments.lexers import PythonLexer

from euporie.core.pygments import ArgparseLexer, EuporiePygmentsStyle


def test_argparse_lexer() -> None:
    """Argparse lexer output is as expected."""
    code = """usage: my_program.py [-h] [--foo FOO] [--bar BAR] filename

description

positional arguments:
  filename

optional arguments:
  -h, --help  show this help message and exit
  --foo FOO   description of foo
  --bar BAR   description of bar
"""
    expected_output = "\x1b[01musage:\x1b[00m \x1b[38;2;113;173;255;04mmy_program.py\x1b[39;00m [\x1b[38;2;110;191;38;01m-h\x1b[39;00m] [\x1b[38;2;110;191;38;01m--foo\x1b[39;00m FOO] [\x1b[38;2;110;191;38;01m--bar\x1b[39;00m BAR] filename\n\ndescription\n\n\x1b[01mpositional arguments:\x1b[00m\n  filename\n\n\x1b[01moptional arguments:\x1b[00m\n  \x1b[38;2;110;191;38;01m-h\x1b[39;00m, \x1b[38;2;110;191;38;01m--help\x1b[39;00m  show this help message and exit\n  \x1b[38;2;110;191;38;01m--foo\x1b[39;00m FOO   description of foo\n  \x1b[38;2;110;191;38;01m--bar\x1b[39;00m BAR   description of bar\n"

    result = highlight(
        code,
        ArgparseLexer(),
        TerminalTrueColorFormatter(style=EuporiePygmentsStyle),
    )
    assert result == expected_output


def test_python_lexer() -> None:
    """Python code is highlighted as expected."""
    code = """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
    expected_output = """\x1b[38;2;110;191;38;01mdef\x1b[39;00m \x1b[38;2;113;173;255mfibonacci\x1b[39m(n: \x1b[38;2;47;188;205mint\x1b[39m) -> \x1b[38;2;47;188;205mint\x1b[39m:\n    \x1b[38;2;110;191;38;01mif\x1b[39;00m n <= \x1b[38;2;81;178;253m1\x1b[39m:\n        \x1b[38;2;110;191;38;01mreturn\x1b[39;00m n\n    \x1b[38;2;110;191;38;01mreturn\x1b[39;00m fibonacci(n-\x1b[38;2;81;178;253m1\x1b[39m) + fibonacci(n-\x1b[38;2;81;178;253m2\x1b[39m)\n"""
    result = highlight(
        code,
        PythonLexer(),
        TerminalTrueColorFormatter(style=EuporiePygmentsStyle),
    )
    assert result == expected_output
