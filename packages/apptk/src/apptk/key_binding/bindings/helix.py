"""Define editor key-bindings and commands for the Helix editing mode.

Helix is a modal editor with a "select-then-act" paradigm. Unlike Vi's
"verb-then-object" approach, Helix selections are made first, then
operations are applied to them.

Key differences from Vi:
- Movement keys select text by default (in select mode)
- `w`, `b`, `e` select words rather than just moving
- `x` selects the current line
- `d` deletes selection, `c` changes selection
- `g` enters goto mode, `m` enters match mode
- `z` enters view mode for scrolling without moving cursor
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.buffer import indent, unindent
from apptk.clipboard import ClipboardData
from apptk.commands import add_cmd, get_cmd
from apptk.enums import EditingMode
from apptk.filters import (
    Condition,
    buffer_has_focus,
    has_arg,
    has_selection,
    is_read_only,
)
from apptk.filters.app import (
    in_paste_mode,
    is_multiline,
    is_searching,
)
from apptk.filters.buffer import cursor_in_leading_ws, is_returnable
from apptk.key_binding import ConditionalKeyBindings, KeyBindings
from apptk.key_binding.helix_state import CharacterFind, InputMode
from apptk.selection import SelectionState, SelectionType

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindingsBase
    from apptk.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.buffer import Buffer

__all__ = [
    "load_helix_bindings",
    "load_helix_search_bindings",
]

log = logging.getLogger(__name__)


# Helix mode conditions


@Condition
def helix_mode() -> bool:
    """Check if Helix editing mode is active."""
    app = get_app()
    return app.editing_mode == EditingMode.HELIX


@Condition
def helix_normal_mode() -> bool:
    """Check if in Helix normal mode (navigation, not in explicit select mode)."""
    if not helix_mode():
        return False
    app = get_app()
    return (
        app.helix_state.input_mode == InputMode.NAVIGATION
        and not app.helix_state.select_mode
    )


@Condition
def helix_insert_mode() -> bool:
    """Check if in Helix insert mode."""
    if not helix_mode():
        return False
    app = get_app()
    return app.helix_state.input_mode == InputMode.INSERT


@Condition
def helix_select_mode() -> bool:
    """Check if in Helix select/extend mode (entered via ``v``)."""
    if not helix_mode():
        return False
    app = get_app()
    return (
        app.helix_state.input_mode == InputMode.NAVIGATION
        and app.helix_state.select_mode
    )


@Condition
def helix_replace_mode() -> bool:
    """Check if in Helix replace mode."""
    if not helix_mode():
        return False
    app = get_app()
    return app.helix_state.input_mode == InputMode.REPLACE


@Condition
def helix_goto_mode() -> bool:
    """Check if in Helix goto mode."""
    if not helix_mode():
        return False
    return get_app().helix_state.goto_mode


@Condition
def helix_match_mode() -> bool:
    """Check if in Helix match mode."""
    if not helix_mode():
        return False
    return get_app().helix_state.match_mode


@Condition
def helix_view_mode() -> bool:
    """Check if in Helix view mode."""
    if not helix_mode():
        return False
    return get_app().helix_state.view_mode


@Condition
def helix_window_mode() -> bool:
    """Check if in Helix window mode."""
    if not helix_mode():
        return False
    return get_app().helix_state.window_mode


# Helper functions


def _exit_helix_submodes() -> None:
    """Exit all Helix sub-modes (goto, match, view, window)."""
    get_app().helix_state.exit_submode()


def _set_insert_state(buff: Buffer, insert_point: int, exit_pos: int) -> None:
    """Remember the insertion point and the position to return to on ESC.

    ``insert_point`` is where typed text is inserted; ``exit_pos`` is where the
    cursor should land when leaving insert mode without having typed anything.
    Without this, exiting insert mode always steps one character left, which
    makes repeated enter/exit cycles drift across the buffer.
    """
    buff.helix_insert_point = insert_point
    buff.helix_exit_pos = exit_pos


def _enter_helix_normal_mode() -> None:
    """Enter Helix normal mode."""
    app = get_app()
    buffer = app.current_buffer
    helix_state = app.helix_state

    if helix_state.input_mode in (InputMode.INSERT, InputMode.REPLACE):
        insert_point = getattr(buffer, "helix_insert_point", None)
        exit_pos = getattr(buffer, "helix_exit_pos", None)
        if insert_point is not None and exit_pos is not None:
            if buffer.cursor_position <= insert_point:
                # Nothing was typed (or the cursor moved back): return to the
                # remembered position so that repeated enter/exit cycles do not
                # drift the cursor backwards.
                buffer.cursor_position = exit_pos
            # If text was typed, the cursor already sits one cell past the last
            # typed character (matching Helix), so leave it where it is.
        else:
            buffer.cursor_position += buffer.document.get_cursor_left_position()
        buffer.helix_insert_point = None
        buffer.helix_exit_pos = None

    helix_state.input_mode = InputMode.NAVIGATION
    helix_state.select_mode = False
    _exit_helix_submodes()


# Normal mode commands


@add_cmd(
    keys=["escape"],
    filter=helix_mode & buffer_has_focus & ~(helix_normal_mode | helix_select_mode),
    hidden=True,
    name="helix-normal-mode",
)
def helix_escape(event: KeyPressEvent) -> None:
    """Return from insert/replace mode to normal mode.

    Not active in navigation mode (with or without a selection), so that an
    application-level escape binding (such as exiting cell edit mode) takes
    precedence there.
    """
    _enter_helix_normal_mode()


@add_cmd(
    keys=["i"],
    filter=(helix_normal_mode | helix_select_mode) & ~is_read_only,
    hidden=True,
    name="helix-insert-mode",
)
def helix_insert_mode_cmd(event: KeyPressEvent) -> None:
    """Enter insert mode before selection."""
    buff = event.current_buffer
    _set_insert_state(buff, buff.cursor_position, buff.cursor_position)
    if buff.selection_state:
        buff.exit_selection()
    event.app.helix_state.input_mode = InputMode.INSERT
    _exit_helix_submodes()


@add_cmd(
    keys=["a"],
    filter=(helix_normal_mode | helix_select_mode) & ~is_read_only,
    hidden=True,
    name="helix-append-mode",
)
def helix_append_mode(event: KeyPressEvent) -> None:
    """Enter insert mode after selection.

    The selection is kept (mirroring Helix ``append_mode``) and the cursor is
    placed at the exclusive end of the selection, so typed text is inserted
    immediately after the selected text.  Without a selection the cursor moves
    one grapheme forward (append after the current character).
    """
    buff = event.current_buffer
    if buff.selection_state:
        from_, to = buff.document.selection_range()
        _set_insert_state(buff, insert_point=to, exit_pos=buff.cursor_position)
        buff.selection_state.original_cursor_position = from_
        buff.cursor_position = to
    else:
        _set_insert_state(
            buff,
            insert_point=buff.cursor_position
            + buff.document.get_cursor_right_position(),
            exit_pos=buff.cursor_position,
        )
        buff.cursor_position += buff.document.get_cursor_right_position()
    event.app.helix_state.input_mode = InputMode.INSERT
    _exit_helix_submodes()


@add_cmd(
    keys=["I"],
    filter=helix_normal_mode & ~is_read_only,
    hidden=True,
    name="helix-insert-line-start",
)
def helix_insert_line_start(event: KeyPressEvent) -> None:
    """Insert at start of line."""
    buff = event.current_buffer
    exit_pos = buff.cursor_position
    if buff.selection_state:
        buff.exit_selection()
    buff.cursor_position += buff.document.get_start_of_line_position(
        after_whitespace=True
    )
    _set_insert_state(buff, buff.cursor_position, exit_pos)
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["A"],
    filter=helix_normal_mode & ~is_read_only,
    hidden=True,
    name="helix-insert-line-end",
)
def helix_insert_line_end(event: KeyPressEvent) -> None:
    """Insert at end of line."""
    buff = event.current_buffer
    if buff.selection_state:
        buff.exit_selection()
    buff.cursor_position += buff.document.get_end_of_line_position()
    _set_insert_state(buff, buff.cursor_position, _helix_line_end_position(buff))
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["o"],
    filter=helix_normal_mode & ~is_read_only,
    hidden=True,
    name="helix-open-below",
)
def helix_open_below(event: KeyPressEvent) -> None:
    """Open new line below and enter insert mode."""
    buff = event.current_buffer
    buff.insert_line_below(copy_margin=not in_paste_mode())
    _set_insert_state(buff, buff.cursor_position, buff.cursor_position)
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["O"],
    filter=helix_normal_mode & ~is_read_only,
    hidden=True,
    name="helix-open-above",
)
def helix_open_above(event: KeyPressEvent) -> None:
    """Open new line above and enter insert mode."""
    buff = event.current_buffer
    buff.insert_line_above(copy_margin=not in_paste_mode())
    _set_insert_state(buff, buff.cursor_position, buff.cursor_position)
    event.app.helix_state.input_mode = InputMode.INSERT


# Helper to ensure selection state is correct for the current mode


def _helix_put_cursor(buff: Buffer, target: int, *, extend: bool = True) -> None:
    """Apply Helix ``put_cursor`` 1-width semantics.

    When *extend* is ``True``, the head is moved to *target* and the anchor
    is adjusted following Helix's 1-width rule so the character originally
    under the cursor stays inside the selection.  If no selection exists yet,
    one is started at the current cursor position first.

    When *extend* is ``False``, any selection is collapsed and the cursor is
    moved to *target*.

    Parameters
    ----------
    buff:
        The buffer whose cursor and selection state will be mutated.
    target:
        The character index the user intends to reach.
    extend:
        Whether this movement should extend an existing selection.
    """
    if not extend:
        # Pure move: collapse to a point cursor (Helix ``Range::point``).
        if buff.selection_state is not None:
            buff.exit_selection()
        buff.cursor_position = target
        return

    if buff.selection_state is None:
        # Starting a fresh selection: anchor at the current cursor position.
        buff.start_selection(selection_type=SelectionType.CHARACTERS)

    # Apply put_cursor 1-width logic.
    anchor = buff.selection_state.original_cursor_position
    head = buff.cursor_position

    # Adjust anchor so the original cursor char stays selected when the head
    # crosses to the other side of the anchor.
    if head >= anchor and target < anchor:
        new_anchor = anchor + 1  # next_grapheme_boundary(anchor)
    elif head < anchor and target >= anchor:
        new_anchor = anchor - 1  # prev_grapheme_boundary(anchor)
    else:
        new_anchor = anchor

    # Forward ranges place the head just past the target char.
    if new_anchor <= target:
        new_head = min(len(buff.text), target + 1)  # next_grapheme_boundary(target)
    else:
        new_head = target

    buff.selection_state.original_cursor_position = new_anchor
    buff.cursor_position = new_head


def _helix_block_cursor_position(buff: Buffer) -> int:
    """Return the position of the block cursor (Helix ``Range::cursor``).

    For a forward selection the block cursor sits on the character before
    the head (the rightmost selected character); for no selection or a
    backward selection it sits at ``cursor_position`` itself.
    """
    sel = buff.selection_state
    if sel is None:
        return buff.cursor_position
    if buff.cursor_position > sel.original_cursor_position:
        return buff.cursor_position - 1
    return buff.cursor_position


def _helix_line_end_position(buff: Buffer) -> int:
    """Return the absolute index of the last character of the current line.

    Helix places the block cursor on the last character of a line (matching
    ``goto_line_end``), rather than one-past-the-end which is only used for
    insertion.  Empty lines keep the cursor on the line's newline character.
    """
    line_start = buff.cursor_position + buff.document.get_start_of_line_position()
    line_end = buff.cursor_position + buff.document.get_end_of_line_position()
    if line_end > line_start:
        return line_end - 1
    return line_start


def _helix_line_selection_end(buff: Buffer, row: int) -> int:
    """Index one past the last visible character of ``row``.

    For a non-empty line this is the position of the trailing newline (one
    before the start of the next line).  For an empty line that contains
    only a newline, or for the last line of the document, it is the start
    of the following line or the end of the document respectively, so that
    ``[start, this)`` includes the line's newline character when present.
    """
    doc = buff.document
    if row + 1 < doc.line_count:
        # For non-empty lines head sits on the newline itself; for an empty
        # line (just ``\\n``) the head must be past it so the range covers it.
        if doc.lines[row]:
            return doc.translate_row_col_to_index(row + 1, 0) - 1
        return doc.translate_row_col_to_index(row + 1, 0)
    return len(buff.text)


def _helix_delete_selection(buff: Buffer) -> ClipboardData:
    """Delete the current selection and return the deleted text.

    Unlike :meth:`Buffer.cut_selection`, a line selection deletes the raw
    ``[anchor, head)`` range, so the trailing newline of the last selected
    line is removed too (Helix ``d`` on a ``x`` line selection deletes the
    whole line).  The clipboard text still has the trailing newline stripped
    for line selections, matching the paste handlers.
    """
    sel = buff.selection_state
    if sel is None:
        return ClipboardData("")
    if sel.type == SelectionType.LINES:
        from_ = min(sel.original_cursor_position, buff.cursor_position)
        to = max(sel.original_cursor_position, buff.cursor_position)
        if from_ == to:
            return ClipboardData("")
        # Include the trailing newline when present (Helix line selections
        # delete the full line including its ending).
        if to < len(buff.text) and buff.text[to] == "\n":
            to += 1
        text = buff.text[from_:to]
        buff.transform_region(from_, to, lambda _ignored: "")
        buff.cursor_position = from_
        cut = text[:-1] if text.endswith("\n") else text
        return ClipboardData(cut, SelectionType.LINES)
    return buff.cut_selection()


def _char_category(ch: str) -> str:
    """Categorize a character following Helix's ``categorize_char``."""
    if ch.isspace():
        return "Whitespace"
    if ch.isalnum() or ch == "_":
        return "Word"
    return "Punctuation"


def _is_word_boundary(a: str, b: str, *, long: bool = False) -> bool:
    """Return whether ``a`` and ``b`` form a word boundary."""
    cat_a = _char_category(a)
    cat_b = _char_category(b)
    if long and {cat_a, cat_b} == {"Word", "Punctuation"}:
        return False
    return cat_a != cat_b


def _helix_prev_word_anchor(buff: Buffer, *, long: bool = False) -> None:
    """Set the selection anchor for a Helix ``b``/``B`` motion.

    The anchor is placed on the character under the cursor so it stays in the
    selection, unless the cursor already sits at a word start (in which case
    the first character of the word is not included).
    """
    sel = buff.selection_state
    if sel is None:
        return
    cur = buff.cursor_position
    if cur == 0 or cur >= len(buff.text):
        return
    anchor = cur + 1
    ch = buff.text[cur]
    prev_ch = buff.text[cur - 1]
    # Raise the anchor above the character under the cursor when it is not a
    # word start (Helix only keeps the anchor at the cursor for boundaries).
    if not ch.isspace() and _is_word_boundary(prev_ch, ch, long=long):
        anchor = cur
    sel.original_cursor_position = min(anchor, len(buff.text))


# Movement commands


@add_cmd(
    keys=["h", "left"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-move-left",
)
def helix_move_left(event: KeyPressEvent) -> None:
    """Move left, or move the block cursor left when extending."""
    buff = event.current_buffer
    target = max(0, _helix_block_cursor_position(buff) - event.arg)
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["l", "right"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-move-right",
)
def helix_move_right(event: KeyPressEvent) -> None:
    """Move right, or move the block cursor right when extending."""
    buff = event.current_buffer
    target = min(len(buff.text), _helix_block_cursor_position(buff) + event.arg)
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["j", "down"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-move-down",
)
def helix_move_down(event: KeyPressEvent) -> None:
    """Move down."""
    buff = event.current_buffer
    for _ in range(event.arg):
        target = buff.cursor_position + buff.document.get_cursor_down_position()
        _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["k", "up"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-move-up",
)
def helix_move_up(event: KeyPressEvent) -> None:
    """Move up."""
    buff = event.current_buffer
    for _ in range(event.arg):
        target = buff.cursor_position + buff.document.get_cursor_up_position()
        _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["w"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-next-word-start",
)
def helix_select_next_word_start(event: KeyPressEvent) -> None:
    """Select to next word start."""
    buff = event.current_buffer
    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()
    if buff.selection_state is None:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)
    pos = buff.document.find_next_word_beginning(count=event.arg)
    if pos:
        buff.cursor_position += pos
    elif buff.cursor_position < len(buff.text):
        buff.cursor_position = len(buff.text)


@add_cmd(
    keys=["W"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-next-long-word-start",
)
def helix_select_next_long_word_start(event: KeyPressEvent) -> None:
    """Select to next WORD start."""
    buff = event.current_buffer
    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()
    if buff.selection_state is None:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)
    pos = buff.document.find_next_word_beginning(count=event.arg, WORD=True)
    if pos:
        buff.cursor_position += pos
    elif buff.cursor_position < len(buff.text):
        buff.cursor_position = len(buff.text)


@add_cmd(
    keys=["b"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-prev-word-start",
)
def helix_select_prev_word_start(event: KeyPressEvent) -> None:
    """Select to previous word start."""
    buff = event.current_buffer
    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()
    if buff.selection_state is None:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)
    pos = buff.document.find_start_of_previous_word(count=event.arg)
    if pos:
        _helix_prev_word_anchor(buff)
        buff.cursor_position += pos
    elif buff.cursor_position > 0:
        _helix_prev_word_anchor(buff)
        buff.cursor_position += buff.document.get_start_of_line_position()


@add_cmd(
    keys=["B"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-prev-long-word-start",
)
def helix_select_prev_long_word_start(event: KeyPressEvent) -> None:
    """Select to previous WORD start."""
    buff = event.current_buffer
    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()
    if buff.selection_state is None:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)
    pos = buff.document.find_start_of_previous_word(count=event.arg, WORD=True)
    if pos:
        _helix_prev_word_anchor(buff, long=True)
        buff.cursor_position += pos


@add_cmd(
    keys=["e"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-next-word-end",
)
def helix_select_next_word_end(event: KeyPressEvent) -> None:
    """Select to next word end."""
    buff = event.current_buffer
    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()
    pos = buff.document.find_next_word_ending(count=event.arg)
    if pos:
        _helix_put_cursor(buff, buff.cursor_position + pos - 1, extend=True)


@add_cmd(
    keys=["E"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-next-long-word-end",
)
def helix_select_next_long_word_end(event: KeyPressEvent) -> None:
    """Select to next WORD end."""
    buff = event.current_buffer
    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()
    pos = buff.document.find_next_word_ending(count=event.arg, WORD=True)
    if pos:
        _helix_put_cursor(buff, buff.cursor_position + pos - 1, extend=True)


# Line selection (Helix's x command)


@add_cmd(
    keys=["x"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-extend-line-below",
)
def helix_extend_line_below(event: KeyPressEvent) -> None:
    """Select current line, extend to next line if already selected."""
    buff = event.current_buffer
    doc = buff.document

    if buff.selection_state is None or (
        buff.selection_state.type != SelectionType.LINES
    ):
        # Start a fresh line selection at beginning of current line.
        # The head is placed one past the trailing newline so that the block
        # cursor renders beyond the last character (matching Helix ``x``).
        row = doc.cursor_position_row
        start = buff.cursor_position + doc.get_start_of_line_position()
        buff.selection_state = SelectionState(start, SelectionType.LINES)
        buff.cursor_position = _helix_line_selection_end(buff, row)
    else:
        # Already have a line selection: extend down by the requested number
        # of lines.  The cursor sits at the start of the line following the
        # selected region.
        head_row = doc.translate_index_to_position(buff.cursor_position)[0]
        head_row += event.arg
        if head_row >= doc.line_count:
            buff.cursor_position = len(buff.text)
        else:
            buff.cursor_position = _helix_line_selection_end(buff, head_row)


@add_cmd(
    keys=["X"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-extend-to-line-bounds",
)
def helix_extend_to_line_bounds(event: KeyPressEvent) -> None:
    """Extend selection to line bounds."""
    buff = event.current_buffer
    if buff.selection_state:
        sel = buff.selection_state
        doc = buff.document
        lo, hi = sorted((sel.original_cursor_position, buff.cursor_position))
        lo_row = doc.translate_index_to_position(lo)[0]
        hi_row, hi_col = doc.translate_index_to_position(hi)
        if hi_col == 0 and hi > 0 and hi == doc.translate_row_col_to_index(hi_row, 0):
            hi_row -= 1  # end sits at a line start → preceding line is last selected
        sel.original_cursor_position = doc.translate_row_col_to_index(lo_row, 0)
        buff.cursor_position = _helix_line_selection_end(buff, hi_row)
        sel.type = SelectionType.LINES
        event.app.helix_state.select_mode = True


# Find character commands


@add_cmd(
    keys=["f"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-find-char",
)
def helix_find_char(event: KeyPressEvent) -> None:
    """Find next occurrence of character."""
    # This needs to wait for the next character input
    event.app.helix_state.waiting_for_char = "f"


@add_cmd(
    keys=["F"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-find-char-backward",
)
def helix_find_char_backward(event: KeyPressEvent) -> None:
    """Find previous occurrence of character."""
    event.app.helix_state.waiting_for_char = "F"


@add_cmd(
    keys=["t"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-find-till-char",
)
def helix_find_till_char(event: KeyPressEvent) -> None:
    """Find till next occurrence of character."""
    event.app.helix_state.waiting_for_char = "t"


@add_cmd(
    keys=["T"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-find-till-char-backward",
)
def helix_find_till_char_backward(event: KeyPressEvent) -> None:
    """Find till previous occurrence of character."""
    event.app.helix_state.waiting_for_char = "T"


@Condition
def waiting_for_char() -> bool:
    """Check if waiting for a character input for f/F/t/T."""
    if not helix_mode():
        return False
    return get_app().helix_state.waiting_for_char is not None


@add_cmd(
    keys=["<any>"],
    filter=(helix_normal_mode | helix_select_mode) & waiting_for_char,
    hidden=True,
    eager=True,
    name="helix-handle-find-char",
)
def helix_handle_find_char(event: KeyPressEvent) -> None:
    """Handle character input for f/F/t/T commands."""
    app = event.app
    buff = event.current_buffer
    char = event.data
    mode = app.helix_state.waiting_for_char
    app.helix_state.waiting_for_char = None

    if not app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()

    if mode == "f":
        app.helix_state.last_character_find = CharacterFind(char, False)
        match = buff.document.find(char, in_current_line=False, count=event.arg)
        if match:
            _helix_put_cursor(buff, buff.cursor_position + match, extend=True)
    elif mode == "F":
        app.helix_state.last_character_find = CharacterFind(char, True)
        pos = buff.document.find_backwards(char, in_current_line=False, count=event.arg)
        if pos:
            _helix_put_cursor(buff, buff.cursor_position + pos, extend=True)
    elif mode == "t":
        app.helix_state.last_character_find = CharacterFind(char, False)
        match = buff.document.find(char, in_current_line=False, count=event.arg)
        if match:
            _helix_put_cursor(buff, buff.cursor_position + match - 1, extend=True)
    elif mode == "T":
        app.helix_state.last_character_find = CharacterFind(char, True)
        pos = buff.document.find_backwards(char, in_current_line=False, count=event.arg)
        if pos:
            _helix_put_cursor(buff, buff.cursor_position + pos + 1, extend=True)


# Selection mode (v)


@add_cmd(
    keys=["v"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-select-mode",
)
def helix_select_mode_cmd(event: KeyPressEvent) -> None:
    """Enter select/extend mode."""
    buff = event.current_buffer
    event.app.helix_state.select_mode = True
    if buff.selection_state is None:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)
        # Match Helix `select_mode`: ensure end-of-document selections are
        # also 1-width, covering the final character.
        if buff.cursor_position == len(buff.text) and buff.cursor_position > 0:
            buff.selection_state.original_cursor_position = buff.cursor_position - 1


@add_cmd(
    keys=["v"],
    filter=helix_select_mode,
    hidden=True,
    name="helix-exit-select-mode",
)
def helix_exit_select_mode(event: KeyPressEvent) -> None:
    """Exit select mode, keeping the current selection."""
    event.app.helix_state.select_mode = False


# Changes


@add_cmd(
    keys=["d"],
    filter=(helix_normal_mode | helix_select_mode) & has_selection,
    hidden=True,
    name="helix-delete-selection",
)
def helix_delete_selection(event: KeyPressEvent) -> None:
    """Delete selection."""
    data = _helix_delete_selection(event.current_buffer)
    event.app.clipboard.set_data(data)


@add_cmd(
    keys=["d"],
    filter=helix_normal_mode & ~has_selection,
    hidden=True,
    name="helix-delete-char",
)
def helix_delete_char(event: KeyPressEvent) -> None:
    """Delete character under cursor."""
    buff = event.current_buffer
    text = buff.delete(count=event.arg)
    event.app.clipboard.set_text(text)


@add_cmd(
    keys=["c"],
    filter=(helix_normal_mode | helix_select_mode) & has_selection & ~is_read_only,
    hidden=True,
    name="helix-change-selection",
)
def helix_change_selection(event: KeyPressEvent) -> None:
    """Change selection (delete and enter insert mode)."""
    buff = event.current_buffer
    data = _helix_delete_selection(buff)
    event.app.clipboard.set_data(data)
    _set_insert_state(buff, buff.cursor_position, max(0, buff.cursor_position - 1))
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["c"],
    filter=helix_normal_mode & ~has_selection & ~is_read_only,
    hidden=True,
    name="helix-change-char",
)
def helix_change_char(event: KeyPressEvent) -> None:
    """Change character under cursor."""
    buff = event.current_buffer
    text = buff.delete(count=event.arg)
    event.app.clipboard.set_text(text)
    _set_insert_state(buff, buff.cursor_position, max(0, buff.cursor_position - 1))
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["A-d"],
    filter=(helix_normal_mode | helix_select_mode) & has_selection,
    hidden=True,
    name="helix-delete-selection-noyank",
)
def helix_delete_selection_noyank(event: KeyPressEvent) -> None:
    """Delete selection without yanking."""
    _helix_delete_selection(event.current_buffer)


@add_cmd(
    keys=["A-d"],
    filter=helix_normal_mode & ~has_selection,
    hidden=True,
    name="helix-delete-char-noyank",
)
def helix_delete_char_noyank(event: KeyPressEvent) -> None:
    """Delete character under cursor without yanking."""
    event.current_buffer.delete(count=event.arg)


@add_cmd(
    keys=["A-c"],
    filter=(helix_normal_mode | helix_select_mode) & has_selection & ~is_read_only,
    hidden=True,
    name="helix-change-selection-noyank",
)
def helix_change_selection_noyank(event: KeyPressEvent) -> None:
    """Change selection without yanking."""
    buff = event.current_buffer
    _helix_delete_selection(buff)
    _set_insert_state(buff, buff.cursor_position, max(0, buff.cursor_position - 1))
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["A-c"],
    filter=helix_normal_mode & ~has_selection & ~is_read_only,
    hidden=True,
    name="helix-change-char-noyank",
)
def helix_change_char_noyank(event: KeyPressEvent) -> None:
    """Change character under cursor without yanking."""
    buff = event.current_buffer
    buff.delete(count=event.arg)
    _set_insert_state(buff, buff.cursor_position, max(0, buff.cursor_position - 1))
    event.app.helix_state.input_mode = InputMode.INSERT


@add_cmd(
    keys=["r"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-replace-char",
)
def helix_replace_char(event: KeyPressEvent) -> None:
    """Replace selection(s) with a single character."""
    event.app.helix_state.input_mode = InputMode.REPLACE_SINGLE


@add_cmd(
    keys=["R"],
    filter=(helix_normal_mode | helix_select_mode) & has_selection & ~is_read_only,
    hidden=True,
    name="helix-replace-with-yanked",
)
def helix_replace_with_yanked(event: KeyPressEvent) -> None:
    """Replace selection with yanked text.

    Matching Helix ``replace_with_yanked``, the selection is kept covering
    the replaced text and the buffer returns to normal mode.
    """
    buff = event.current_buffer
    data = event.app.clipboard.get_data()
    replacement = data.text
    if replacement.endswith("\n"):
        replacement = replacement[:-1]
    sel = buff.selection_state
    if sel is None:
        return
    ranges = list(buff.document.selection_ranges())
    for start, end in reversed(ranges):
        buff.transform_region(start, end, lambda _ignored, r=replacement: r)
    # Restore a selection covering the replaced text.  (`transform_region`
    # clears the selection state via the text-change notification.)
    start = ranges[0][0]
    new_end = start + len(replacement)
    buff.cursor_position = new_end
    buff.selection_state = SelectionState(start, sel.type)
    event.app.helix_state.select_mode = False


@add_cmd(
    keys=["~"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-switch-case",
)
def helix_switch_case(event: KeyPressEvent) -> None:
    """Switch case of selection or character."""
    buff = event.current_buffer
    selection_state = buff.selection_state
    if selection_state:
        for start, end in buff.document.selection_ranges():
            buff.transform_region(start, end, lambda s: s.swapcase())
        buff.selection_state = selection_state
    else:
        c = buff.document.current_char
        if c and c != "\n":
            buff.insert_text(c.swapcase(), overwrite=True)


@add_cmd(
    keys=["`"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-to-lowercase",
)
def helix_to_lowercase(event: KeyPressEvent) -> None:
    """Convert selection to lowercase."""
    buff = event.current_buffer
    if buff.selection_state:
        for start, end in buff.document.selection_ranges():
            buff.transform_region(start, end, lambda s: s.lower())
        buff.exit_selection()


@add_cmd(
    keys=["A-`"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-to-uppercase",
)
def helix_to_uppercase(event: KeyPressEvent) -> None:
    """Convert selection to uppercase."""
    buff = event.current_buffer
    if buff.selection_state:
        for start, end in buff.document.selection_ranges():
            buff.transform_region(start, end, lambda s: s.upper())
        buff.exit_selection()


# Yank and paste


@add_cmd(
    keys=["y"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-yank",
)
def helix_yank(event: KeyPressEvent) -> None:
    """Yank the selection (Helix ``yank``).

    In select mode the current selection is yanked.  In normal mode the
    cursor sits on a 1-width selection, so the character under the cursor
    is yanked, following Helix's select-then-act model.
    """
    buff = event.current_buffer
    if buff.selection_state is not None:
        # Save selection state since copy_selection clears it
        selection_state = buff.selection_state
        data = buff.copy_selection()
        event.app.clipboard.set_data(data)
        # Restore selection state to maintain the selection
        buff.selection_state = selection_state
    elif buff.cursor_position < len(buff.text):
        # Normal mode: yank the character under the cursor.
        text = buff.text[buff.cursor_position]
        event.app.clipboard.set_data(ClipboardData(text))


@add_cmd(
    keys=["p"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-paste-after",
)
def helix_paste_after(event: KeyPressEvent) -> None:
    """Paste after selection."""
    buff = event.current_buffer
    data = event.app.clipboard.get_data()
    pasted_text = data.text * event.arg
    if data.type == SelectionType.LINES:
        # Line paste: insert on new line below current line
        end_of_line = buff.cursor_position + buff.document.get_end_of_line_position()
        buff.cursor_position = end_of_line
        insert_text = "\n" + pasted_text
        paste_start = buff.cursor_position + 1
        buff.insert_text(insert_text)
        # Cursor is now at end of pasted text; select from start of paste
        buff.selection_state = SelectionState(paste_start, SelectionType.LINES)
    else:
        # Character paste: insert after cursor
        paste_start = buff.cursor_position + 1
        buff.cursor_position += buff.document.get_cursor_right_position()
        buff.insert_text(pasted_text)
        # Cursor is now at end of pasted text; select from start of paste
        buff.selection_state = SelectionState(paste_start, SelectionType.CHARACTERS)


@add_cmd(
    keys=["P"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-paste-before",
)
def helix_paste_before(event: KeyPressEvent) -> None:
    """Paste before selection."""
    buff = event.current_buffer
    data = event.app.clipboard.get_data()
    pasted_text = data.text * event.arg
    if data.type == SelectionType.LINES:
        # Line paste: insert on new line above current line
        start_of_line = (
            buff.cursor_position + buff.document.get_start_of_line_position()
        )
        buff.cursor_position = start_of_line
        paste_start = buff.cursor_position
        buff.insert_text(pasted_text + "\n")
        # Cursor is after the inserted newline; move back to end of pasted text
        buff.cursor_position -= 1
        buff.selection_state = SelectionState(paste_start, SelectionType.LINES)
    else:
        # Character paste: insert before cursor
        paste_start = buff.cursor_position
        buff.insert_text(pasted_text)
        # Cursor is now at end of pasted text; select from start of paste
        buff.selection_state = SelectionState(paste_start, SelectionType.CHARACTERS)


# Undo/redo


@add_cmd(
    keys=["u"],
    filter=helix_normal_mode,
    hidden=True,
    save_before=(lambda e: False),
    name="helix-undo",
)
def helix_undo(event: KeyPressEvent) -> None:
    """Undo."""
    for _ in range(event.arg):
        event.current_buffer.undo()


@add_cmd(
    keys=["U"],
    filter=helix_normal_mode,
    hidden=True,
    save_before=(lambda e: False),
    name="helix-redo",
)
def helix_redo(event: KeyPressEvent) -> None:
    """Redo."""
    for _ in range(event.arg):
        event.current_buffer.redo()


# Indentation


@add_cmd(
    keys=[">"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-indent",
)
def helix_indent(event: KeyPressEvent) -> None:
    """Indent selection."""
    buff = event.current_buffer
    doc = buff.document
    if buff.selection_state:
        start, end = (
            doc.translate_index_to_position(x)[0] for x in doc.selection_range()
        )
    else:
        start = end = doc.cursor_position_row
    indent(buff, start, end + 1, count=event.arg)


@add_cmd(
    keys=["<"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-unindent",
)
def helix_unindent(event: KeyPressEvent) -> None:
    """Unindent selection."""
    buff = event.current_buffer
    doc = buff.document
    if buff.selection_state:
        start, end = (
            doc.translate_index_to_position(x)[0] for x in doc.selection_range()
        )
    else:
        start = end = doc.cursor_position_row
    unindent(buff, start, end + 1, count=event.arg)


# Selection manipulation


@add_cmd(
    keys=[";"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-collapse-selection",
)
def helix_collapse_selection(event: KeyPressEvent) -> None:
    """Collapse selection to cursor."""
    event.app.helix_state.select_mode = False
    event.current_buffer.exit_selection()


@add_cmd(
    keys=["A-;"],
    filter=(helix_normal_mode | helix_select_mode) & has_selection,
    hidden=True,
    name="helix-flip-selection",
)
def helix_flip_selection(event: KeyPressEvent) -> None:
    """Flip selection cursor and anchor."""
    buff = event.current_buffer
    if buff.selection_state:
        anchor = buff.selection_state.original_cursor_position
        cursor = buff.cursor_position
        buff.cursor_position = anchor
        buff.selection_state.original_cursor_position = cursor


@add_cmd(
    keys=["%"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-select-all",
)
def helix_select_all(event: KeyPressEvent) -> None:
    """Select entire file."""
    buff = event.current_buffer
    event.app.helix_state.select_mode = True
    buff.cursor_position = 0
    buff.start_selection()
    buff.cursor_position = len(buff.text)


# Join lines


@add_cmd(
    keys=["J"],
    filter=(helix_normal_mode | helix_select_mode) & ~is_read_only,
    hidden=True,
    name="helix-join-lines",
)
def helix_join_lines(event: KeyPressEvent) -> None:
    """Join lines."""
    buff = event.current_buffer
    if buff.selection_state:
        buff.join_selected_lines()
        buff.exit_selection()
    else:
        for _ in range(event.arg):
            buff.join_next_line()


# Goto mode


@add_cmd(
    keys=["g"],
    filter=helix_normal_mode & ~helix_goto_mode,
    hidden=True,
    name="helix-enter-goto-mode",
)
def helix_enter_goto_mode(event: KeyPressEvent) -> None:
    """Enter goto mode."""
    event.app.helix_state.goto_mode = True


@add_cmd(
    keys=["g"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-file-start",
)
def helix_goto_file_start(event: KeyPressEvent) -> None:
    """Go to start of file or line number."""
    _exit_helix_submodes()
    buff = event.current_buffer
    if event.arg != 1 or has_arg():
        # Go to specific line
        target = buff.document.translate_row_col_to_index(event.arg - 1, 0)
    else:
        target = 0
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["e"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-file-end",
)
def helix_goto_file_end(event: KeyPressEvent) -> None:
    """Go to end of file."""
    _exit_helix_submodes()
    _helix_put_cursor(
        event.current_buffer,
        len(event.current_buffer.text),
        extend=event.app.helix_state.select_mode,
    )


@add_cmd(
    keys=["h"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-line-start",
)
def helix_goto_line_start(event: KeyPressEvent) -> None:
    """Go to start of line."""
    _exit_helix_submodes()
    buff = event.current_buffer
    target = buff.cursor_position + buff.document.get_start_of_line_position()
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["l"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-line-end",
)
def helix_goto_line_end(event: KeyPressEvent) -> None:
    """Go to end of line."""
    _exit_helix_submodes()
    buff = event.current_buffer
    target = _helix_line_end_position(buff)
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["s"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-first-nonwhitespace",
)
def helix_goto_first_nonwhitespace(event: KeyPressEvent) -> None:
    """Go to first non-whitespace character."""
    _exit_helix_submodes()
    buff = event.current_buffer
    target = buff.cursor_position + buff.document.get_start_of_line_position(
        after_whitespace=True
    )
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["t"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-window-top",
)
def helix_goto_window_top(event: KeyPressEvent) -> None:
    """Go to top of window."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                w.render_info.first_visible_line(after_scroll_offset=True), 0
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["c"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-window-center",
)
def helix_goto_window_center(event: KeyPressEvent) -> None:
    """Go to center of window."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                w.render_info.center_visible_line(), 0
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["b"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-goto-window-bottom",
)
def helix_goto_window_bottom(event: KeyPressEvent) -> None:
    """Go to bottom of window."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                w.render_info.last_visible_line(before_scroll_offset=True), 0
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["escape"],
    filter=helix_goto_mode,
    hidden=True,
    name="helix-exit-goto-mode",
)
def helix_exit_goto_mode(event: KeyPressEvent) -> None:
    """Exit goto mode."""
    _exit_helix_submodes()


# Match mode


@add_cmd(
    keys=["m"],
    filter=helix_normal_mode & ~helix_match_mode,
    hidden=True,
    name="helix-enter-match-mode",
)
def helix_enter_match_mode(event: KeyPressEvent) -> None:
    """Enter match mode."""
    event.app.helix_state.match_mode = True


@add_cmd(
    keys=["m"],
    filter=helix_match_mode,
    hidden=True,
    name="helix-goto-matching-bracket",
)
def helix_goto_matching_bracket(event: KeyPressEvent) -> None:
    """Go to matching bracket."""
    _exit_helix_submodes()
    buff = event.current_buffer
    match = buff.document.find_matching_bracket_position()
    if match:
        _helix_put_cursor(
            buff,
            buff.cursor_position + match,
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["escape"],
    filter=helix_match_mode,
    hidden=True,
    name="helix-exit-match-mode",
)
def helix_exit_match_mode(event: KeyPressEvent) -> None:
    """Exit match mode."""
    _exit_helix_submodes()


# View mode


@add_cmd(
    keys=["z"],
    filter=helix_normal_mode & ~helix_view_mode,
    hidden=True,
    name="helix-enter-view-mode",
)
def helix_enter_view_mode(event: KeyPressEvent) -> None:
    """Enter view mode."""
    event.app.helix_state.view_mode = True


@add_cmd(
    keys=["z", "c"],
    filter=helix_view_mode,
    hidden=True,
    name="helix-view-center",
    eager=True,
)
def helix_view_center(event: KeyPressEvent) -> None:
    """Center view on cursor."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        scroll_height = w.render_info.window_height // 2
        y = max(0, buff.document.cursor_position_row - scroll_height)
        w.vertical_scroll = y


@add_cmd(
    keys=["t"],
    filter=helix_view_mode,
    hidden=True,
    name="helix-view-top",
)
def helix_view_top(event: KeyPressEvent) -> None:
    """Align view to top."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w:
        w.vertical_scroll = buff.document.cursor_position_row


@add_cmd(
    keys=["b"],
    filter=helix_view_mode,
    hidden=True,
    name="helix-view-bottom",
)
def helix_view_bottom(event: KeyPressEvent) -> None:
    """Align view to bottom."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        cursor_row = buff.document.cursor_position_row
        w.vertical_scroll = max(0, cursor_row - w.render_info.window_height + 1)


@add_cmd(
    keys=["j", "down"],
    filter=helix_view_mode,
    hidden=True,
    name="helix-scroll-down",
)
def helix_scroll_down(event: KeyPressEvent) -> None:
    """Scroll down."""
    w = event.app.layout.current_window
    if w:
        w.vertical_scroll += event.arg


@add_cmd(
    keys=["k", "up"],
    filter=helix_view_mode,
    hidden=True,
    name="helix-scroll-up",
)
def helix_scroll_up(event: KeyPressEvent) -> None:
    """Scroll up."""
    w = event.app.layout.current_window
    if w:
        w.vertical_scroll = max(0, w.vertical_scroll - event.arg)


@add_cmd(
    keys=["c-f", "pagedown"],
    filter=helix_view_mode | helix_normal_mode,
    hidden=True,
    name="helix-page-down",
)
def helix_page_down(event: KeyPressEvent) -> None:
    """Page down."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                min(
                    buff.document.cursor_position_row + w.render_info.window_height,
                    buff.document.line_count - 1,
                ),
                buff.document.cursor_position_col,
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["c-b", "pageup"],
    filter=helix_view_mode | helix_normal_mode,
    hidden=True,
    name="helix-page-up",
)
def helix_page_up(event: KeyPressEvent) -> None:
    """Page up."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                max(buff.document.cursor_position_row - w.render_info.window_height, 0),
                buff.document.cursor_position_col,
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["c-u"],
    filter=helix_view_mode | helix_normal_mode,
    hidden=True,
    name="helix-half-page-up",
)
def helix_half_page_up(event: KeyPressEvent) -> None:
    """Half page up."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        half = w.render_info.window_height // 2
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                max(buff.document.cursor_position_row - half, 0),
                buff.document.cursor_position_col,
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["c-d"],
    filter=helix_view_mode | helix_normal_mode,
    hidden=True,
    name="helix-half-page-down",
)
def helix_half_page_down(event: KeyPressEvent) -> None:
    """Half page down."""
    _exit_helix_submodes()
    w = event.app.layout.current_window
    buff = event.current_buffer
    if w and w.render_info:
        half = w.render_info.window_height // 2
        _helix_put_cursor(
            buff,
            buff.document.translate_row_col_to_index(
                min(
                    buff.document.cursor_position_row + half,
                    buff.document.line_count - 1,
                ),
                buff.document.cursor_position_col,
            ),
            extend=event.app.helix_state.select_mode,
        )


@add_cmd(
    keys=["escape"],
    filter=helix_view_mode,
    hidden=True,
    name="helix-exit-view-mode",
)
def helix_exit_view_mode(event: KeyPressEvent) -> None:
    """Exit view mode."""
    _exit_helix_submodes()


# Search


@add_cmd(
    keys=["/"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-search-forward",
)
def helix_search_forward(event: KeyPressEvent) -> None:
    """Search forward."""
    from apptk.search import SearchDirection, start_global_search

    start_global_search(direction=SearchDirection.FORWARD)


@add_cmd(
    keys=["?"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-search-backward",
)
def helix_search_backward(event: KeyPressEvent) -> None:
    """Search backward."""
    from apptk.search import SearchDirection, start_global_search

    start_global_search(direction=SearchDirection.BACKWARD)


@add_cmd(
    keys=["n"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-search-next",
)
def helix_search_next(event: KeyPressEvent) -> None:
    """Select next search match."""
    from apptk.search import SearchDirection, find_next_match

    find_next_match(SearchDirection.FORWARD)


@add_cmd(
    keys=["N"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-search-prev",
)
def helix_search_prev(event: KeyPressEvent) -> None:
    """Select previous search match."""
    from apptk.search import SearchDirection, find_next_match

    find_next_match(SearchDirection.BACKWARD)


@add_cmd(
    keys=["enter"],
    filter=helix_mode & is_searching,
    hidden=True,
    name="helix-accept-search",
)
def helix_accept_search(event: KeyPressEvent) -> None:
    """Accept the search input."""
    from apptk.search import accept_global_search

    accept_global_search()


@add_cmd(
    keys=["escape"],
    filter=helix_mode & is_searching,
    hidden=True,
    name="helix-stop-search",
)
def helix_stop_search(event: KeyPressEvent) -> None:
    """Abort the search."""
    from apptk.search import stop_global_search

    stop_global_search()


@add_cmd(
    keys=["*"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-search-selection",
)
def helix_search_selection(event: KeyPressEvent) -> None:
    """Use current selection as search pattern."""
    buff = event.current_buffer
    search_state = event.app.current_search_state
    search_state.text = buff.document.get_word_under_cursor()


# Numeric arguments


def _create_arg_handler(digit: str) -> None:
    """Create a handler for a numeric argument digit."""

    @add_cmd(
        keys=[digit],
        filter=helix_normal_mode | helix_select_mode,
        hidden=True,
        name=f"helix-arg-{digit}",
    )
    def _arg(event: KeyPressEvent) -> None:
        """Handle numeric argument."""
        event.append_to_arg_count(event.data)


for n in "123456789":
    _create_arg_handler(n)


@add_cmd(
    keys=["0"],
    filter=(helix_normal_mode | helix_select_mode) & has_arg,
    hidden=True,
    name="helix-arg-0",
)
def helix_arg_0(event: KeyPressEvent) -> None:
    """Handle zero in numeric argument."""
    event.append_to_arg_count(event.data)


@add_cmd(
    keys=["home"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-home",
)
def helix_home(event: KeyPressEvent) -> None:
    """Move to start of line."""
    buff = event.current_buffer
    target = buff.cursor_position + buff.document.get_start_of_line_position()
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["end"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-end",
)
def helix_end(event: KeyPressEvent) -> None:
    """Move to end of line."""
    buff = event.current_buffer
    target = _helix_line_end_position(buff)
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["G"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-goto-line",
)
def helix_goto_line(event: KeyPressEvent) -> None:
    """Go to line number (defaults to the first line, matching Helix ``G``)."""
    buff = event.current_buffer
    target = buff.document.translate_row_col_to_index(event.arg - 1, 0)
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


@add_cmd(
    keys=["|"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-goto-column",
)
def helix_goto_column(event: KeyPressEvent) -> None:
    """Go to column number."""
    buff = event.current_buffer
    col = (event.arg or 1) - 1
    target = buff.cursor_position + buff.document.get_column_cursor_position(col)
    _helix_put_cursor(buff, target, extend=event.app.helix_state.select_mode)


# Unimpaired-style bindings


@add_cmd(
    keys=[("]", "space")],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-add-newline-below",
)
def helix_add_newline_below(event: KeyPressEvent) -> None:
    """Add newline below current line."""
    buff = event.current_buffer
    doc = buff.document
    cursor_pos = buff.cursor_position
    end_of_line = cursor_pos + doc.get_end_of_line_position()
    buff.cursor_position = end_of_line
    buff.insert_text("\n")
    buff.cursor_position = cursor_pos


@add_cmd(
    keys=[("[", "space")],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-add-newline-above",
)
def helix_add_newline_above(event: KeyPressEvent) -> None:
    """Add newline above current line."""
    buff = event.current_buffer
    doc = buff.document
    cursor_pos = buff.cursor_position
    start_of_line = cursor_pos + doc.get_start_of_line_position()
    buff.cursor_position = start_of_line
    buff.insert_text("\n")
    # Cursor shifts down by 1 due to inserted newline
    buff.cursor_position = cursor_pos + 1


@add_cmd(
    keys=["A-."],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-repeat-last-motion",
)
def helix_repeat_last_motion(event: KeyPressEvent) -> None:
    """Repeat last motion (f/F/t/T)."""
    app = event.app
    buff = event.current_buffer
    find = app.helix_state.last_character_find

    if find is None:
        return

    if not event.app.helix_state.select_mode and buff.selection_state is not None:
        buff.exit_selection()

    if find.backwards:
        pos = buff.document.find_backwards(
            find.character, in_current_line=False, count=event.arg
        )
        if pos:
            _helix_put_cursor(buff, buff.cursor_position + pos, extend=True)
    else:
        pos = buff.document.find(find.character, in_current_line=False, count=event.arg)
        if pos:
            _helix_put_cursor(buff, buff.cursor_position + pos, extend=True)


@add_cmd(
    keys=[","],
    filter=helix_select_mode,
    hidden=True,
    name="helix-keep-primary-selection",
)
def helix_keep_primary_selection(event: KeyPressEvent) -> None:
    """Keep only the primary selection."""
    # In single-cursor mode, this is essentially a no-op
    # Multi-cursor support would need additional implementation


@add_cmd(
    keys=["A-,"],
    filter=helix_select_mode,
    hidden=True,
    name="helix-remove-primary-selection",
)
def helix_remove_primary_selection(event: KeyPressEvent) -> None:
    """Remove the primary selection."""
    # In single-cursor mode, this exits selection
    event.app.helix_state.select_mode = False
    event.current_buffer.exit_selection()


@add_cmd(
    keys=["s"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-select-regex",
)
def helix_select_regex(event: KeyPressEvent) -> None:
    """Select all regex matches inside selections."""
    # This would need integration with a regex prompt
    # For now, just bell to indicate not implemented
    event.app.output.bell()


@add_cmd(
    keys=["S"],
    filter=helix_select_mode,
    hidden=True,
    name="helix-split-selection",
)
def helix_split_selection(event: KeyPressEvent) -> None:
    """Split selection into sub selections on regex matches."""
    # This would need integration with a regex prompt
    # For now, just bell to indicate not implemented
    event.app.output.bell()


@add_cmd(
    keys=["A-s"],
    filter=helix_select_mode,
    hidden=True,
    name="helix-split-selection-newlines",
)
def helix_split_selection_newlines(event: KeyPressEvent) -> None:
    """Split selection on newlines."""
    # Multi-cursor support needed for full implementation
    event.app.output.bell()


@add_cmd(
    keys=["&"],
    filter=helix_select_mode,
    hidden=True,
    name="helix-align-selections",
)
def helix_align_selections(event: KeyPressEvent) -> None:
    """Align selections in columns."""
    # Multi-cursor support needed for full implementation
    event.app.output.bell()


@add_cmd(
    keys=["_"],
    filter=helix_select_mode,
    hidden=True,
    name="helix-trim-selections",
)
def helix_trim_selections(event: KeyPressEvent) -> None:
    """Trim whitespace from selections."""
    # Would need to modify selection boundaries
    event.app.output.bell()


@add_cmd(
    keys=["C"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-copy-selection-below",
)
def helix_copy_selection_below(event: KeyPressEvent) -> None:
    """Copy selection onto next line (add cursor below)."""
    # Multi-cursor support needed for full implementation
    event.app.output.bell()


@add_cmd(
    keys=["A-C"],
    filter=helix_normal_mode | helix_select_mode,
    hidden=True,
    name="helix-copy-selection-above",
)
def helix_copy_selection_above(event: KeyPressEvent) -> None:
    """Copy selection onto previous line (add cursor above)."""
    # Multi-cursor support needed for full implementation
    event.app.output.bell()


get_cmd("helix-toggle-comments").add_keys(
    keys=["c-c"],
    filter=helix_normal_mode | helix_select_mode,
)


@add_cmd(
    keys=["c-i"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-jump-forward",
)
def helix_jump_forward(event: KeyPressEvent) -> None:
    """Jump forward on the jumplist."""
    event.current_buffer.history_forward()


@add_cmd(
    keys=["c-o"],
    filter=helix_normal_mode,
    hidden=True,
    name="helix-jump-backward",
)
def helix_jump_backward(event: KeyPressEvent) -> None:
    """Jump backward on the jumplist."""
    event.current_buffer.history_backward()


@add_cmd(
    keys=["c-s"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-commit-undo",
)
def helix_commit_undo(event: KeyPressEvent) -> None:
    """Commit undo checkpoint."""
    # Create an undo boundary
    buff = event.current_buffer
    buff.save_to_undo_stack()


# Insert mode commands


@add_cmd(
    keys=["<any>"],
    filter=helix_insert_mode & ~is_read_only & buffer_has_focus,
    hidden=True,
    name="helix-self-insert",
)
def helix_self_insert(event: KeyPressEvent) -> None:
    """Insert character."""
    # Only insert printable characters
    data = event.data
    if data and len(data) == 1 and data.isprintable():
        event.current_buffer.insert_text(data, overwrite=False)


@Condition
def helix_replace_single_mode() -> bool:
    """Check if in Helix single-character replace mode."""
    if not helix_mode():
        return False
    app = get_app()
    return app.helix_state.input_mode == InputMode.REPLACE_SINGLE


@add_cmd(
    keys=["<any>"],
    filter=helix_replace_mode & ~is_read_only & buffer_has_focus,
    hidden=True,
    name="helix-replace-insert",
)
def helix_replace_insert(event: KeyPressEvent) -> None:
    """Replace character."""
    data = event.data
    if data and len(data) == 1 and data.isprintable():
        event.current_buffer.insert_text(data, overwrite=True)


@add_cmd(
    keys=["<any>"],
    filter=helix_replace_single_mode & ~is_read_only & buffer_has_focus,
    hidden=True,
    name="helix-replace-single-char",
)
def helix_replace_single_char(event: KeyPressEvent) -> None:
    """Replace selected ranges (or single char) with the typed character.

    Matching Helix ``replace``, an existing selection is kept covering the
    replaced text and the buffer returns to normal mode.
    """
    data = event.data
    if not data or len(data) != 1 or not data.isprintable():
        event.app.helix_state.input_mode = InputMode.NAVIGATION
        return
    buff = event.current_buffer
    sel = buff.selection_state
    if sel is not None:
        # Replace each grapheme in the range with the typed character
        # (Helix ``change_by_and_with_selection``).
        for start, end in buff.document.selection_ranges():
            region_text = buff.text[start:end]
            new_text = data * len(region_text)
            buff.transform_region(start, end, lambda _ignored, new=new_text: new)
        # `transform_region` clears the selection state; restore it.
        buff.selection_state = sel
    else:
        # No selection: overwrite character under cursor.
        buff.insert_text(data, overwrite=True, move_cursor=False)
    event.app.helix_state.input_mode = InputMode.NAVIGATION
    event.app.helix_state.select_mode = False


@add_cmd(
    keys=["enter", "c-j"],
    filter=helix_insert_mode & is_multiline,
    hidden=True,
    name="helix-newline",
)
def helix_newline(event: KeyPressEvent) -> None:
    """Insert newline."""
    event.current_buffer.newline(copy_margin=not in_paste_mode())


@add_cmd(
    keys=["enter"],
    filter=helix_insert_mode & is_returnable & ~is_multiline,
    hidden=True,
    name="helix-accept-line",
)
def helix_accept_line(event: KeyPressEvent) -> None:
    """Accept line."""
    event.current_buffer.validate_and_handle()


@add_cmd(
    keys=["backspace", "c-h"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-delete-backward",
)
def helix_delete_backward(event: KeyPressEvent) -> None:
    """Delete character backward."""
    event.current_buffer.delete_before_cursor(count=event.arg)


@add_cmd(
    keys=["delete", "c-d"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-delete-forward",
)
def helix_delete_forward(event: KeyPressEvent) -> None:
    """Delete character forward."""
    event.current_buffer.delete(count=event.arg)


@add_cmd(
    keys=["c-w", "A-backspace"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-delete-word-backward",
)
def helix_delete_word_backward(event: KeyPressEvent) -> None:
    """Delete word backward."""
    buff = event.current_buffer
    pos = buff.document.find_start_of_previous_word()
    if pos:
        buff.delete_before_cursor(count=-pos)


@add_cmd(
    keys=["A-d", "A-delete"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-delete-word-forward",
)
def helix_delete_word_forward(event: KeyPressEvent) -> None:
    """Delete word forward."""
    buff = event.current_buffer
    pos = buff.document.find_next_word_ending()
    if pos:
        buff.delete(count=pos)


@add_cmd(
    keys=["c-u"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-kill-to-line-start",
)
def helix_kill_to_line_start(event: KeyPressEvent) -> None:
    """Kill to start of line."""
    buff = event.current_buffer
    pos = buff.document.get_start_of_line_position()
    if pos:
        buff.delete_before_cursor(count=-pos)


@add_cmd(
    keys=["c-k"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-kill-to-line-end",
)
def helix_kill_to_line_end(event: KeyPressEvent) -> None:
    """Kill to end of line."""
    buff = event.current_buffer
    pos = buff.document.get_end_of_line_position()
    if pos:
        buff.delete(count=pos)


@add_cmd(
    keys=["c-i"],
    filter=helix_insert_mode & cursor_in_leading_ws,
    hidden=True,
    name="helix-insert-indent",
)
def helix_insert_indent(event: KeyPressEvent) -> None:
    """Indent lines."""
    buffer = event.current_buffer
    current_row = buffer.document.cursor_position_row
    indent(buffer, current_row, current_row + event.arg)


@add_cmd(
    keys=["s-tab"],
    filter=helix_insert_mode & cursor_in_leading_ws,
    hidden=True,
    name="helix-insert-unindent",
)
def helix_insert_unindent(event: KeyPressEvent) -> None:
    """Unindent lines."""
    current_row = event.current_buffer.document.cursor_position_row
    unindent(event.current_buffer, current_row, current_row + event.arg)


# Arrow keys in insert mode


@add_cmd(
    keys=["left"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-left",
)
def helix_insert_left(event: KeyPressEvent) -> None:
    """Move left in insert mode."""
    buff = event.current_buffer
    buff.cursor_position = max(0, buff.cursor_position - event.arg)


@add_cmd(
    keys=["right"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-right",
)
def helix_insert_right(event: KeyPressEvent) -> None:
    """Move right in insert mode."""
    buff = event.current_buffer
    buff.cursor_position = min(len(buff.text), buff.cursor_position + event.arg)


@add_cmd(
    keys=["up"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-up",
)
def helix_insert_up(event: KeyPressEvent) -> None:
    """Move up in insert mode."""
    event.current_buffer.cursor_up()


@add_cmd(
    keys=["down"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-down",
)
def helix_insert_down(event: KeyPressEvent) -> None:
    """Move down in insert mode."""
    event.current_buffer.cursor_down()


@add_cmd(
    keys=["home"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-home",
)
def helix_insert_home(event: KeyPressEvent) -> None:
    """Move to start of line in insert mode."""
    buff = event.current_buffer
    buff.cursor_position += buff.document.get_start_of_line_position()


@add_cmd(
    keys=["end"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-end",
)
def helix_insert_end(event: KeyPressEvent) -> None:
    """Move to end of line in insert mode."""
    buff = event.current_buffer
    buff.cursor_position += buff.document.get_end_of_line_position()


# Handle unbound keys in navigation mode (do nothing)


@add_cmd(
    keys=["<any>"],
    filter=(helix_normal_mode | helix_select_mode) & ~has_arg & ~waiting_for_char,
    hidden=True,
    name="helix-unbound-key",
)
def helix_unbound_key(event: KeyPressEvent) -> None:
    """Handle unbound keys in navigation mode - do nothing."""
    # Bell to indicate unbound key
    event.app.output.bell()


# Autocomplete trigger in insert mode


@add_cmd(
    keys=["c-x"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-autocomplete",
)
def helix_autocomplete(event: KeyPressEvent) -> None:
    """Trigger autocomplete."""
    buff = event.current_buffer
    buff.start_completion(select_first=False)


@add_cmd(
    keys=["c-r"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-insert-register",
)
def helix_insert_register(event: KeyPressEvent) -> None:
    """Insert register content."""
    # Wait for next key to determine which register
    # For now, insert from the default clipboard
    data = event.app.clipboard.get_data()
    event.current_buffer.insert_text(data.text)


# Completion in insert mode


@add_cmd(
    keys=["c-n"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-complete-next",
)
def helix_complete_next(event: KeyPressEvent) -> None:
    """Next completion."""
    buff = event.current_buffer
    if buff.complete_state:
        buff.complete_next()
    else:
        buff.start_completion(select_first=True)


@add_cmd(
    keys=["c-p"],
    filter=helix_insert_mode,
    hidden=True,
    name="helix-complete-prev",
)
def helix_complete_prev(event: KeyPressEvent) -> None:
    """Previous completion."""
    buff = event.current_buffer
    if buff.complete_state:
        buff.complete_previous()
    else:
        buff.start_completion(select_last=True)


def load_helix_bindings() -> KeyBindingsBase:
    """Load Helix key bindings.

    Returns:
        A KeyBindings object with Helix-style bindings.
    """
    kb = KeyBindings()

    # Bind all helix commands
    helix_commands = [
        "helix-normal-mode",
        "helix-insert-mode",
        "helix-append-mode",
        "helix-insert-line-start",
        "helix-insert-line-end",
        "helix-open-below",
        "helix-open-above",
        "helix-move-left",
        "helix-move-right",
        "helix-move-down",
        "helix-move-up",
        "helix-select-next-word-start",
        "helix-select-next-long-word-start",
        "helix-select-prev-word-start",
        "helix-select-prev-long-word-start",
        "helix-select-next-word-end",
        "helix-select-next-long-word-end",
        "helix-extend-line-below",
        "helix-extend-to-line-bounds",
        "helix-find-char",
        "helix-find-char-backward",
        "helix-find-till-char",
        "helix-find-till-char-backward",
        "helix-select-mode",
        "helix-exit-select-mode",
        "helix-delete-selection",
        "helix-delete-char",
        "helix-change-selection",
        "helix-change-char",
        "helix-replace-char",
        "helix-replace-with-yanked",
        "helix-switch-case",
        "helix-to-lowercase",
        "helix-to-uppercase",
        "helix-yank",
        "helix-paste-after",
        "helix-paste-before",
        "helix-undo",
        "helix-redo",
        "helix-indent",
        "helix-unindent",
        "helix-collapse-selection",
        "helix-flip-selection",
        "helix-select-all",
        "helix-join-lines",
        "helix-enter-goto-mode",
        "helix-goto-file-start",
        "helix-goto-file-end",
        "helix-goto-line-start",
        "helix-goto-line-end",
        "helix-goto-first-nonwhitespace",
        "helix-goto-window-top",
        "helix-goto-window-center",
        "helix-goto-window-bottom",
        "helix-exit-goto-mode",
        "helix-enter-match-mode",
        "helix-goto-matching-bracket",
        "helix-exit-match-mode",
        "helix-enter-view-mode",
        "helix-view-center",
        "helix-view-top",
        "helix-view-bottom",
        "helix-scroll-down",
        "helix-scroll-up",
        "helix-page-down",
        "helix-page-up",
        "helix-half-page-up",
        "helix-half-page-down",
        "helix-exit-view-mode",
        "helix-search-forward",
        "helix-search-backward",
        "helix-search-next",
        "helix-search-prev",
        "helix-search-selection",
        "helix-accept-search",
        "helix-stop-search",
        "helix-arg-0",
        "helix-self-insert",
        "helix-replace-insert",
        "helix-replace-single-char",
        "helix-newline",
        "helix-accept-line",
        "helix-delete-backward",
        "helix-delete-forward",
        "helix-delete-word-backward",
        "helix-delete-word-forward",
        "helix-kill-to-line-start",
        "helix-kill-to-line-end",
        "helix-insert-indent",
        "helix-insert-unindent",
        "helix-insert-left",
        "helix-insert-right",
        "helix-insert-up",
        "helix-insert-down",
        "helix-insert-home",
        "helix-insert-end",
        "helix-complete-next",
        "helix-complete-prev",
        "helix-unbound-key",
        "helix-handle-find-char",
        "helix-home",
        "helix-end",
        "helix-goto-line",
        "helix-goto-column",
        "helix-repeat-last-motion",
        "helix-keep-primary-selection",
        "helix-jump-forward",
        "helix-jump-backward",
        "helix-commit-undo",
        "helix-remove-primary-selection",
        "helix-select-regex",
        "helix-split-selection",
        "helix-split-selection-newlines",
        "helix-align-selections",
        "helix-trim-selections",
        "helix-copy-selection-below",
        "helix-copy-selection-above",
        "helix-delete-selection-noyank",
        "helix-delete-char-noyank",
        "helix-change-selection-noyank",
        "helix-change-char-noyank",
        "helix-autocomplete",
        "helix-insert-register",
        "helix-toggle-comments",
        "helix-add-newline-below",
        "helix-add-newline-above",
    ]

    # Add numeric argument commands
    for n in "123456789":
        helix_commands.append(f"helix-arg-{n}")

    for name in helix_commands:
        try:
            get_cmd(name).bind(kb)
        except KeyError:
            log.warning("Command %s not found", name)

    return ConditionalKeyBindings(kb, helix_mode)


def load_helix_search_bindings() -> KeyBindingsBase:
    """Load Helix search key bindings.

    Returns:
        A KeyBindings object with Helix search bindings.
    """
    kb = KeyBindings()
    for name in (
        "helix-search-forward",
        "helix-search-backward",
        "helix-search-next",
        "helix-search-prev",
        "helix-search-selection",
        "helix-accept-search",
        "helix-stop-search",
    ):
        try:
            get_cmd(name).bind(kb)
        except KeyError:
            log.warning("Command %s not found", name)
    return ConditionalKeyBindings(kb, helix_mode)
