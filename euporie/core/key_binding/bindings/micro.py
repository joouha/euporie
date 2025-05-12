"""Define editor key-bindings and commands for the micro editing mode."""

from __future__ import annotations

import logging
import re
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.buffer import indent, unindent
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    buffer_has_focus,
    has_selection,
    in_paste_mode,
    is_multiline,
    shift_selection_mode,
)
from prompt_toolkit.key_binding import ConditionalKeyBindings
from prompt_toolkit.key_binding.bindings.named_commands import (
    accept_line,
    backward_delete_char,
    backward_word,
    beginning_of_buffer,
    delete_char,
    end_of_buffer,
    forward_word,
    get_by_name,
)
from prompt_toolkit.key_binding.bindings.scroll import (
    scroll_backward,
    scroll_forward,
    scroll_half_page_down,
    scroll_half_page_up,
    scroll_one_line_down,
    scroll_one_line_up,
)
from prompt_toolkit.keys import Keys
from prompt_toolkit.selection import SelectionState, SelectionType

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd, get_cmd
from euporie.core.filters import (
    buffer_is_code,
    buffer_is_markdown,
    cursor_at_start_of_line,
    cursor_in_leading_ws,
    has_suggestion,
    insert_mode,
    is_returnable,
    micro_insert_mode,
    micro_mode,
    micro_recording_macro,
    micro_replace_mode,
)
from euporie.core.key_binding.micro_state import MicroInputMode
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.key_binding.utils import if_no_repeat

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase, KeyPressEvent

    from euporie.core.config import Config

log = logging.getLogger(__name__)


class EditMode:
    """Micro style editor key-bindings."""


# Register default bindings for micro edit mode
register_bindings(
    {
        "euporie.core.key_binding.bindings.micro:EditMode": {
            "move-cursor-right": "right",
            "move-cursor-left": "left",
            "newline": "enter",
            "accept-line": "enter",
            "backspace": ["backspace", "c-h"],
            "backward-kill-word": [
                "c-backspace",
                "A-backspace",
                ("c-A-h"),
                ("escape", "c-h"),
            ],
            "start-selection": [
                "s-up",
                "s-down",
                "s-right",
                "s-left",
                ("A-s-left"),
                ("A-s-right"),
                "c-s-left",
                "c-s-right",
                "s-home",
                "s-end",
                "c-s-home",
                "c-s-end",
            ],
            "extend-selection": [
                "s-up",
                "s-down",
                "s-right",
                "s-left",
                ("A-s-left"),
                ("A-s-right"),
                "c-s-left",
                "c-s-right",
                "s-home",
                "s-end",
                "c-s-home",
                "c-s-end",
            ],
            "cancel-selection": [
                "up",
                "down",
                "right",
                "left",
                ("A-left"),
                ("A-right"),
                "c-left",
                "c-right",
                "home",
                "end",
                "c-home",
                "c-end",
            ],
            "replace-selection": "<any>",
            "delete-selection": ["delete", "backspace", "c-h"],
            "backward-word": ["c-left", ("A-b")],
            "forward-word": ["c-right", ("A-f")],
            "move-lines-up": ("A-up"),
            "move-lines-down": ("A-down"),
            "go-to-start-of-line": ["home", ("A-left"), ("A-a")],
            "go-to-end-of-line": ["end", ("A-right"), ("A-e")],
            "beginning-of-buffer": ["c-up", "c-home"],
            "end-of-buffer": ["c-down", "c-end"],
            "go-to-start-of-paragraph": ("A-{"),
            "go-to-end-of-paragraph": ("A-}"),
            "indent-lines": "tab",
            "unindent-line": "backspace",
            "unindent-lines": "s-tab",
            "undo": "c-z",
            "redo": "c-y",
            "copy-selection": "c-c",
            "cut-selection": ["c-x", "s-delete"],
            "cut-line": "c-k",
            "duplicate-line": "c-d",
            "duplicate-selection": "c-d",
            "paste-clipboard": "c-v",
            "select-all": "c-a",
            "delete": "delete",
            "toggle-case": "f4",
            "toggle-overwrite-mode": "insert",
            "start-macro": "c-u",
            "end-macro": "c-u",
            "run-macro": "c-j",
            "accept-suggestion": ["right", "c-f"],
            "fill-suggestion": ("A-f"),
            "toggle-comment": "c-_",
            "go-to-matching-bracket": [("A-("), ("A-)")],
            'wrap-selection-""': '"',
            "wrap-selection-''": "'",
            "wrap-selection-()": ["(", ")"],
            "wrap-selection-{}": ["{", "}"],
            "wrap-selection-[]": ["[", "]"],
            "wrap-selection-``": "`",
            "wrap-selection-**": "*",
            "wrap-selection-__": "_",
        },
    }
)


def load_micro_bindings(config: Config | None = None) -> KeyBindingsBase:
    """Load editor key-bindings in the style of the ``micro`` text editor."""
    return ConditionalKeyBindings(
        load_registered_bindings(
            "euporie.core.key_binding.bindings.micro:EditMode", config=config
        ),
        micro_mode,
    )


# Commands


@add_cmd(
    filter=buffer_has_focus,
)
def toggle_overwrite_mode() -> None:
    """Toggle overwrite when using micro editing mode."""
    if micro_replace_mode():
        get_app().micro_state.input_mode = MicroInputMode.INSERT
    elif micro_insert_mode():
        get_app().micro_state.input_mode = MicroInputMode.REPLACE


@add_cmd(
    filter=buffer_has_focus & ~micro_recording_macro,
    hidden=True,
)
def start_macro() -> None:
    """Start recording a macro."""
    get_app().micro_state.start_macro()


@add_cmd(
    filter=buffer_has_focus & micro_recording_macro,
    hidden=True,
)
def end_macro() -> None:
    """Stop recording a macro."""
    get_app().micro_state.end_macro()


@add_cmd(
    filter=buffer_has_focus,
    record_in_macro=False,
    hidden=True,
)
def run_macro() -> None:
    """Re-execute the last keyboard macro defined."""
    # Insert the macro.
    app = get_app()
    macro = app.micro_state.macro
    if macro:
        app.key_processor.feed_multiple(macro, first=True)


add_cmd(
    name="backspace",
    title="Delete previous character",
    filter=buffer_has_focus & ~has_selection,
    save_before=if_no_repeat,
)(backward_delete_char)
add_cmd(
    title="Delete character", name="delete", filter=buffer_has_focus & ~has_selection
)(delete_char)


@add_cmd(title="Delete previous word", filter=buffer_has_focus)
def backward_kill_word(event: KeyPressEvent) -> None:
    """Delete the word behind the cursor, using whitespace as a word boundary."""
    buff = event.current_buffer
    pos = buff.document.find_start_of_previous_word()

    # Delete until the start of the document if nothing is found
    if pos is None:
        pos = -buff.cursor_position
    # Delete the word
    if pos:
        buff.delete_before_cursor(count=-pos)
    else:
        # Nothing to delete. Bell.
        event.app.output.bell()


# Navigation

add_cmd(
    title="Move back one word",
    filter=buffer_has_focus,
)(backward_word)
add_cmd(
    title="Move forward one word",
    filter=buffer_has_focus,
)(forward_word)
add_cmd(
    title="Move to the beginning of the input",
    filter=buffer_has_focus,
)(beginning_of_buffer)
add_cmd(
    title="Move to the end of the input",
    filter=buffer_has_focus,
)(end_of_buffer)

add_cmd(
    filter=buffer_has_focus,
)(scroll_backward)
add_cmd(
    filter=buffer_has_focus,
)(scroll_forward)
add_cmd(
    title="Scroll down half a page",
    filter=buffer_has_focus,
)(scroll_half_page_down)
add_cmd(
    title="Scroll up half a page",
    filter=buffer_has_focus,
)(scroll_half_page_up)
add_cmd(
    title="Scroll down one line",
    filter=buffer_has_focus,
)(scroll_one_line_down)
add_cmd(
    title="Scroll up one line",
    filter=buffer_has_focus,
)(scroll_one_line_up)


@add_cmd(
    filter=buffer_has_focus,
)
def move_cursor_left() -> None:
    """Move back a character, or up a line."""
    get_app().current_buffer.cursor_position -= 1


@add_cmd(
    filter=buffer_has_focus,
)
def move_cursor_right() -> None:
    """Move forward a character, or down a line."""
    get_app().current_buffer.cursor_position += 1


@add_cmd(
    filter=buffer_has_focus & ~shift_selection_mode,
)
def go_to_start_of_line() -> None:
    """Move the cursor to the start of the line."""
    buff = get_app().current_buffer
    buff.cursor_position += buff.document.get_start_of_line_position(
        after_whitespace=not cursor_in_leading_ws()
        or buff.document.cursor_position_col == 0
    )


@add_cmd(
    name="go-to-end-of-line",
    filter=buffer_has_focus & ~shift_selection_mode,
)
def go_to_end_of_line() -> None:
    """Move the cursor to the end of the line."""
    buff = get_app().current_buffer
    buff.cursor_position += buff.document.get_end_of_line_position()


@add_cmd(
    filter=buffer_has_focus,
)
def go_to_start_of_paragraph() -> None:
    """Move the cursor to the start of the current paragraph."""
    buf = get_app().current_buffer
    buf.cursor_position += buf.document.start_of_paragraph()


@add_cmd(
    filter=buffer_has_focus,
)
def go_to_end_of_paragraph() -> None:
    """Move the cursor to the end of the current paragraph."""
    buffer = get_app().current_buffer
    buffer.cursor_position += buffer.document.end_of_paragraph()


# Editing


@add_cmd(
    filter=buffer_has_focus & buffer_is_code,
)
def toggle_comment() -> None:
    """Comment or uncomments the current or selected lines."""
    comment = "# "
    buffer = get_app().current_buffer
    document = buffer.document
    selection_state = buffer.selection_state
    lines = buffer.text.splitlines(keepends=False)

    start, end = (
        document.translate_index_to_position(x)[0] for x in document.selection_range()
    )
    cursor_in_first_line = document.cursor_position_row == start
    # Only remove comments if all lines in the selection have a comment
    uncommenting = all(
        line.lstrip().startswith(comment.rstrip()) for line in lines[start : end + 1]
    )
    if uncommenting:
        for i in range(start, end + 1):
            if not lines:
                lines = [""]
            # Replace the first instance of the comment in each line
            lines[i] = lines[i].replace(comment, "", 1)
            if len(lines[i]) < len(comment):
                # The line might be blank and have trailing whitespace removed
                lines[i] = lines[i].replace(comment.rstrip(), "", 1)
        # Find cursor and selection column positions
        cur_col = document.translate_index_to_position(buffer.cursor_position)[1]
        if selection_state is not None:
            sel_col = document.translate_index_to_position(
                selection_state.original_cursor_position
            )[1]
        # Move cursor & adjust selection
        if cursor_in_first_line:
            bcp = buffer.cursor_position - min(len(comment), cur_col)
            if selection_state is not None:
                selection_state.original_cursor_position -= len(comment) * (
                    end - start
                ) + min(len(comment), sel_col)
        else:
            if selection_state is not None:
                selection_state.original_cursor_position -= min(len(comment), sel_col)
            bcp = buffer.cursor_position - (
                len(comment) * (end - start) + min(len(comment), cur_col)
            )
    else:
        # Find the minimum leading whitespace in the selected lines
        whitespace = min(
            len(line) - len(line.lstrip()) for line in lines[start : end + 1]
        )
        for i in range(start, end + 1):
            # Add a comment after the minimum leading whitespace to each line
            line = lines[i]
            lines[i] = line[:whitespace] + comment + line[whitespace:]
        # Move cursor & adjust selection
        if cursor_in_first_line:
            bcp = buffer.cursor_position + len(comment)
            if selection_state is not None:
                selection_state.original_cursor_position += len(comment) * (
                    end - start + 1
                )
        else:
            if selection_state is not None:
                selection_state.original_cursor_position += len(comment)
            bcp = buffer.cursor_position + len(comment) * (end - start + 1)

    # Set the buffer text, curor position and selection state
    buffer.document = Document("\n".join(lines), bcp)
    buffer.selection_state = selection_state


def wrap_selection_cmd(left: str, right: str) -> None:
    """Add strings to either end of the current selection."""
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    for start, end in buffer.document.selection_ranges():
        buffer.transform_region(start, end, lambda s: f"{left}{s}{right}")
    # keep the selection of the inner expression
    buffer.cursor_position += len(left)
    if selection_state is not None:
        selection_state.original_cursor_position += len(left)
    buffer.selection_state = selection_state


WRAP_PAIRS: dict[str, list[str]] = {
    "code": [
        '""',
        "''",
        "()",
        "{}",
        "[]",
    ],
    "markdown": [
        "``",
        "**",
        "__",
        "<>",
    ],
}

for pair in WRAP_PAIRS["code"]:
    left, right = list(pair)
    add_cmd(
        name=f"wrap-selection-{pair}",
        title=f"Wrap selection in {pair}",
        description=f"Wraps the current selection with: {pair}",
        filter=buffer_has_focus & has_selection & buffer_is_code,
    )(partial(wrap_selection_cmd, left, right))


for pair in WRAP_PAIRS["markdown"]:
    left, right = list(pair)
    add_cmd(
        name=f"wrap-selection-{pair}",
        # keys=sorted(set(pair)),
        title=f"Wrap selection in {pair}",
        description=f"Wraps the current selection with: {pair}",
        filter=buffer_has_focus & has_selection & buffer_is_markdown,
    )(partial(wrap_selection_cmd, left, right))


@add_cmd(
    filter=buffer_has_focus & ~has_selection,
)
def duplicate_line() -> None:
    """Duplicate the current line."""
    buffer = get_app().current_buffer
    line = buffer.document.current_line
    eol = buffer.document.get_end_of_line_position()
    buffer.cursor_position += eol
    buffer.newline(copy_margin=False)
    buffer.insert_text(line)
    buffer.cursor_position -= eol


@add_cmd(
    filter=buffer_has_focus & has_selection,
)
def duplicate_selection() -> None:
    """Duplicate the current selection."""
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    from_, to = buffer.document.selection_range()
    text = buffer.document.text[from_:to]
    buffer.insert_text(text)
    buffer.selection_state = selection_state


@add_cmd(
    title="Paste",
    filter=buffer_has_focus,
)
def paste_clipboard() -> None:
    """Pate the clipboard contents, replacing any current selection."""
    app = get_app()
    buff = app.current_buffer
    if buff.selection_state:
        buff.cut_selection()
    buff.paste_clipboard_data(app.clipboard.get_data())


@add_cmd(
    title="Copy",
    filter=has_selection,
)
def copy_selection() -> None:
    """Add the current selection to the clipboard."""
    app = get_app()
    buffer = app.current_buffer
    selection_state = buffer.selection_state
    data = buffer.copy_selection()
    buffer.selection_state = selection_state
    app.clipboard.set_data(data)


@add_cmd(
    title="Cut",
    filter=has_selection,
)
def cut_selection() -> None:
    """Remove the current selection and adds it to the clipboard."""
    data = get_app().current_buffer.cut_selection()
    get_app().clipboard.set_data(data)


@add_cmd(
    filter=buffer_has_focus,
)
def cut_line() -> None:
    """Remove the current line adds it to the clipboard."""
    app = get_app()
    buffer = app.current_buffer
    clipboard = app.clipboard
    clipboard_text = clipboard.get_data().text
    line = buffer.document.current_line
    clipboard.set_text(f"{clipboard_text}\n{line}")
    lines = buffer.document.lines[:]
    del lines[buffer.document.cursor_position_row]
    text = "\n".join(lines)
    buffer.document = Document(
        text,
        min(
            buffer.cursor_position + buffer.document.get_start_of_line_position(),
            len(text),
        ),
    )


def move_line(n: int) -> None:
    """Move the current or selected lines up or down by one or more lines."""
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    lines = buffer.text.splitlines(keepends=False)
    start, end = (
        buffer.document.translate_index_to_position(x)[0]
        for x in buffer.document.selection_range()
    )
    end += 1
    # Check that we are not moving lines off the edge of the document
    if start + n < 0 or end > len(lines):
        return
    # Rearrange the lines
    sel_lines = lines[start:end]
    lines_new = lines[:start] + lines[end:]
    lines_new = lines_new[: start + n] + sel_lines + lines_new[start + n :]
    # Calculate the new cursor position
    row = buffer.document.cursor_position_row
    col = buffer.document.cursor_position_col
    text = "\n".join(lines_new)
    cursor_position_new = Document(text).translate_row_col_to_index(row + n, col)
    cursor_position_diff = buffer.cursor_position - cursor_position_new
    # Update the selection if we have one
    if selection_state:
        selection_state.original_cursor_position -= cursor_position_diff
    # Update the buffer contents
    buffer.document = Document(text, cursor_position_new)
    buffer.selection_state = selection_state


@add_cmd(
    filter=buffer_has_focus,
)
def move_lines_up() -> None:
    """Move the current or selected lines up by one line."""
    move_line(-1)


@add_cmd(
    filter=buffer_has_focus,
)
def move_lines_down() -> None:
    """Move the current or selected lines down by one line."""
    move_line(1)


add_cmd(
    filter=insert_mode & is_returnable & ~is_multiline,
    description="Accept an input.",
)(accept_line)


def dent_buffer(event: KeyPressEvent, indenting: bool = True) -> None:
    """Indent or unindent the current or selected lines in a buffer."""
    buffer = get_app().current_buffer
    document = buffer.document
    selection_state = buffer.selection_state
    cursor_position = buffer.cursor_position
    lines = buffer.document.lines

    # Apply indentation end the selected range
    start, end = (
        document.translate_index_to_position(x)[0] for x in document.selection_range()
    )
    dent_func = indent if indenting else unindent
    dent_func(buffer, start, end + 1)

    # If there is a selection, adjust the selection range
    if selection_state:
        # Calculate the direction of the change
        sign = indenting * 2 - 1
        # Determine which lines were affected
        lines_affected = {
            i: indenting or lines[i][:1] == " " for i in range(start, end + 1)
        }
        total_lines_affected = sum(lines_affected.values())
        # If the cursor was in the first line, it will only move by the change of that line
        # otherwise it will move by the total change of all lines
        cursor_in_first_line = document.cursor_position_row == start
        diffs = (
            get_app().config.tab_size * total_lines_affected,
            get_app().config.tab_size * lines_affected[start],
        )
        # Do not move the cursor or the start of the selection back onto a previous line
        buffer.cursor_position = (
            cursor_position
            + max(
                diffs[cursor_in_first_line],
                document.get_start_of_line_position(),
            )
            * sign
        )
        og_cursor_col = document.translate_index_to_position(
            selection_state.original_cursor_position
        )[1]
        selection_state.original_cursor_position += (
            max(
                diffs[not cursor_in_first_line],
                -og_cursor_col,
            )
            * sign
        )
        selection_state.original_cursor_position = max(
            min(selection_state.original_cursor_position, len(buffer.text)), 0
        )
    # Maintain the selection state before indentation
    buffer.selection_state = selection_state


@add_cmd(
    filter=buffer_has_focus & is_multiline,
)
def newline(event: KeyPressEvent) -> None:
    """Inert a new line, replacing any selection and indenting if appropriate."""
    # TODO https://git.io/J9GfI
    buffer = get_app().current_buffer
    document = buffer.document
    buffer.cut_selection()
    buffer.newline(copy_margin=not in_paste_mode())
    if buffer_is_code():
        pre = document.current_line_before_cursor.rstrip()
        post = document.current_line_after_cursor.lstrip()
        if post and post.strip()[0] in (")", "]", "}"):
            buffer.insert_text(
                "\n" + buffer.document.leading_whitespace_in_current_line,
                move_cursor=False,
                fire_event=False,
            )
        if pre and pre[-1:] in (":", "(", "[", "{"):
            dent_buffer(event)


@add_cmd(
    filter=(buffer_has_focus & (cursor_in_leading_ws | has_selection)),
)
def indent_lines(event: KeyPressEvent) -> None:
    """Inndent the current or selected lines."""
    dent_buffer(event)


@add_cmd(
    name="unindent-line",
    filter=cursor_in_leading_ws & ~has_selection & ~cursor_at_start_of_line,
)
@add_cmd(
    filter=buffer_has_focus
    & (cursor_in_leading_ws | has_selection)
    & (~cursor_at_start_of_line | cursor_at_start_of_line),
)
def unindent_lines(event: KeyPressEvent) -> None:
    """Unindent the current or selected lines."""
    dent_buffer(event, indenting=False)


@add_cmd(
    filter=buffer_has_focus,
)
def toggle_case() -> None:
    """Toggle the case of the current word or selection."""
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    if selection_state is None:
        start, end = buffer.document.find_boundaries_of_current_word()
        selection_state = SelectionState(buffer.cursor_position + start)
        selection_state.enter_shift_mode()
        buffer.cursor_position += end
    if selection_state is not None:
        cp = buffer.cursor_position
        text = buffer.cut_selection().text
        if text.islower():
            text = text.title()
        elif text.istitle():
            text = text.upper()
        else:
            text = text.lower()
        buffer.insert_text(text)
        buffer.cursor_position = cp
        buffer.selection_state = selection_state


@add_cmd(
    filter=buffer_has_focus,
)
def undo() -> None:
    """Undo the last edit."""
    get_app().current_buffer.undo()


@add_cmd(
    filter=buffer_has_focus,
)
def redo() -> None:
    """Redo the last edit."""
    get_app().current_buffer.redo()


# Selection


@add_cmd(
    filter=buffer_has_focus,
)
def select_all() -> None:
    """Select all text."""
    buffer = get_app().current_buffer
    buffer.selection_state = SelectionState(0)
    buffer.cursor_position = len(buffer.text)
    buffer.selection_state.enter_shift_mode()


def unshift_move(event: KeyPressEvent) -> None:
    """Handle keys in shift selection mode.

    When called with a shift + movement key press event, moves the cursor as if shift
    is not pressed.

    Args:
        event: The key press event to process

    """
    key = event.key_sequence[0].key

    if key == Keys.ShiftUp:
        event.current_buffer.auto_up(count=event.arg)
        return
    if key == Keys.ShiftDown:
        event.current_buffer.auto_down(count=event.arg)
        return

    # the other keys are handled through their readline command
    key_to_command: dict[tuple[Keys | str, ...], str] = {
        (Keys.ShiftLeft,): "move-cursor-left",
        (Keys.ShiftRight,): "move-cursor-right",
        (Keys.ShiftHome,): "go-to-start-of-line",
        (Keys.ShiftEnd,): "go-to-end-of-line",
        (
            Keys.Escape,
            Keys.ShiftLeft,
        ): "backward-word",
        (
            Keys.Escape,
            Keys.ShiftRight,
        ): "forward-word",
        (Keys.ControlShiftLeft,): "backward-word",
        (Keys.ControlShiftRight,): "forward-word",
        (Keys.ControlShiftHome,): "beginning-of-buffer",
        (Keys.ControlShiftEnd,): "end-of-buffer",
    }

    key_sequence = tuple(key_ress.key for key_ress in event.key_sequence)
    try:
        command = get_cmd(key_to_command[key_sequence])
    except KeyError:
        pass
    else:
        command.key_handler(event)


@add_cmd(filter=~has_selection, hidden=True)
def start_selection(event: KeyPressEvent) -> None:
    """Start a new selection."""
    # Take the current cursor position as the start of this selection.
    buff = event.current_buffer
    if buff.text:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)
        if buff.selection_state is not None:
            buff.selection_state.enter_shift_mode()

        # Then move the cursor
        original_position = buff.cursor_position
        unshift_move(event)
        if buff.cursor_position == original_position:
            # Cursor didn't actually move - so cancel selection
            # to avoid having an empty selection
            buff.exit_selection()


@add_cmd(filter=shift_selection_mode, hidden=True)
def extend_selection(event: KeyPressEvent) -> None:
    """Extend the selection."""
    # Just move the cursor, like shift was not pressed
    unshift_move(event)
    buff = event.current_buffer
    if (
        buff.selection_state is not None
        and buff.cursor_position == buff.selection_state.original_cursor_position
    ):
        # selection is now empty, so cancel selection
        buff.exit_selection()


@add_cmd(filter=has_selection, hidden=True)
def replace_selection(event: KeyPressEvent) -> None:
    """Replace selection by what is typed."""
    event.current_buffer.cut_selection()
    get_by_name("self-insert").call(event)


@add_cmd(filter=has_selection, hidden=True)
def delete_selection() -> None:
    """Delete the contents of the current selection."""
    get_app().current_buffer.cut_selection()


@add_cmd(filter=shift_selection_mode, hidden=True)
def cancel_selection(event: KeyPressEvent) -> None:
    """Cancel the selection."""
    event.current_buffer.exit_selection()
    # we then process the cursor movement
    key_press = event.key_sequence[0]
    event.key_processor.feed(key_press, first=True)


@add_cmd(
    filter=buffer_has_focus,
)
def go_to_matching_bracket(event: KeyPressEvent) -> None:
    """Go to matching bracket if the cursor is on a paired bracket."""
    buff = event.current_buffer
    buff.cursor_position += buff.document.find_matching_bracket_position()


@add_cmd(
    filter=has_suggestion,
)
def accept_suggestion(event: KeyPressEvent) -> None:
    """Accept suggestion."""
    b = get_app().current_buffer
    suggestion = b.suggestion
    if suggestion:
        b.insert_text(suggestion.text)


@add_cmd(
    filter=has_suggestion,
)
def fill_suggestion(event: KeyPressEvent) -> None:
    """Fill partial suggestion."""
    b = get_app().current_buffer
    suggestion = b.suggestion
    if suggestion:
        t = re.split(r"(\S+\s+)", suggestion.text)
        b.insert_text(next(x for x in t if x))
