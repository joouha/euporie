"""Tests for Pygments lexers and styles."""

from __future__ import annotations

from pygments.lexers import PythonLexer
from pygments.token import Generic, Keyword, Name

from euporie.core.pygments import ArgparseLexer, EuporiePygmentsStyle


def test_argparse_lexer_tokenizes_usage_line() -> None:
    """Argparse lexer correctly tokenizes the usage line."""
    code = "usage: my_program.py [-h] [--foo FOO] filename\n"
    tokens = list(ArgparseLexer().get_tokens(code))

    # Check program name is tokenized as Name.Namespace
    assert (Name.Namespace, "my_program.py") in tokens
    # Check short option is tokenized as Keyword
    assert (Keyword, "-h") in tokens
    # Check long option is tokenized as Keyword
    assert (Keyword, "--foo") in tokens


def test_argparse_lexer_tokenizes_section_headings() -> None:
    """Argparse lexer correctly tokenizes section headings."""
    code = "positional arguments:\n  filename\n\noptional arguments:\n  -h\n"
    tokens = list(ArgparseLexer().get_tokens(code))

    # Check section headings are tokenized as Generic.Heading
    assert (Generic.Heading, "positional arguments:") in tokens
    assert (Generic.Heading, "optional arguments:") in tokens


def test_argparse_lexer_tokenizes_options() -> None:
    """Argparse lexer correctly tokenizes options in help text."""
    code = "  -h, --help  show this help message\n  --foo FOO   description\n"
    tokens = list(ArgparseLexer().get_tokens(code))

    # Check options are tokenized as Keyword
    assert (Keyword, "-h") in tokens
    assert (Keyword, "--help") in tokens
    assert (Keyword, "--foo") in tokens


def test_argparse_lexer_preserves_text() -> None:
    """Argparse lexer preserves all input text."""
    code = "usage: prog [-h]\n\ndescription\n"
    tokens = list(ArgparseLexer().get_tokens(code))

    # Reconstruct text from tokens
    reconstructed = "".join(text for _, text in tokens)
    assert reconstructed == code


def test_euporie_pygments_style_has_required_tokens() -> None:
    """EuporiePygmentsStyle defines styles for common token types."""
    # Verify the style has definitions for important token types
    assert Keyword in EuporiePygmentsStyle.styles
    assert Name.Builtin in EuporiePygmentsStyle.styles
    assert Name.Function in EuporiePygmentsStyle.styles
    assert Generic.Heading in EuporiePygmentsStyle.styles


def test_python_lexer_with_euporie_style() -> None:
    """Python lexer works with EuporiePygmentsStyle."""
    code = "def foo(): pass\n"
    lexer = PythonLexer()
    tokens = list(lexer.get_tokens(code))

    # Verify basic tokenization works
    token_types = [t[0] for t in tokens]
    assert any(t for t in token_types if t in Keyword)

    # Verify style can be applied to all tokens without error
    for token_type, _ in tokens:
        # This should not raise - style should handle all token types
        EuporiePygmentsStyle.style_for_token(token_type)
