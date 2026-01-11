"""Tests for apptk.key_binding.bindings.named_commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from apptk.document import Document
from apptk.key_binding.bindings.named_commands import insert_comment, toggle_comments
from apptk.selection import SelectionState, SelectionType


class _FakeBuffer:
    """Minimal buffer-like object that keeps text, cursor and document in sync."""

    def __init__(
        self,
        text: str,
        cursor_position: int,
        selection_state: SelectionState | None,
    ) -> None:
        self._text = text
        self._cursor_position = cursor_position
        self.selection_state = selection_state
        self.document = Document(
            text,
            cursor_position,
            selection=selection_state,
        )
        self.validate_and_handle = MagicMock()

    @property
    def text(self) -> str:
        """Return the buffer text."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self.document = Document(value, min(self._cursor_position, len(value)))

    @property
    def cursor_position(self) -> int:
        """Return the cursor position."""
        return self._cursor_position

    @cursor_position.setter
    def cursor_position(self, value: int) -> None:
        self._cursor_position = value


def _make_event(
    text: str,
    cursor_position: int = 0,
    language: str | None = None,
    comment_prefix: str = "#",
    arg: int = 1,
    selection_start: int | None = None,
) -> MagicMock:
    """Create a mock KeyPressEvent with a real Document-backed buffer."""
    event = MagicMock()
    event.arg = arg
    event.arg_present = arg != 1

    if selection_start is not None:
        selection_state = SelectionState(selection_start, SelectionType.CHARACTERS)
    else:
        selection_state = None

    buffer = _FakeBuffer(text, cursor_position, selection_state)
    event.current_buffer = buffer

    control = MagicMock()
    control.language = language
    event.app.layout.current_control = control
    event.app.get_comment_prefix.return_value = comment_prefix

    return event


def test_toggle_comments_adds_comment_to_single_line() -> None:
    """Test that toggle_comments adds a comment to an uncommented line."""
    event = _make_event("hello", cursor_position=0, comment_prefix="#")
    toggle_comments(event)
    assert event.current_buffer.text == "# hello"


def test_toggle_comments_removes_comment_from_single_line() -> None:
    """Test that toggle_comments removes a comment from a commented line."""
    event = _make_event("# hello", cursor_position=0, comment_prefix="#")
    toggle_comments(event)
    assert event.current_buffer.text == "hello"


def test_toggle_comments_removes_comment_without_space() -> None:
    """Test that toggle_comments removes a comment token without trailing space."""
    event = _make_event("#hello", cursor_position=0, comment_prefix="#")
    toggle_comments(event)
    assert event.current_buffer.text == "hello"


def test_toggle_comments_preserves_indentation_when_commenting() -> None:
    """Test that indentation is preserved when adding comments."""
    text = "    hello\n    world"
    event = _make_event(
        text,
        cursor_position=0,
        comment_prefix="#",
        selection_start=len(text),
    )
    toggle_comments(event)
    assert event.current_buffer.text == "    # hello\n    # world"


def test_toggle_comments_preserves_indentation_when_uncommenting() -> None:
    """Test that indentation is preserved when removing comments."""
    text = "    # hello\n    # world"
    event = _make_event(
        text,
        cursor_position=0,
        comment_prefix="#",
        selection_start=len(text),
    )
    toggle_comments(event)
    assert event.current_buffer.text == "    hello\n    world"


def test_toggle_comments_with_non_hash_comment_prefix() -> None:
    """Test toggle_comments with a non-hash comment prefix like //."""
    event = _make_event("hello", cursor_position=0, comment_prefix="//")
    toggle_comments(event)
    assert event.current_buffer.text == "// hello"


def test_toggle_comments_uncomment_non_hash_prefix() -> None:
    """Test uncommenting with a non-hash comment prefix."""
    event = _make_event("// hello", cursor_position=0, comment_prefix="//")
    toggle_comments(event)
    assert event.current_buffer.text == "hello"


def test_toggle_comments_skips_blank_lines() -> None:
    """Test that blank lines are not commented."""
    text = "hello\n\nworld"
    event = _make_event(
        text,
        cursor_position=0,
        comment_prefix="#",
        selection_start=len(text),
    )
    toggle_comments(event)
    assert event.current_buffer.text == "# hello\n\n# world"


def test_insert_comment_comments_all_lines() -> None:
    """Test that insert_comment comments all lines with arg=1."""
    event = _make_event("hello\nworld", cursor_position=0, comment_prefix="#")
    insert_comment(event)
    buffer = event.current_buffer
    assert buffer.document.text == "# hello\n# world"
    buffer.validate_and_handle.assert_called_once()


def test_insert_comment_uncomments_all_lines() -> None:
    """Test that insert_comment uncomments all lines with arg != 1."""
    event = _make_event(
        "# hello\n# world", cursor_position=0, comment_prefix="#", arg=2
    )
    insert_comment(event)
    buffer = event.current_buffer
    assert buffer.document.text == "hello\nworld"
    buffer.validate_and_handle.assert_called_once()


def test_insert_comment_uncomments_without_space() -> None:
    """Test that insert_comment handles comment tokens without trailing space."""
    event = _make_event("#hello\n#world", cursor_position=0, comment_prefix="#", arg=2)
    insert_comment(event)
    buffer = event.current_buffer
    assert buffer.document.text == "hello\nworld"


def test_insert_comment_uses_language_aware_prefix() -> None:
    """Test that insert_comment uses the app's comment prefix."""
    event = _make_event("hello", cursor_position=0, comment_prefix="//")
    insert_comment(event)
    buffer = event.current_buffer
    assert buffer.document.text == "// hello"
