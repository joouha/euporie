"""Contain lexers for pygments."""

from __future__ import annotations

from typing import ClassVar

from pygments.lexer import RegexLexer
from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Literal,
    Name,
    Operator,
    Text,
    _TokenType,
)


class ArgparseLexer(RegexLexer):
    """A pygments lexer for agrparse help text."""

    name = "argparse"
    aliases: ClassVar[list[str]] = ["argparse"]
    filenames: ClassVar[list[str]] = []

    tokens: ClassVar[
        dict[str, list[tuple[str, _TokenType] | tuple[str, _TokenType, str]]]
    ] = {
        "root": [
            (r"(?<=usage: )[^\s]+", Name.Namespace),
            (r"\{", Operator, "options"),
            (r"[\[\{\|\}\]]", Operator),
            (r"((?<=\s)|(?<=\[))(--[a-zA-Z0-9-]+|-[a-zA-Z0-9-])", Keyword),
            (r"^(\w+\s)?\w+:", Generic.Heading),
            (r"\b(str|int|bool|UPath|loads)\b", Name.Builtin),
            (r"\b[A-Z]+_[A-Z]*\b", Name.Variable),
            (r"'.*?'", Literal.String),
            (r".", Text),
        ],
        "options": [
            (r"\d+", Literal.Number),
            (r",", Text),
            (r"[^\}]", Literal.String),
            (r"\}", Operator, "#pop"),
        ],
    }


class EuporiePygmentsStyle(Style):
    """ANSI color only pygments style.

    This is loosely based on Pygments' "native" style, modified to use ANSI colors
    instead of RGB. This adapts better to light/dark mode, because the built-in themes
    from a terminal are typically designed for whatever background is used.
    """

    styles: ClassVar[dict[_TokenType, str]] = {
        Comment: "italic ansibrightblack",
        Comment.Preproc: "noitalic bold ansired",
        Comment.Special: "noitalic bold ansired",
        Keyword: "bold ansigreen",
        Keyword.Pseudo: "nobold",
        Keyword.Constant: "nobold ansired",
        Operator.Word: "bold ansigreen",
        Literal.Date: "ansicyan",
        Literal.String: "ansiyellow",
        Literal.String.Other: "ansiyellow",
        Literal.Number: "ansibrightblue",
        Name.Builtin: "ansicyan",
        Name.Variable: "ansicyan",
        Name.Constant: "ansicyan",
        Name.Class: "underline ansibrightblue",
        Name.Function: "ansibrightblue",
        Name.Namespace: "underline ansibrightblue",
        Name.Exception: "noinherit bold",
        Name.Tag: "bold ansigreen",
        Name.Attribute: "noinherit",
        Name.Decorator: "ansiyellow",
        Generic.Heading: "bold",
        Generic.Subheading: "underline",
        Generic.Deleted: "ansired",
        Generic.Inserted: "ansigreen",
        Generic.Error: "ansired",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Traceback: "ansired",
        Error: "bold ansired",
    }
