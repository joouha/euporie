"""Tests for apptk.formatted_text.utils."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apptk.formatted_text.utils import merge

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from apptk.mouse_events import MouseEvent


def test_merge_fragments_empty() -> None:
    """Test that merging an empty list returns an empty list."""
    assert merge([]) == []


def test_merge_fragments_single() -> None:
    """Test that a single fragment is returned unchanged."""
    ft = [("bold", "hello")]
    assert merge(ft) == [("bold", "hello")]


def test_merge_fragments_same_style() -> None:
    """Test that adjacent fragments with the same style are merged."""
    ft = [("bold", "hel"), ("bold", "lo")]  # codespell:ignore hel
    assert merge(ft) == [("bold", "hello")]


def test_merge_fragments_different_style() -> None:
    """Test that fragments with different styles are not merged."""
    ft = [("bold", "hel"), ("italic", "lo")]  # codespell:ignore hel
    assert merge(ft) == [("bold", "hel"), ("italic", "lo")]  # codespell:ignore hel


def test_merge_fragments_normalized_style() -> None:
    """Test that fragments with extra whitespace in style are merged."""
    ft = [("bold italic", "hel"), ("bold  italic", "lo")]  # codespell:ignore hel
    result = merge(ft)
    assert len(result) == 1
    assert result[0][1] == "hello"
    # The first fragment's original style is preserved
    assert result[0][0] == "bold italic"


def test_merge_fragments_different_order_not_merged() -> None:
    """Test that fragments with reordered style tokens are not merged."""
    ft = [("bold italic", "hel"), ("italic bold", "lo")]  # codespell:ignore hel
    result = merge(ft)
    assert len(result) == 2
    assert result[0] == ("bold italic", "hel")  # codespell:ignore hel
    assert result[1] == ("italic bold", "lo")


def test_merge_fragments_multiple_groups() -> None:
    """Test merging with multiple groups of same-style fragments."""
    ft = [
        ("bold", "a"),
        ("bold", "b"),
        ("italic", "c"),
        ("italic", "d"),
        ("bold", "e"),
    ]
    result = merge(ft)
    assert result == [("bold", "ab"), ("italic", "cd"), ("bold", "e")]


def test_merge_fragments_with_mouse_handler() -> None:
    """Test that fragments with different mouse handlers are not merged."""

    def handler_a(e: MouseEvent) -> NotImplementedOrNone:
        return None

    def handler_b(e: MouseEvent) -> NotImplementedOrNone:
        return None

    ft = [
        ("bold", "a", handler_a),
        ("bold", "b", handler_a),
        ("bold", "c", handler_b),
    ]
    result = merge(ft)
    assert len(result) == 2
    assert result[0] == ("bold", "ab", handler_a)
    assert result[1] == ("bold", "c", handler_b)


def test_merge_fragments_preserves_zero_width() -> None:
    """Test that zero-width fragments are handled correctly."""
    ft = [
        ("bold", "hello"),
        ("[ZeroWidthEscape]", "\x1b[0m"),
        ("bold", " world"),
    ]
    result = merge(ft)
    # Zero-width fragment has a different normalized style, so no merging across it
    assert len(result) == 3


def test_merge_fragments_unstyled() -> None:
    """Test that unstyled fragments are preserved."""
    ft = [("", "hello"), ("", " "), ("", "world")]
    result = merge(ft)
    assert result == [("", "hello world")]


def test_merge_fragments_unstyled_empty_text() -> None:
    """Test that unstyled fragments with empty text are preserved."""
    ft = [("bold", "hello"), ("", ""), ("bold", " world")]
    result = merge(ft)
    # The empty unstyled fragment breaks the merge
    assert len(result) == 3
    assert result[0] == ("bold", "hello")
    assert result[1] == ("", "")
    assert result[2] == ("bold", " world")
