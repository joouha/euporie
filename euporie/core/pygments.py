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
    """Version of pygment's "native" style which works better on light backgrounds."""

    styles: ClassVar[dict[_TokenType, str]] = {
        Comment: "italic #888888",
        Comment.Preproc: "noitalic bold #cd2828",
        Comment.Special: "noitalic bold #e50808 bg:#520000",
        Keyword: "bold #6ebf26",
        Keyword.Pseudo: "nobold",
        Keyword.Constant: "nobold #ff3d3d",
        Operator.Word: "bold #6ebf26",
        Literal.Date: "#2fbccd",
        Literal.String: "#ed9d13",
        Literal.String.Other: "#ffa500",
        Literal.Number: "#51b2fd",
        Name.Builtin: "#2fbccd",
        Name.Variable: "#40ffff",
        Name.Constant: "#40ffff",
        Name.Class: "underline #71adff",
        Name.Function: "#71adff",
        Name.Namespace: "underline #71adff",
        Name.Exception: "noinherit bold",
        Name.Tag: "bold #6ebf26",
        Name.Attribute: "noinherit",
        Name.Decorator: "#ffa500",
        Generic.Heading: "bold",
        Generic.Subheading: "underline",
        Generic.Deleted: "#d22323",
        Generic.Inserted: "#589819",
        Generic.Error: "#d22323",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Traceback: "#d22323",
        Error: "bold bg:#a61717 #ffffff",
    }
