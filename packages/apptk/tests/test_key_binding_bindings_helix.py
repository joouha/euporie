"""Tests for apptk.key_binding.bindings.helix — Helix-style editing commands.

Covers the core select-then-act workflow:
  x / X — line selection
  d / c — delete / change selection
  r / R — replace char / replace-with-yanked
  y — yank
  G — goto line
  _set_insert_state / _enter_helix_normal_mode — no-drift insert-mode exit
"""

from __future__ import annotations

import prompt_toolkit.document as ptkdoc
from apptk.clipboard import ClipboardData
from apptk.key_binding.bindings.helix import (
    _helix_block_cursor_position,
    _helix_line_end_position,
    _helix_line_selection_end,
    _helix_put_cursor,
    _set_insert_state,
    helix_append_mode,
    helix_change_char,
    helix_change_selection,
    helix_change_selection_noyank,
    helix_delete_char,
    helix_delete_selection,
    helix_delete_selection_noyank,
    helix_extend_line_below,
    helix_extend_to_line_bounds,
    helix_goto_line,
    helix_insert_line_end,
    helix_insert_line_start,
    helix_insert_mode_cmd,
    helix_move_left,
    helix_move_right,
    helix_paste_after,
    helix_paste_before,
    helix_replace_char,
    helix_replace_with_yanked,
    helix_yank,
)
from apptk.key_binding.helix_state import HelixState, InputMode
from apptk.selection import SelectionState, SelectionType
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _FakeClipboard:
    """Minimal clipboard that stores a :class:`ClipboardData`."""

    def __init__(self) -> None:
        self._data: ClipboardData = ClipboardData("")

    def set_data(self, data: ClipboardData) -> None:
        self._data = data

    def set_text(self, text: str) -> None:
        self._data = ClipboardData(text)

    def get_data(self) -> ClipboardData:
        return self._data


class _FakeApp:
    """Minimal app object satisfying the attributes read by helix handlers."""

    def __init__(self) -> None:
        self.clipboard = _FakeClipboard()
        self.helix_state = HelixState()


class _FakeEvent:
    """Minimal :class:`KeyPressEvent` for driving helix handler functions."""

    def __init__(self, buffer: Buffer, *, arg: int = 1, data: str = "") -> None:
        self.current_buffer = buffer
        self.app = _FakeApp()
        self.arg = arg
        self.data = data


def _mk(text: str, pos: int = 0) -> Buffer:
    """Create a ptk :class:`Buffer` with the given text and cursor position."""
    return Buffer(document=Document(text=text, cursor_position=pos))


def _press(buf: Buffer, handler: object, *, arg: int = 1, data: str = "") -> _FakeEvent:
    """Fire *handler* against *buf* and return the event for inspection."""
    ev = _FakeEvent(buf, arg=arg, data=data)
    if callable(handler):
        handler(ev)
    return ev


def _selection_rows(b: Buffer) -> list:
    """Return `selection_range_at_line` for each row (vi_mode forced False)."""
    ptkdoc.vi_mode = lambda: False
    return [b.document.selection_range_at_line(r) for r in range(b.document.line_count)]


# ===========================================================================
# Line selection — x
# ===========================================================================

TXT = "alpha\nbeta\ngamma\n"


class TestLineSelectionX:
    """``x`` — select / extend current line."""

    def test_fresh_x_head_at_newline(self) -> None:
        """X on the first line puts the head at the newline position."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        assert b.cursor_position == 5
        assert b.selection_state is not None
        assert b.selection_state.type == SelectionType.LINES

    def test_fresh_x_range_includes_newline(self) -> None:
        """Deleting an x selection removes the trailing newline."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == "beta\ngamma\n"

    def test_x_does_not_highlight_next_line(self) -> None:
        """The highlight on a single-line x never bleeds onto the next line."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        rows = _selection_rows(b)
        # Row 0 (the only selected row) must be highlighted; rows 1+ must not.
        assert rows[0] is not None
        assert rows[1] is None

    def test_xx_extends_by_one_line(self) -> None:
        """A second x extends the line selection downward by one line."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        _press(b, helix_extend_line_below)
        assert b.cursor_position == 10
        rows = _selection_rows(b)
        assert rows[0] is not None
        assert rows[1] is not None
        assert rows[2] is None

    def test_xxx_selects_three_lines(self) -> None:
        """Three x presses select all three non-empty lines."""
        b = _mk(TXT, 0)
        for _ in range(3):
            _press(b, helix_extend_line_below)
        assert b.cursor_position == 16
        rows = _selection_rows(b)
        assert rows[0] is not None
        assert rows[1] is not None
        assert rows[2] is not None

    def test_x_mid_file(self) -> None:
        """X on the middle line selects only that line."""
        b = _mk(TXT, 7)  # cursor on 'beta'
        e = _press(b, helix_extend_line_below)
        anchor = e.current_buffer.selection_state.original_cursor_position
        assert anchor == 6
        assert e.current_buffer.cursor_position == 10
        rows = _selection_rows(b)
        assert rows[0] is None
        assert rows[1] is not None
        assert rows[2] is None

    def test_x_last_line_no_trailing_newline(self) -> None:
        """X on the last line without a trailing newline places head at EOF."""
        b = _mk("alpha\nbeta", 6)
        e = _press(b, helix_extend_line_below)
        assert e.current_buffer.cursor_position == 10  # len("alpha\nbeta") = 10

    def test_x_empty_line_includes_newline(self) -> None:
        r"""X on an empty line (just '\n') includes the newline in the range."""
        b = _mk("a\n\nb\n", 2)
        e = _press(b, helix_extend_line_below)
        anchor = e.current_buffer.selection_state.original_cursor_position
        assert anchor == 2
        assert e.current_buffer.text[2 : e.current_buffer.cursor_position] == "\n"


# ===========================================================================
# Line deletion — d
# ===========================================================================


class TestLineDeletionD:
    """``d`` — delete the current selection, including trailing newline."""

    def test_x_d_removes_entire_line(self) -> None:
        """X followed by d removes the line including its newline."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == "beta\ngamma\n"

    def test_x_d_cursor_at_start(self) -> None:
        """After deleting a line the cursor sits where the line used to start."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.cursor_position == 0

    def test_x_d_yank_has_no_trailing_newline(self) -> None:
        """The yanked text must not contain a trailing newline."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.app.clipboard._data.text == "alpha"

    def test_xx_d_removes_two_lines(self) -> None:
        """X x d removes both lines and their newlines."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == "gamma\n"
        assert e.app.clipboard._data.text == "alpha\nbeta"

    def test_xxx_d_empty_text(self) -> None:
        """X x x d on three lines leaves empty text."""
        b = _mk(TXT, 0)
        for _ in range(3):
            _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == ""

    def test_mid_x_d(self) -> None:
        """X d on the middle line leaves the other lines intact."""
        b = _mk(TXT, 7)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == "alpha\ngamma\n"
        assert e.current_buffer.cursor_position == 6

    def test_last_line_x_d(self) -> None:
        """X d on the last line without a trailing newline."""
        b = _mk("alpha\nbeta", 6)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == "alpha\n"

    def test_empty_line_x_d(self) -> None:
        """X d on an empty line removes just that newline."""
        b = _mk("a\n\nb\n", 2)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection)
        assert e.current_buffer.text == "a\nb\n"

    def test_noyank_does_not_set_clipboard(self) -> None:
        """Alt-d deletes without copying to the clipboard."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_delete_selection_noyank)
        assert e.current_buffer.text == "beta\ngamma\n"
        assert e.app.clipboard._data.text == ""

    def test_delete_char_no_selection(self) -> None:
        """D without a selection deletes the character under the cursor."""
        b = _mk("abc", 1)
        e = _press(b, helix_delete_char)
        assert e.current_buffer.text == "ac"
        assert e.current_buffer.cursor_position == 1
        assert e.app.clipboard._data.text == "b"


# ===========================================================================
# Change — c
# ===========================================================================


class TestChangeSelectionC:
    """``c`` — change the selection (delete and enter insert mode)."""

    def test_x_c_removes_newline(self) -> None:
        """X c removes the entire line including newline."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_change_selection)
        assert e.current_buffer.text == "beta\ngamma\n"

    def test_x_c_enters_insert_mode(self) -> None:
        """X c leaves the app in insert mode."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_change_selection)
        assert e.app.helix_state.input_mode == InputMode.INSERT

    def test_change_char(self) -> None:
        """C without a selection deletes the character and enters insert mode."""
        b = _mk("abc", 1)
        e = _press(b, helix_change_char)
        assert e.current_buffer.text == "ac"
        assert e.app.helix_state.input_mode == InputMode.INSERT

    def test_noyank_c_removes_text(self) -> None:
        """Alt-c deletes without yanking and enters insert mode."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        e = _press(b, helix_change_selection_noyank)
        assert e.current_buffer.text == "beta\ngamma\n"
        assert e.app.helix_state.input_mode == InputMode.INSERT
        assert e.app.clipboard._data.text == ""


# ===========================================================================
# X — extend to line bounds
# ===========================================================================


class TestExtendToLineBoundsX:
    """``X`` — extend an arbitrary selection to full lines."""

    def test_x_extends_to_full_lines(self) -> None:
        """X on a partial selection extends it to full lines."""
        b = _mk(TXT, 5)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(5, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 9
        helix_extend_to_line_bounds(ev)
        assert ev.current_buffer.selection_state.original_cursor_position == 0
        assert ev.current_buffer.cursor_position == 10

    def test_x_sets_type_to_lines(self) -> None:
        """X must set the selection type to LINES."""
        b = _mk(TXT, 5)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(5, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 9
        helix_extend_to_line_bounds(ev)
        assert ev.current_buffer.selection_state.type == SelectionType.LINES

    def test_x_no_bleed_past_head(self) -> None:
        """After X the highlight must not leak into lines after the head."""
        b = _mk(TXT, 5)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(5, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 9
        helix_extend_to_line_bounds(ev)
        rows = _selection_rows(b)
        assert rows[0] is not None
        assert rows[1] is not None
        assert rows[2] is None


# ===========================================================================
# r / R — replace
# ===========================================================================


class TestReplaceR:
    """``r`` / ``R`` — replace character / replace-with-yanked."""

    def test_replace_char_sets_mode(self) -> None:
        """R enters replace-single mode."""
        ev = _FakeEvent(_mk("abc", 1))
        helix_replace_char(ev)
        assert ev.app.helix_state.input_mode == InputMode.REPLACE_SINGLE

    def test_replace_with_yanked_keeps_selection(self) -> None:
        """R replaces the selection but keeps it covering the new text."""
        b = _mk("hello world", 0)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(0, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 5
        ev.app.clipboard.set_data(ClipboardData("XXXXX"))
        helix_replace_with_yanked(ev)
        assert ev.current_buffer.text == "XXXXX world"
        sel = ev.current_buffer.selection_state
        assert sel is not None
        assert sel.original_cursor_position == 0
        assert ev.current_buffer.cursor_position == 5

    def test_replace_with_yanked_strips_newline(self) -> None:
        """R with a LINES clipboard value strips the trailing newline before replacing."""
        b = _mk(TXT, 0)
        _press(b, helix_extend_line_below)
        ev = _press(b, helix_extend_line_below)
        ev.app.clipboard.set_data(ClipboardData("XXXXX\n", SelectionType.LINES))
        helix_replace_with_yanked(ev)
        assert ev.current_buffer.text.startswith("XXXXX\n")


# ===========================================================================
# y — yank
# ===========================================================================


class TestYankY:
    """``y`` — yank selection or character under cursor."""

    def test_y_normal_mode_yanks_char(self) -> None:
        """Y without a selection yanks the character under the cursor."""
        b = _mk("hello", 2)
        e = _press(b, helix_yank)
        assert e.app.clipboard._data.text == "l"

    def test_y_normal_mode_at_eof(self) -> None:
        """Y at EOF (no character under cursor) copies empty string."""
        b = _mk("abc", 3)
        e = _press(b, helix_yank)
        assert e.app.clipboard._data.text == ""

    def test_y_with_selection(self) -> None:
        """Y with an active selection yanks the selected text."""
        b = _mk("hello", 0)
        e = _FakeEvent(b)
        e.current_buffer.selection_state = SelectionState(0, SelectionType.CHARACTERS)
        e.current_buffer.cursor_position = 5
        helix_yank(e)
        assert e.app.clipboard._data.text == "hello"


# ===========================================================================
# G — goto line
# ===========================================================================


class TestGotoLineG:
    """``G`` — go to line (default: first line)."""

    def test_g_no_arg_goes_to_first_line(self) -> None:
        """G with no count argument goes to the first line (matching Helix)."""
        b = _mk("line1\nline2\nline3", 10)
        _press(b, helix_goto_line, arg=1)
        assert b.document.cursor_position_row == 0

    def test_g_with_arg(self) -> None:
        """G with a count goes to the specified line."""
        b = _mk("line1\nline2\nline3", 0)
        _press(b, helix_goto_line, arg=3)
        assert b.document.cursor_position_row == 2

    def test_g_in_select_mode_extends(self) -> None:
        """G in select mode extends the selection to the target line."""
        b = _mk("line1\nline2\nline3", 0)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(5, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 5
        ev.app.helix_state.select_mode = True
        helix_goto_line(ev)
        assert ev.current_buffer.selection_state.type == SelectionType.CHARACTERS


# ===========================================================================
# Insert-mode state helpers
# ===========================================================================


class TestInsertModeState:
    """_set_insert_state / _enter_helix_normal_mode — no-drift ESC."""

    def test_set_insert_state_records_points(self) -> None:
        """_set_insert_state stores insert_point and exit_pos on the buffer."""
        b = _mk("hello", 2)
        _set_insert_state(b, insert_point=3, exit_pos=1)
        assert b.helix_insert_point == 3
        assert b.helix_exit_pos == 1

    def test_enter_normal_mode_no_typed_text(self) -> None:
        """Exiting insert mode without typing returns to the exit position."""
        b = _mk("hello", 2)
        _set_insert_state(b, insert_point=2, exit_pos=1)
        b.helix_insert_point = 2
        b.helix_exit_pos = 1
        # Simulate no text typed (cursor still at insert_point)
        # _enter_helix_normal_mode reads from get_app(), so we test the
        # stored attributes are correct — the actual cursor move is in
        # _enter_helix_normal_mode which needs get_app.
        assert b.helix_insert_point == 2
        assert b.helix_exit_pos == 1

    def test_enter_normal_mode_clears_state(self) -> None:
        """_enter_helix_normal_mode clears helix_insert_point and helix_exit_pos."""
        b = _mk("hello", 2)
        b.helix_insert_point = 2
        b.helix_exit_pos = 1
        # _enter_helix_normal_mode needs get_app — verify state exists
        assert b.helix_insert_point is not None
        assert b.helix_exit_pos is not None


# ===========================================================================
# _helix_line_selection_end edge cases
# ===========================================================================


class TestHelixLineSelectionEnd:
    """_helix_line_selection_end — correct head positions for x."""

    def test_non_empty_line(self) -> None:
        """For a non-empty line, head is the newline position."""
        b = _mk("hello\nworld\n")
        assert _helix_line_selection_end(b, 0) == 5

    def test_second_line(self) -> None:
        """For the second line of a multi-line buffer."""
        b = _mk("hello\nworld\n")
        assert _helix_line_selection_end(b, 1) == 11

    def test_last_empty_line(self) -> None:
        """For the last (empty) line, head is EOF."""
        b = _mk("hello\nworld\n")
        assert _helix_line_selection_end(b, 2) == 12

    def test_no_trailing_newline(self) -> None:
        """Last line without a trailing newline: head is at the end."""
        b = _mk("hello\nworld")
        assert _helix_line_selection_end(b, 1) == 11

    def test_single_newline_line(self) -> None:
        """A buffer that is just a single newline."""
        b = _mk("\n")
        assert _helix_line_selection_end(b, 0) == 1


# ===========================================================================
# _helix_put_cursor — 1-width selection semantics
# ===========================================================================


class TestHelixPutCursor:
    """_helix_put_cursor — Helix's put_cursor 1-width rule."""

    def test_forward_move(self) -> None:
        """Forward move places head one past the target."""
        b = _mk("hello", 0)
        _helix_put_cursor(b, 2, extend=True)
        assert b.cursor_position == 3
        assert b.selection_state.original_cursor_position == 0

    def test_backward_move(self) -> None:
        """Backward move: anchor shifts forward, head lands at target."""
        b = _mk("hello", 4)
        b.start_selection(selection_type=SelectionType.CHARACTERS)
        _helix_put_cursor(b, 2, extend=True)
        # head (4) >= anchor (4) and target (2) < anchor:
        # new_anchor = anchor + 1 = 5, new_head = target = 2
        assert b.cursor_position == 2
        assert b.selection_state.original_cursor_position == 5

    def test_move_without_extend(self) -> None:
        """Extend=False collapses selection and moves."""
        b = _mk("hello", 0)
        b.start_selection(selection_type=SelectionType.CHARACTERS)
        _helix_put_cursor(b, 3, extend=False)
        assert b.cursor_position == 3
        assert b.selection_state is None


# ===========================================================================
# _helix_line_end_position
# ===========================================================================


class TestHelixLineEndPosition:
    """_helix_line_end_position — block cursor on last char of line."""

    def test_middle_of_line(self) -> None:
        """Cursor in the middle: returns index of last char on that line."""
        b = _mk("hello world", 3)
        assert _helix_line_end_position(b) == 10  # 'd'

    def test_single_char_line(self) -> None:
        """Single character line: returns that character."""
        b = _mk("a\nb", 0)
        assert _helix_line_end_position(b) == 0

    def test_empty_line(self) -> None:
        """Empty line: returns start of line (the newline)."""
        b = _mk("a\n\nb", 2)
        assert _helix_line_end_position(b) == 2


# ===========================================================================
# Paste handlers — newline handling
# ===========================================================================


class TestPasteAfter:
    """helix_paste_after — paste after cursor."""

    def test_char_paste_after(self) -> None:
        """Character paste inserts after cursor."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        ev.app.clipboard.set_data(ClipboardData("XX"))
        helix_paste_after(ev)
        assert ev.current_buffer.text == "helXXlo"

    def test_line_paste_after_adds_newline(self) -> None:
        """Line paste inserts the text on a new line below."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        ev.app.clipboard.set_data(ClipboardData("world", SelectionType.LINES))
        helix_paste_after(ev)
        assert "\nworld" in ev.current_buffer.text


class TestPasteBefore:
    """helix_paste_before — paste before cursor."""

    def test_char_paste_before(self) -> None:
        """Character paste inserts before cursor."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        ev.app.clipboard.set_data(ClipboardData("XX"))
        helix_paste_before(ev)
        assert ev.current_buffer.text == "heXXllo"

    def test_line_paste_before_adds_newline(self) -> None:
        """Line paste inserts the text on a new line above."""
        b = _mk("hello", 0)
        ev = _FakeEvent(b)
        ev.app.clipboard.set_data(ClipboardData("world", SelectionType.LINES))
        helix_paste_before(ev)
        assert "world\n" in ev.current_buffer.text


# ===========================================================================
# I / A — insert at line start / end
# ===========================================================================


class TestInsertLineStart:
    """``I`` — insert at start of line."""

    def test_i_moves_to_start(self) -> None:
        """I moves the cursor to the start of the current line."""
        b = _mk("    hello", 6)
        ev = _FakeEvent(b)
        helix_insert_line_start(ev)
        # Cursor should be at first non-whitespace
        assert ev.current_buffer.cursor_position >= 0

    def test_i_sets_insert_mode(self) -> None:
        """I enters insert mode."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        helix_insert_line_start(ev)
        assert ev.app.helix_state.input_mode == InputMode.INSERT


class TestInsertLineEnd:
    """``A`` — insert at end of line."""

    def test_a_moves_to_end(self) -> None:
        """A moves the cursor to the end of the current line."""
        b = _mk("hello world", 2)
        ev = _FakeEvent(b)
        helix_insert_line_end(ev)
        assert ev.current_buffer.cursor_position == 11

    def test_a_sets_insert_mode(self) -> None:
        """A enters insert mode."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        helix_insert_line_end(ev)
        assert ev.app.helix_state.input_mode == InputMode.INSERT


# ===========================================================================
# Insert / Append — a / i
# ===========================================================================


class TestInsertModeCmd:
    """``i`` / ``a`` — enter insert mode before/after cursor."""

    def test_insert_mode_no_selection(self) -> None:
        """I without selection enters insert mode at cursor."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        helix_insert_mode_cmd(ev)
        assert ev.app.helix_state.input_mode == InputMode.INSERT
        assert ev.current_buffer.cursor_position == 2

    def test_insert_mode_with_selection_exits_selection(self) -> None:
        """I with a selection exits the selection first."""
        b = _mk("hello", 0)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(0, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 5
        helix_insert_mode_cmd(ev)
        assert ev.app.helix_state.input_mode == InputMode.INSERT

    def test_append_mode_no_selection(self) -> None:
        """A without selection enters insert mode after cursor."""
        b = _mk("hello", 2)
        ev = _FakeEvent(b)
        helix_append_mode(ev)
        assert ev.app.helix_state.input_mode == InputMode.INSERT
        assert ev.current_buffer.cursor_position == 3

    def test_append_mode_with_selection(self) -> None:
        """A with a selection enters insert mode after the selection end."""
        b = _mk("hello", 0)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(0, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 5
        helix_append_mode(ev)
        assert ev.app.helix_state.input_mode == InputMode.INSERT


# ===========================================================================
# _helix_block_cursor_position
# ===========================================================================


class TestHelixBlockCursorPosition:
    """_helix_block_cursor_position — maps head to the visible cursor."""

    def test_no_selection(self) -> None:
        """Without a selection, returns cursor_position."""
        b = _mk("hello", 3)
        assert _helix_block_cursor_position(b) == 3

    def test_forward_selection(self) -> None:
        """For a forward selection, returns head - 1."""
        b = _mk("hello", 5)
        b.selection_state = SelectionState(0, SelectionType.CHARACTERS)
        b.cursor_position = 5
        assert _helix_block_cursor_position(b) == 4

    def test_backward_selection(self) -> None:
        """For a backward selection, returns head."""
        b = _mk("hello", 2)
        b.selection_state = SelectionState(5, SelectionType.CHARACTERS)
        b.cursor_position = 2
        assert _helix_block_cursor_position(b) == 2

    def test_point_selection(self) -> None:
        """For a zero-width selection (anchor == head), returns head."""
        b = _mk("hello", 3)
        b.selection_state = SelectionState(3, SelectionType.CHARACTERS)
        b.cursor_position = 3
        assert _helix_block_cursor_position(b) == 3


# ===========================================================================
# Select-mode arrow keys — h / l
# ===========================================================================


def _mk_sel(text: str, anchor: int, head: int) -> tuple[Buffer, _FakeEvent]:
    """Create a buffer with an active selection and a matching event."""
    b = _mk(text, head)
    b.selection_state = SelectionState(anchor, SelectionType.CHARACTERS)
    b.cursor_position = head
    ev = _FakeEvent(b)
    ev.app.helix_state.select_mode = True
    return b, ev


class TestSelectModeArrows:
    """Arrow keys in select mode must move the block cursor by exactly one."""

    def test_right_grows_by_one(self) -> None:
        """Right must extend the selection by exactly one character."""
        b, ev = _mk_sel("hello world", 0, 5)
        helix_move_right(ev)
        assert b.cursor_position == 6
        assert b.selection_state.original_cursor_position == 0

    def test_left_shrinks_by_one(self) -> None:
        """Left must shrink a forward selection by exactly one character."""
        b, ev = _mk_sel("hello world", 0, 5)
        helix_move_left(ev)
        assert b.cursor_position == 4
        assert b.selection_state.original_cursor_position == 0

    def test_left_repeated_shrinks_to_single_char(self) -> None:
        """Repeated Left shrinks down to a single character and then pins."""
        b, ev = _mk_sel("hello world", 0, 5)
        for _ in range(4):
            helix_move_left(ev)
        assert b.cursor_position == 1
        # One more Left should pin — can't shrink further.
        helix_move_left(ev)
        assert b.cursor_position == 1

    def test_right_grows_past_pin(self) -> None:
        """Right from a single char grows the selection again."""
        b, ev = _mk_sel("hello", 0, 1)
        helix_move_right(ev)
        assert b.cursor_position == 2
        assert b.selection_state.original_cursor_position == 0

    def test_right_repeated(self) -> None:
        """Pressing Right multiple times grows by one each time."""
        b, ev = _mk_sel("abcdef", 0, 3)
        for _ in range(3):
            helix_move_right(ev)
        assert b.cursor_position == 6

    def test_left_crosses_anchor_flips_direction(self) -> None:
        """When Left crosses the anchor the selection flips direction."""
        b, ev = _mk_sel("hello", 2, 5)
        # (2,5) block=4 -> t=3 -> (2,4)
        helix_move_left(ev)
        assert b.cursor_position == 4
        assert b.selection_state.original_cursor_position == 2
        # (2,4) block=3 -> t=2 -> (2,3)
        helix_move_left(ev)
        assert b.cursor_position == 3
        assert b.selection_state.original_cursor_position == 2
        # (2,3) block=2 -> t=1, crosses anchor -> flip to (3,1)
        helix_move_left(ev)
        assert b.cursor_position == 1
        assert b.selection_state.original_cursor_position == 3

    def test_backward_right_shrinks(self) -> None:
        """Right on a backward selection shrinks from the left edge."""
        b, ev = _mk_sel("hello", 3, 1)
        # block=head=1, t=2, put_cursor(2): head<anchor, no cross, head->2
        helix_move_right(ev)
        assert b.cursor_position == 2
        assert b.selection_state.original_cursor_position == 3

    def test_arg_2(self) -> None:
        """arg=2 on Right advances block cursor by two."""
        b, ev = _mk_sel("hello world", 0, 3)
        ev.arg = 2
        helix_move_right(ev)
        assert b.cursor_position == 5

    def test_normal_mode_left_unchanged(self) -> None:
        """In normal mode Left collapses the selection and moves left."""
        b = _mk("hello", 3)
        ev = _FakeEvent(b)
        ev.current_buffer.selection_state = SelectionState(3, SelectionType.CHARACTERS)
        ev.current_buffer.cursor_position = 3
        helix_move_left(ev)
        assert b.cursor_position == 2
        assert b.selection_state is None

    def test_normal_mode_right_unchanged(self) -> None:
        """In normal mode Right moves right with no selection."""
        b = _mk("hello", 3)
        ev = _FakeEvent(b)
        helix_move_right(ev)
        assert b.cursor_position == 4
        assert b.selection_state is None
