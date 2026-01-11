"""Key bindings which are also known by GNU Readline by the given names.

This module ports the ``prompt_toolkit`` named commands to use the new command registry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apptk.commands import add_cmd, get_cmd
from apptk.document import Document
from apptk.filters import (
    buffer_has_focus,
    completion_is_selected,
    has_selection,
)
from apptk.filters.buffer import cursor_in_leading_ws
from apptk.filters.modes import insert_mode
from apptk.selection import SelectionState, SelectionType
from prompt_toolkit.key_binding.bindings.named_commands import _readline_commands

if TYPE_CHECKING:
    from apptk.key_binding.key_processor import KeyPressEvent

__all__ = ["get_by_name", "toggle_comments"]

log = logging.getLogger(__name__)

# Replace legacy named-command access methods
register = add_cmd
get_by_name = get_cmd

# Convert legacy named commands into Commands
for name, binding in _readline_commands.items():
    add_cmd(
        name=name,
        record_in_macro=binding.record_in_macro,
        save_before=binding.save_before,
        eager=binding.eager,
        filter=binding.filter,
    )(binding.handler)

# Update some commands

get_cmd("menu-complete").update(
    hidden=True,
    aliases=["next-completion"],
    description="Show the completion menu and select the next completion.",
).add_keys(
    keys=["c-i"],
    filter=buffer_has_focus & insert_mode & ~has_selection & ~cursor_in_leading_ws,
)

get_cmd("menu-complete-backward").update(
    hidden=True,
    aliases=["previous-completion"],
    description="Show the completion menu and select the previous completion.",
).add_keys(
    keys=["s-tab"],
    filter=buffer_has_focus
    & completion_is_selected
    & insert_mode
    & ~has_selection
    & ~cursor_in_leading_ws,
)


@add_cmd(
    name="insert-comment",
    filter=buffer_has_focus,
    hidden=True,
)
def insert_comment(event: KeyPressEvent) -> None:
    """Comment all lines and accept the input using language-aware prefixes.

    Without numeric argument, comment all lines.
    With numeric argument, uncomment all lines.
    In any case accept the input.
    """
    buff = event.current_buffer

    control = event.app.layout.current_control
    language = getattr(control, "language", None)
    comment_token = event.app.get_comment_prefix(language)

    if event.arg != 1:

        def change(line: str) -> str:
            if line.startswith(comment_token + " "):
                return line[len(comment_token) + 1 :]
            if line.startswith(comment_token):
                return line[len(comment_token) :]
            return line

    else:

        def change(line: str) -> str:
            return comment_token + " " + line

    buff.document = Document(
        text="\n".join(map(change, buff.text.splitlines())), cursor_position=0
    )

    # Accept input.
    buff.validate_and_handle()


@add_cmd(
    name="toggle-comments",
    aliases=["helix-toggle-comments", "micro-toggle-comments"],
    filter=buffer_has_focus,
    hidden=True,
)
def toggle_comments(event: KeyPressEvent) -> None:
    """Toggle line comments on the selected (or current) lines.

    Looks up the comment token for the current buffer's language via the
    application's :py:meth:`get_comment_prefix` method. Comments are
    inserted after the minimum leading whitespace of the affected
    non-blank lines. Cursor position and selection state are adjusted so
    they track the text changes.
    """
    app = event.app
    buffer = event.current_buffer

    # Determine the comment token from the buffer's language
    control = event.app.layout.current_control
    language = getattr(control, "language", None)
    comment_token = app.get_comment_prefix(language)
    comment = comment_token + " "

    doc = buffer.document
    had_selection = buffer.selection_state is not None

    # Determine line range
    start, end = (doc.translate_index_to_position(x)[0] for x in doc.selection_range())

    # Remember positions before the edit (translated on the OLD document)
    old_cursor = buffer.cursor_position
    old_cursor_row, old_cursor_col = doc.translate_index_to_position(old_cursor)
    if had_selection:
        old_anchor = buffer.selection_state.original_cursor_position
        old_anchor_row, old_anchor_col = doc.translate_index_to_position(old_anchor)
        sel_type = buffer.selection_state.type
    else:
        old_anchor_row = old_anchor_col = 0
        sel_type = SelectionType.CHARACTERS

    # Build new lines and per-line column deltas
    lines = list(doc.lines)
    all_commented = all(
        lines[i].lstrip().startswith(comment_token)
        for i in range(start, end + 1)
        if lines[i].strip()
    )

    deltas: dict[int, int] = {}

    if all_commented:
        for i in range(start, end + 1):
            line = lines[i]
            stripped = line.lstrip()
            indent_len = len(line) - len(stripped)
            if stripped.startswith(comment):
                lines[i] = line[:indent_len] + stripped[len(comment) :]
                deltas[i] = -len(comment)
            elif stripped.startswith(comment_token):
                lines[i] = line[:indent_len] + stripped[len(comment_token) :]
                deltas[i] = -len(comment_token)
            else:
                deltas[i] = 0
    else:
        whitespace = min(
            (
                len(lines[i]) - len(lines[i].lstrip())
                for i in range(start, end + 1)
                if lines[i].strip()
            ),
            default=0,
        )
        for i in range(start, end + 1):
            if lines[i].strip():
                line = lines[i]
                lines[i] = line[:whitespace] + comment + line[whitespace:]
                deltas[i] = len(comment)
            else:
                deltas[i] = 0

    new_text = "\n".join(lines)
    buffer.text = new_text
    new_doc = Document(new_text)

    def _adjust(row: int, col: int) -> int:
        new_col = max(0, col + deltas.get(row, 0))
        new_index = new_doc.translate_row_col_to_index(row, new_col)
        return max(0, min(new_index, len(new_text)))

    buffer.cursor_position = _adjust(old_cursor_row, old_cursor_col)

    if had_selection:
        buffer.selection_state = SelectionState(
            _adjust(old_anchor_row, old_anchor_col), sel_type
        )
