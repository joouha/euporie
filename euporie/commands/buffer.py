# -*- coding: utf-8 -*-
import logging
from functools import partial

from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import indent, unindent
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    buffer_has_focus,
    completion_is_selected,
    emacs_mode,
    has_completions,
    has_focus,
    has_selection,
    in_paste_mode,
    is_done,
    is_multiline,
    shift_selection_mode,
    to_filter,
)
from prompt_toolkit.key_binding.bindings.named_commands import (
    backward_char,
    backward_delete_char,
    backward_kill_word,
    backward_word,
    beginning_of_buffer,
    beginning_of_line,
    delete_char,
    end_of_buffer,
    end_of_line,
    forward_char,
    forward_word,
    get_by_name,
    menu_complete,
    menu_complete_backward,
    self_insert,
)
from prompt_toolkit.key_binding.bindings.scroll import (
    scroll_backward,
    scroll_forward,
    scroll_half_page_down,
    scroll_half_page_up,
    scroll_one_line_down,
    scroll_one_line_up,
    scroll_page_down,
    scroll_page_up,
)
from prompt_toolkit.key_binding.key_bindings import Binding
from prompt_toolkit.keys import Keys
from prompt_toolkit.selection import SelectionState, SelectionType

from euporie.commands.registry import add, get
from euporie.config import config
from euporie.filters import (
    cell_is_code,
    cursor_in_leading_ws,
    has_suggestion,
    insert_mode,
    micro_recording_macro,
    micro_replace_mode,
)
from euporie.key_binding.micro_state import InputMode

log = logging.getLogger(__name__)


def if_no_repeat(event: "KeyPressEvent") -> bool:
    """Returns True when the previous event was delivered to another handler."""
    return not event.is_repeat


# Typing


@add(filter=buffer_has_focus, save_before=if_no_repeat)
def type_key(event: "KeyPressEvent") -> "None":
    event.current_buffer.insert_text(
        event.data * event.arg, overwrite=micro_replace_mode()
    )


@add(filter=buffer_has_focus)
def toggle_micro_input_mode() -> "None":
    if micro_replace_mode():
        get_app().micro_state.input_mode = InputMode.INSERT
    elif micro_insert_mode():
        get_app().micro_state.input_mode = InputMode.REPLACE


@add(filter=buffer_has_focus & ~micro_recording_macro)
def start_macro() -> None:
    """Start recording a macro."""
    get_app().micro_state.start_macro()


@add(filter=buffer_has_focus & micro_recording_macro)
def end_macro() -> None:
    """Stop recording a macro."""
    get_app().micro_state.end_macro()


@add(filter=buffer_has_focus, record_in_macro=False)
def run_macro() -> None:
    """Re-execute the last keyboard macro defined."""
    # Insert the macro.
    app = get_app()
    macro = app.micro_state.macro
    if macro:
        app.key_processor.feed_multiple(macro, first=True)


add(name="backspace", filter=~shift_selection_mode, save_before=if_no_repeat)(
    backward_delete_char
)
add(name="delete", filter=~shift_selection_mode)(delete_char)
add(filter=buffer_has_focus)(backward_kill_word)

# Naavigation

add(filter=buffer_has_focus)(backward_word)
add(filter=buffer_has_focus)(forward_word)
add(filter=buffer_has_focus)(beginning_of_buffer)
add(filter=buffer_has_focus)(end_of_buffer)

add(filter=buffer_has_focus)(scroll_backward)
add(filter=buffer_has_focus)(scroll_forward)
add(filter=buffer_has_focus)(scroll_half_page_down)
add(filter=buffer_has_focus)(scroll_half_page_up)
add(filter=buffer_has_focus)(scroll_one_line_down)
add(filter=buffer_has_focus)(scroll_one_line_up)
add(filter=buffer_has_focus)(scroll_page_down)
add(filter=buffer_has_focus)(scroll_page_up)


@add(
    filter=buffer_has_focus,
    description="Move the cursor forward a character, or down a line",
)
def move_cursor_left() -> "None":
    """Move back a character, or up a line."""
    get_app().current_buffer.cursor_position -= 1


@add(
    filter=buffer_has_focus,
    description="Move the cursor forward a character, or down a line",
)
def move_cursor_right() -> "None":
    """Move forward a character, or down a line."""
    get_app().current_buffer.cursor_position += 1


@add(
    filter=buffer_has_focus,
    description="Move the cursor to the start of the line",
)
def go_to_start_of_line() -> "None":
    buff = get_app().current_buffer
    buff.cursor_position += buff.document.get_start_of_line_position(
        after_whitespace=not cursor_in_leading_ws()
        or buff.document.cursor_position_col == 0
    )


@add(
    filter=buffer_has_focus,
    description="Move the cursor to the end of the line",
)
def go_to_end_of_line() -> "None":
    buff = get_app().current_buffer
    buff.cursor_position += buff.document.get_end_of_line_position()


@add(filter=buffer_has_focus)
def go_to_start_of_paragraph() -> "None":
    buf = get_app().current_buffer
    buf.cursor_position += buf.document.start_of_paragraph()


@add(filter=buffer_has_focus)
def go_to_end_of_paragraph() -> "None":
    buffer = get_app().current_buffer
    buffer.cursor_position += buf.document.end_of_paragraph()


# Editing


def wrap_selection(buffer, left, right=None):
    selection_state = buffer.selection_state

    for start, end in buffer.document.selection_ranges():
        buffer.transform_region(start, end, lambda s: f"{left}{s}{right}")

    # keep the selection of the inner expression
    # e.g. `echo |Hello World|` -> `echo "|Hello World|"`
    buffer.cursor_position += 1
    selection_state.original_cursor_position += 1
    buffer.selection_state = selection_state


def wrap_selection_cmd(left, right):
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    for start, end in buffer.document.selection_ranges():
        buffer.transform_region(start, end, lambda s: f"{left}{s}{right}")
    # keep the selection of the inner expression
    # e.g. `echo |Hello World|` -> `echo "|Hello World|"`
    buffer.cursor_position += 1
    selection_state.original_cursor_position += 1
    buffer.selection_state = selection_state


for pair in [
    '""',
    "''",
    "``",
    "()",
    "{}",
    "[]",
]:
    left, right = pair
    for key in set(pair):
        add(
            name=f"wrap-selection-{key}",
            keys=key,
            title="Wrap selection in {pair}",
            filter=buffer_has_focus & has_selection,
        )(partial(wrap_selection_cmd, left, right))


@add(
    filter=buffer_has_focus,
    description="Duplicate the current line",
)
def duplicate_line() -> "None":
    buffer = get_app().current_buffer
    line = buffer.document.current_line
    eol = buffer.document.get_end_of_line_position()
    buffer.cursor_position += eol
    buffer.newline()
    buffer.insert_text(line)
    buffer.cursor_position -= eol


@add(
    title="Paste",
    filter=buffer_has_focus,
    description="Paste the clipboard, replacing any current selection",
)
def paste_clipboard() -> "None":
    app = get_app()
    buff = app.current_buffer
    if buff.selection_state:
        buff.cut_selection()
    buff.paste_clipboard_data(app.clipboard.get_data())


@add(
    title="Copy",
    filter=has_selection,
    description="Adds the current selection to the clipboard",
)
def copy_selection() -> "None":
    app = get_app()
    data = app.current_buffer.copy_selection()
    app.clipboard.set_data(data)


@add(
    title="Cut",
    filter=has_selection,
    description="Removes the current selection and adds it to the clipboard",
)
def cut_selection() -> "None":
    data = get_app().current_buffer.cut_selection()
    get_app().clipboard.set_data(data)


@add(
    filter=buffer_has_focus,
    description="Removes the current line adds it to the clipboard",
)
def cut_line() -> "None":
    app = get_app()
    buffer = app.current_buffer
    clipboard = app.clipboard
    clipboard_text = clipboard.get_data().text
    line = buffer.document.current_line
    clipboard.set_text(f"{clipboard_text}\n{line}")
    lines = buffer.document.lines[:]
    del lines[buffer.document.cursor_position_row]
    buffer.document = Document(
        "\n".join(lines),
        buffer.cursor_position + buffer.document.get_start_of_line_position(),
    )


def move_line(n: "int") -> "None":
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    lines = buffer.text.splitlines(keepends=False)
    start, end = map(
        lambda x: buffer.document.translate_index_to_position(x)[0],
        buffer.document.selection_range(),
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


@add(filter=buffer_has_focus)
def move_lines_up() -> "None":
    move_line(-1)


@add(filter=buffer_has_focus)
def move_lines_down() -> "None":
    move_line(1)


@add(filter=buffer_has_focus & is_multiline)
def newline(event: "KeyPressEvent") -> "None":
    """Insert a new line, replacing any selection."""
    buffer = get_app().current_buffer
    buffer.cut_selection()
    buffer.newline(copy_margin=not in_paste_mode())

    if cell_is_code():
        pre = buffer.document.text_before_cursor
        if pre.rstrip()[-1:] in (":", "(", "[", "{"):
            dent_buffer(event)
    # TODO
    # post = buffer.document.text_after_cursor
    # if post.lstrip()[0:1] in (")", "]", "}"):


def dent_buffer(event: "KeyPressEvent", un: "bool" = False) -> "None":
    buffer = get_app().current_buffer
    selection_state = buffer.selection_state
    cursor_position = buffer.cursor_position
    lines = buffer.document.lines

    # Apply indentation to the selected range
    from_, to = map(
        lambda x: buffer.document.translate_index_to_position(x)[0],
        buffer.document.selection_range(),
    )
    dent = unindent if un else indent
    dent(buffer, from_, to + 1, count=event.arg)

    # If there is a selection, indent it and adjust the selection range
    if selection_state:
        change = config.tab_size * (un * -2 + 1)
        # Count how many lines will be affected
        line_count = 0
        for i in range(from_, to + 1):
            if not un or lines[i][:1] == " ":
                line_count += 1
        backwards = cursor_position < selection_state.original_cursor_position
        if un and not line_count:
            buffer.cursor_position = cursor_position
        else:
            buffer.cursor_position = max(
                0, cursor_position + change * (1 if backwards else line_count)
            )
            selection_state.original_cursor_position = max(
                0,
                selection_state.original_cursor_position
                + change * (line_count if backwards else 1),
            )

    # Maintain the selection state before indentation
    buffer.selection_state = selection_state


@add(filter=cursor_in_leading_ws | has_selection)
def indent_lines(event: "KeyPressEvent") -> "None":
    dent_buffer(event)


@add(name="unindent-line", filter=cursor_in_leading_ws & ~has_selection)
@add(filter=cursor_in_leading_ws | has_selection)
def unindent_lines(event: "KeyPressEvent") -> "None":
    dent_buffer(event, un=True)


@add(filter=buffer_has_focus)
def toggle_case():
    buffer = get_app().current_buffer
    if buffer.selection_state is None:
        cp = buffer.cursor_position
        start, end = buffer.document.find_boundaries_of_current_word()
        if start != 0 and end != 0:
            buffer.cursor_position += end
            buffer.selection_state = SelectionState(cp + start)
            buffer.selection_state.enter_shift_mode()
    selection_state = buffer.selection_state
    if selection_state is not None:
        text = buffer.cut_selection().text
        if text.islower():
            text = text.title()
        elif text.istitle():
            text = text.upper()
        else:
            text = text.lower()
        buffer.insert_text(text)
        buffer.selection_state = selection_state


@add(filter=buffer_has_focus)
def undo():
    get_app().current_buffer.undo()


@add(filter=buffer_has_focus)
def redo():
    get_app().current_buffer.redo()


# Selection


@add(
    filter=~has_selection,
)
def start_selection(event: "KeyPressEvent") -> "None":
    """
    Start selection with shift + movement.
    """
    # Take the current cursor position as the start of this selection.
    buff = event.current_buffer
    if buff.text:
        buff.start_selection(selection_type=SelectionType.CHARACTERS)

        if buff.selection_state is not None:
            # (`selection_state` should never be `None`, it is created by
            # `start_selection`.)
            buff.selection_state.enter_shift_mode()

        # Then move the cursor
        original_position = buff.cursor_position
        unshift_move(event)
        if buff.cursor_position == original_position:
            # Cursor didn't actually move - so cancel selection
            # to avoid having an empty selection
            buff.exit_selection()


@add(
    filter=shift_selection_mode,
)
def extend_selection(event: "KeyPressEvent") -> "None":
    """Extend the selection."""
    # Just move the cursor, like shift was not pressed
    unshift_move(event)
    buff = event.current_buffer
    if buff.selection_state is not None:
        if buff.cursor_position == buff.selection_state.original_cursor_position:
            # selection is now empty, so cancel selection
            buff.exit_selection()


@add(filter=has_selection)
def replace_selection(event: "KeyPressEvent") -> "None":
    """Replace selection by what is typed."""
    event.current_buffer.cut_selection()
    get_by_name("self-insert").call(event)


@add(filter=has_selection)
def delete_selection() -> "None":
    get_app().current_buffer.cut_selection()


def unshift_move(event: "KeyPressEvent") -> "None":
    """Used for the shift selection mode.

    When called with a shift + movement key press event, moves the cursor as if shift
    is not pressed.

    """
    key = event.key_sequence[0].key

    if key == Keys.ShiftUp:
        event.current_buffer.auto_up(count=event.arg)
        return
    if key == Keys.ShiftDown:
        event.current_buffer.auto_down(count=event.arg)
        return

    # the other keys are handled through their readline command
    key_to_command: Dict[Union[Keys, str], str] = {
        Keys.ShiftLeft: "move-cursor-left",
        Keys.ShiftRight: "move-cursor-right",
        Keys.ShiftHome: "go-to-start-of-line",
        Keys.ShiftEnd: "go-to-end-of-line",
        Keys.ControlShiftLeft: "backward-word",
        Keys.ControlShiftRight: "forward-word",
        Keys.ControlShiftHome: "beginning-of-buffer",
        Keys.ControlShiftEnd: "end-of-buffer",
    }

    try:
        command = get(key_to_command[key])
    except KeyError:
        pass
    else:
        command.key_handler(event)


@add(filter=shift_selection_mode)
def cancel_selection(event: "KeyPressEvent") -> "None":
    """Cancel the selection."""
    event.current_buffer.exit_selection()
    # we then process the cursor movement
    key_press = event.key_sequence[0]
    event.key_processor.feed(key_press, first=True)


@add(filter=buffer_has_focus)
def select_all() -> "None":
    buffer = get_app().current_buffer
    buffer.selection_state = SelectionState(0)
    buffer.cursor_position = len(buffer.text)
    buffer.selection_state.enter_shift_mode()
