"""These are almost end-to-end tests.

They create a Prompt, feed it with some input and check the result.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import pytest
from apptk.clipboard import ClipboardData, InMemoryClipboard
from apptk.enums import EditingMode
from apptk.filters import ViInsertMode
from apptk.history import InMemoryHistory
from apptk.input.defaults import create_pipe_input
from apptk.key_binding.bindings.named_commands import prefix_meta
from apptk.key_binding.key_bindings import KeyBindings
from apptk.output import DummyOutput
from apptk.shortcuts import PromptSession

if TYPE_CHECKING:
    from apptk.application import Application
    from apptk.document import Document


def _history() -> InMemoryHistory:
    """Create a history with sample entries."""
    h = InMemoryHistory()
    h.append_string("line1 first input")
    h.append_string("line2 second input")
    h.append_string("line3 third input")
    return h


def _feed_cli_with_input(
    text: str,
    editing_mode: EditingMode = EditingMode.EMACS,
    clipboard: InMemoryClipboard | None = None,
    history: InMemoryHistory | None = None,
    multiline: bool = False,
    check_line_ending: bool = True,
    key_bindings: KeyBindings | None = None,
) -> tuple[Document, Application[str]]:
    """Create a Prompt, feed it with the given user input and return the CLI object.

    This returns a (result, Application) tuple.
    """
    from apptk.key_binding.vi_state import InputMode

    # If the given text doesn't end with a newline, the interface won't finish.
    if check_line_ending:
        assert text.endswith("\r")

    with create_pipe_input() as inp:
        inp.send_text(text)
        session = PromptSession(
            input=inp,
            output=DummyOutput(),
            editing_mode=editing_mode,
            history=history,
            multiline=multiline,
            clipboard=clipboard,
            key_bindings=key_bindings,
        )

        # Set Vi state to INSERT mode to match original prompt_toolkit behavior
        # that these tests were written for (apptk defaults to NAVIGATION mode)
        # if editing_mode == EditingMode.VI:
        #     session.app.vi_state.input_mode = InputMode.INSERT

        def set_vi_insert_mode() -> None:
            # Set Vi state to INSERT mode to match original prompt_toolkit behavior
            # that these tests were written for (apptk defaults to NAVIGATION mode)
            if editing_mode == EditingMode.VI:
                session.app.vi_state.input_mode = InputMode.INSERT

        _ = session.prompt(pre_run=set_vi_insert_mode)
        return session.default_buffer.document, session.app


def test_simple_text_input() -> None:
    """Test simple text input followed by enter."""
    # Simple text input, followed by enter.
    result, cli = _feed_cli_with_input("hello\r")
    assert result.text == "hello"
    assert cli.current_buffer.text == "hello"


def test_emacs_cursor_movements() -> None:
    """Test cursor movements with Emacs key bindings."""
    # ControlA (beginning-of-line)
    result, _cli = _feed_cli_with_input("hello\x01X\r")
    assert result.text == "Xhello"

    # ControlE (end-of-line)  # codespell:ignore ControlE
    result, _cli = _feed_cli_with_input("hello\x01X\x05Y\r")
    assert result.text == "XhelloY"

    # ControlH or \b
    result, _cli = _feed_cli_with_input("hello\x08X\r")
    assert result.text == "hellX"

    # Delete.  (Left, left, delete)
    result, _cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x1b[3~\r")
    assert result.text == "helo"

    # Left.
    result, _cli = _feed_cli_with_input("hello\x1b[DX\r")
    assert result.text == "hellXo"

    # ControlA, right
    result, _cli = _feed_cli_with_input("hello\x01\x1b[CX\r")
    assert result.text == "hXello"

    # ControlB (backward-char)
    result, _cli = _feed_cli_with_input("hello\x02X\r")
    assert result.text == "hellXo"

    # ControlF (forward-char)
    result, _cli = _feed_cli_with_input("hello\x01\x06X\r")
    assert result.text == "hXello"

    # ControlD: delete after cursor.
    result, _cli = _feed_cli_with_input("hello\x01\x04\r")
    assert result.text == "ello"

    # ControlD at the end of the input ssshould not do anything.
    result, _cli = _feed_cli_with_input("hello\x04\r")
    assert result.text == "hello"

    # Left, Left, ControlK  (kill-line)
    result, _cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x0b\r")
    assert result.text == "hel"  # codespell:ignore hel

    # Left, Left Esc- ControlK (kill-line, but negative)
    result, _cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x1b-\x0b\r")
    assert result.text == "lo"

    # ControlL: should not influence the result.  # codespell:ignore ControlL
    result, _cli = _feed_cli_with_input("hello\x0c\r")
    assert result.text == "hello"

    # ControlRight (forward-word)
    result, _cli = _feed_cli_with_input("hello world\x01X\x1b[1;5CY\r")
    assert result.text == "XhelloY world"

    # ContrlolLeft (backward-word)
    result, _cli = _feed_cli_with_input("hello world\x1b[1;5DY\r")
    assert result.text == "hello Yworld"

    # <esc>-f with argument. (forward-word)
    result, _cli = _feed_cli_with_input("hello world abc def\x01\x1b3\x1bfX\r")
    assert result.text == "hello world abcX def"

    # <esc>-f with negative argument. (forward-word)
    result, _cli = _feed_cli_with_input("hello world abc def\x1b-\x1b3\x1bfX\r")
    assert result.text == "hello Xworld abc def"

    # <esc>-b with argument. (backward-word)
    result, _cli = _feed_cli_with_input("hello world abc def\x1b3\x1bbX\r")
    assert result.text == "hello Xworld abc def"

    # <esc>-b with negative argument. (backward-word)
    result, _cli = _feed_cli_with_input("hello world abc def\x01\x1b-\x1b3\x1bbX\r")
    assert result.text == "hello world abc Xdef"

    # ControlW (kill-word / unix-word-rubout)
    result, cli = _feed_cli_with_input("hello world\x17\r")
    assert result.text == "hello "
    assert cli.clipboard.get_data().text == "world"

    result, _cli = _feed_cli_with_input("test hello world\x1b2\x17\r")
    assert result.text == "test "

    # Escape Backspace (unix-word-rubout)
    result, cli = _feed_cli_with_input("hello world\x1b\x7f\r")
    assert result.text == "hello "
    assert cli.clipboard.get_data().text == "world"

    result, cli = _feed_cli_with_input("hello world\x1b\x08\r")
    assert result.text == "hello "
    assert cli.clipboard.get_data().text == "world"

    # Backspace (backward-delete-char)
    result, _cli = _feed_cli_with_input("hello world\x7f\r")
    assert result.text == "hello worl"  # codespell:ignore worl
    assert result.cursor_position == len("hello worl")  # codespell:ignore worl

    result, _cli = _feed_cli_with_input("hello world\x08\r")
    assert result.text == "hello worl"  # codespell:ignore worl
    assert result.cursor_position == len("hello worl")  # codespell:ignore worl

    # Delete (delete-char)
    result, _cli = _feed_cli_with_input("hello world\x01\x1b[3~\r")
    assert result.text == "ello world"
    assert result.cursor_position == 0

    # Escape-\\ (delete-horizontal-space)
    result, _cli = _feed_cli_with_input("hello     world\x1b8\x02\x1b\\\r")
    assert result.text == "helloworld"
    assert result.cursor_position == len("hello")


def test_emacs_kill_multiple_words_and_paste() -> None:
    """Test killing multiple words and pasting them."""
    # Using control-w twice should place both words on the clipboard.
    result, cli = _feed_cli_with_input(
        "hello world test\x17\x17--\x19\x19\r"  # Twice c-w.  Twice c-y.
    )
    assert result.text == "hello --world testworld test"
    assert cli.clipboard.get_data().text == "world test"

    # Using alt-d twice should place both words on the clipboard.
    result, cli = _feed_cli_with_input(
        "hello world test"
        "\x1bb\x1bb"  # Twice left.
        "\x1bd\x1bd"  # Twice kill-word.
        "abc"
        "\x19"  # Paste.
        "\r"
    )
    assert result.text == "hello abcworld test"
    assert cli.clipboard.get_data().text == "world test"


def test_interrupts() -> None:
    """Test keyboard interrupts and EOF."""
    # ControlC: raise KeyboardInterrupt.
    with pytest.raises(KeyboardInterrupt):
        _result, _cli = _feed_cli_with_input("hello\x03\r")

    with pytest.raises(KeyboardInterrupt):
        _result, _cli = _feed_cli_with_input("hello\x03\r")

    # ControlD without any input: raises EOFError.
    with pytest.raises(EOFError):
        _result, _cli = _feed_cli_with_input("\x04\r")


def test_emacs_yank() -> None:
    """Test yanking from clipboard."""
    # ControlY (yank)
    c = InMemoryClipboard(ClipboardData("XYZ"))
    result, _cli = _feed_cli_with_input("hello\x02\x19\r", clipboard=c)
    assert result.text == "hellXYZo"
    assert result.cursor_position == len("hellXYZ")


def test_quoted_insert() -> None:
    """Test quoted insert functionality."""
    # ControlQ - ControlB (quoted-insert)
    result, _cli = _feed_cli_with_input("hello\x11\x02\r")
    assert result.text == "hello\x02"


def test_transformations() -> None:
    """Test text transformation commands."""
    # Meta-c (capitalize-word)
    result, _cli = _feed_cli_with_input("hello world\01\x1bc\r")
    assert result.text == "Hello world"
    assert result.cursor_position == len("Hello")

    # Meta-u (uppercase-word)
    result, _cli = _feed_cli_with_input("hello world\01\x1bu\r")
    assert result.text == "HELLO world"
    assert result.cursor_position == len("Hello")

    # Meta-u (downcase-word)
    result, _cli = _feed_cli_with_input("HELLO WORLD\01\x1bl\r")
    assert result.text == "hello WORLD"
    assert result.cursor_position == len("Hello")

    # ControlT (transpose-chars)
    result, _cli = _feed_cli_with_input("hello\x14\r")
    assert result.text == "helol"
    assert result.cursor_position == len("hello")

    # Left, Left, Control-T (transpose-chars)
    result, _cli = _feed_cli_with_input("abcde\x1b[D\x1b[D\x14\r")
    assert result.text == "abdce"
    assert result.cursor_position == len("abcd")


def test_emacs_other_bindings() -> None:
    """Test other Emacs key bindings."""
    # Transpose characters.
    result, _cli = _feed_cli_with_input("abcde\x14X\r")  # Ctrl-T
    assert result.text == "abcedX"

    # Left, Left, Transpose. (This is slightly different.)
    result, _cli = _feed_cli_with_input("abcde\x1b[D\x1b[D\x14X\r")
    assert result.text == "abdcXe"

    # Clear before cursor.
    result, _cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x15X\r")
    assert result.text == "Xlo"

    # unix-word-rubout: delete word before the cursor.
    # (ControlW).
    result, _cli = _feed_cli_with_input("hello world test\x17X\r")
    assert result.text == "hello world X"

    result, _cli = _feed_cli_with_input("hello world /some/very/long/path\x17X\r")
    assert result.text == "hello world X"

    # (with argument.)
    result, _cli = _feed_cli_with_input("hello world test\x1b2\x17X\r")
    assert result.text == "hello X"

    result, _cli = _feed_cli_with_input("hello world /some/very/long/path\x1b2\x17X\r")
    assert result.text == "hello X"

    # backward-kill-word: delete word before the cursor.
    # (Esc-ControlH).
    result, _cli = _feed_cli_with_input("hello world /some/very/long/path\x1b\x08X\r")
    assert result.text == "hello world /some/very/long/X"

    # (with arguments.)
    result, _cli = _feed_cli_with_input(
        "hello world /some/very/long/path\x1b3\x1b\x08X\r"
    )
    assert result.text == "hello world /some/very/X"


def test_controlx_controlx() -> None:
    """Test Control-X Control-X binding."""
    # At the end: go to the start of the line.
    result, _cli = _feed_cli_with_input("hello world\x18\x18X\r")
    assert result.text == "Xhello world"
    assert result.cursor_position == 1

    # At the start: go to the end of the line.
    result, _cli = _feed_cli_with_input("hello world\x01\x18\x18X\r")
    assert result.text == "hello worldX"

    # Left, Left Control-X Control-X: go to the end of the line.
    result, _cli = _feed_cli_with_input("hello world\x1b[D\x1b[D\x18\x18X\r")
    assert result.text == "hello worldX"


def test_emacs_history_bindings() -> None:
    """Test Emacs history navigation bindings."""
    # Adding a new item to the history.
    history = _history()
    result, _cli = _feed_cli_with_input("new input\r", history=history)
    assert result.text == "new input"
    assert history.get_strings()[-1] == "new input"

    # Go up in history, and accept the last item.
    result, _cli = _feed_cli_with_input("hello\x1b[A\r", history=history)
    assert result.text == "new input"

    # Esc< (beginning-of-history)
    result, _cli = _feed_cli_with_input("hello\x1b<\r", history=history)
    assert result.text == "line1 first input"

    # Esc> (end-of-history)
    result, _cli = _feed_cli_with_input(
        "another item\x1b[A\x1b[a\x1b>\r", history=history
    )
    assert result.text == "another item"

    # ControlUp (previous-history)
    result, _cli = _feed_cli_with_input("\x1b[1;5A\r", history=history)
    assert result.text == "another item"

    # Esc< ControlDown (beginning-of-history, next-history)
    result, _cli = _feed_cli_with_input("\x1b<\x1b[1;5B\r", history=history)
    assert result.text == "line2 second input"


def test_emacs_reverse_search() -> None:
    """Test reverse search in history."""
    history = _history()

    # ControlR  (reverse-search-history)
    result, _cli = _feed_cli_with_input("\x12input\r\r", history=history)
    assert result.text == "line3 third input"

    # Hitting ControlR twice.
    result, _cli = _feed_cli_with_input("\x12input\x12\r\r", history=history)
    assert result.text == "line2 second input"


def test_emacs_arguments() -> None:
    """Test various combinations of arguments in Emacs mode."""
    # esc 4
    result, _cli = _feed_cli_with_input("\x1b4x\r")
    assert result.text == "xxxx"

    # esc 4 4
    result, _cli = _feed_cli_with_input("\x1b44x\r")
    assert result.text == "x" * 44

    # esc 4 esc 4
    result, _cli = _feed_cli_with_input("\x1b4\x1b4x\r")
    assert result.text == "x" * 44

    # esc - right (-1 position to the right, equals 1 to the left.)
    result, _cli = _feed_cli_with_input("aaaa\x1b-\x1b[Cbbbb\r")
    assert result.text == "aaabbbba"

    # esc - 3 right
    result, _cli = _feed_cli_with_input("aaaa\x1b-3\x1b[Cbbbb\r")
    assert result.text == "abbbbaaa"

    # esc - - - 3 right
    result, _cli = _feed_cli_with_input("aaaa\x1b---3\x1b[Cbbbb\r")
    assert result.text == "abbbbaaa"


def test_emacs_arguments_for_all_commands() -> None:
    """Test all Emacs commands with Meta-[0-9] arguments.

    Test both positive and negative arguments. No one should crash.
    """
    from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

    for key in ANSI_SEQUENCES:
        # Ignore BracketedPaste. This would hang forever, because it waits for
        # the end sequence.
        if key != "\x1b[200~":
            try:
                # Note: we add an 'X' after the key, because Ctrl-Q (quoted-insert)
                # expects something to follow. We add an additional \r, because
                # Ctrl-R and Ctrl-S (reverse-search) expect that.
                _result, _cli = _feed_cli_with_input("hello\x1b4" + key + "X\r\r")

                _result, _cli = _feed_cli_with_input("hello\x1b-" + key + "X\r\r")
            except KeyboardInterrupt:
                # This exception should only be raised for Ctrl-C
                assert key == "\x03"


def test_emacs_kill_ring() -> None:
    """Test kill ring functionality."""
    operations = (
        # abc ControlA ControlK
        "abc\x01\x0b"
        # def ControlA ControlK
        "def\x01\x0b"
        # ghi ControlA ControlK
        "ghi\x01\x0b"
        # ControlY (yank)
        "\x19"
    )

    result, _cli = _feed_cli_with_input(operations + "\r")
    assert result.text == "ghi"

    result, _cli = _feed_cli_with_input(operations + "\x1by\r")
    assert result.text == "def"

    result, _cli = _feed_cli_with_input(operations + "\x1by\x1by\r")
    assert result.text == "abc"

    result, _cli = _feed_cli_with_input(operations + "\x1by\x1by\x1by\r")
    assert result.text == "ghi"


def test_emacs_selection() -> None:
    """Test text selection and copy/paste."""
    # Copy/paste empty selection should not do anything.
    operations = (
        "hello"
        # Twice left.
        "\x1b[D\x1b[D"
        # Control-Space
        "\x00"
        # ControlW (cut)
        "\x17"
        # ControlY twice. (paste twice)
        "\x19\x19\r"
    )

    result, _cli = _feed_cli_with_input(operations)
    assert result.text == "hello"

    # Copy/paste one character.
    operations = (
        "hello"
        # Twice left.
        "\x1b[D\x1b[D"
        # Control-Space
        "\x00"
        # Right.
        "\x1b[C"
        # ControlW (cut)
        "\x17"
        # ControlA (Home).
        "\x01"
        # ControlY (paste)
        "\x19\r"
    )

    result, _cli = _feed_cli_with_input(operations)
    assert result.text == "lhelo"


def test_emacs_insert_comment() -> None:
    """Test insert-comment (M-#) binding."""
    # Test insert-comment (M-#) binding.
    result, _cli = _feed_cli_with_input("hello\x1b#", check_line_ending=False)
    assert result.text == "#hello"

    result, _cli = _feed_cli_with_input(
        "hello\rworld\x1b#", check_line_ending=False, multiline=True
    )
    assert result.text == "#hello\n#world"


def test_emacs_record_macro() -> None:
    """Test macro recording and execution."""
    operations = (
        "  "
        "\x18("  # Start recording macro. C-X(
        "hello"
        "\x18)"  # Stop recording macro.
        "  "
        "\x18e"  # Execute macro.
        "\x18e"  # Execute macro.
        "\r"
    )

    result, _cli = _feed_cli_with_input(operations)
    assert result.text == "  hello  hellohello"


def test_emacs_nested_macro() -> None:
    """Test calling the macro within a macro."""
    # Calling a macro within a macro should take the previous recording (if one
    # exists), not the one that is in progress.
    operations = (
        "\x18("  # Start recording macro. C-X(
        "hello"
        "\x18e"  # Execute macro.
        "\x18)"  # Stop recording macro.
        "\x18e"  # Execute macro.
        "\r"
    )

    result, _cli = _feed_cli_with_input(operations)
    assert result.text == "hellohello"

    operations = (
        "\x18("  # Start recording macro. C-X(
        "hello"
        "\x18)"  # Stop recording macro.
        "\x18("  # Start recording macro. C-X(
        "\x18e"  # Execute macro.
        "world"
        "\x18)"  # Stop recording macro.
        "\x01\x0b"  # Delete all (c-a c-k).
        "\x18e"  # Execute macro.
        "\r"
    )

    result, _cli = _feed_cli_with_input(operations)
    assert result.text == "helloworld"


def test_prefix_meta() -> None:
    """Test the prefix-meta command."""
    # Test the prefix-meta command.
    b = KeyBindings()
    b.add("j", "j", filter=ViInsertMode())(prefix_meta)

    result, _cli = _feed_cli_with_input(
        "hellojjIX\r", key_bindings=b, editing_mode=EditingMode.VI
    )
    assert result.text == "Xhello"


def test_bracketed_paste() -> None:
    """Test bracketed paste mode."""
    result, _cli = _feed_cli_with_input("\x1b[200~hello world\x1b[201~\r")
    assert result.text == "hello world"

    result, _cli = _feed_cli_with_input("\x1b[200~hello\rworld\x1b[201~\x1b\r")
    assert result.text == "hello\nworld"

    # With \r\n endings.
    result, _cli = _feed_cli_with_input("\x1b[200~hello\r\nworld\x1b[201~\x1b\r")
    assert result.text == "hello\nworld"

    # With \n endings.
    result, _cli = _feed_cli_with_input("\x1b[200~hello\nworld\x1b[201~\x1b\r")
    assert result.text == "hello\nworld"


def test_vi_cursor_movements() -> None:
    """Test cursor movements with Vi key bindings."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    result, cli = feed("\x1b[27u\r")
    assert result.text == ""
    assert cli.editing_mode == EditingMode.VI

    # Esc h a X
    result, cli = feed("hello\x1b[27uhaX\r")
    assert result.text == "hellXo"

    # Esc I X
    result, cli = feed("hello\x1b[27uIX\r")
    assert result.text == "Xhello"

    # Esc I X
    result, cli = feed("hello\x1b[27uIX\r")
    assert result.text == "Xhello"

    # Esc 2hiX
    result, cli = feed("hello\x1b[27u2hiX\r")
    assert result.text == "heXllo"

    # Esc 2h2liX
    result, cli = feed("hello\x1b[27u2h2liX\r")
    assert result.text == "hellXo"

    # Esc \b\b
    result, cli = feed("hello\b\b\r")
    assert result.text == "hel"  # codespell:ignore hel

    # Esc \b\b
    result, cli = feed("hello\b\b\r")
    assert result.text == "hel"  # codespell:ignore hel

    # Esc 2h D
    result, cli = feed("hello\x1b[27u2hD\r")
    assert result.text == "he"

    # Esc 2h rX \r
    result, cli = feed("hello\x1b[27u2hrX\r")
    assert result.text == "heXlo"


def test_vi_operators() -> None:
    """Test Vi operators."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Esc g~0
    result, _cli = feed("hello\x1b[27ug~0\r")
    assert result.text == "HELLo"

    # Esc gU0
    result, _cli = feed("hello\x1b[27ugU0\r")
    assert result.text == "HELLo"

    # Esc d0
    result, _cli = feed("hello\x1b[27ud0\r")
    assert result.text == "o"


def test_vi_text_objects() -> None:
    """Test Vi text objects."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Esc gUgg
    result, _cli = feed("hello\x1b[27ugUgg\r")
    assert result.text == "HELLO"

    # Esc gUU
    result, _cli = feed("hello\x1b[27ugUU\r")
    assert result.text == "HELLO"

    # Esc di(
    result, _cli = feed("before(inside)after\x1b[27u8hdi(\r")
    assert result.text == "before()after"

    # Esc di[
    result, _cli = feed("before[inside]after\x1b[27u8hdi[\r")
    assert result.text == "before[]after"

    # Esc da(
    result, _cli = feed("before(inside)after\x1b[27u8hda(\r")
    assert result.text == "beforeafter"


def test_vi_digraphs() -> None:
    """Test Vi digraph input."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # C-K o/
    result, _cli = feed("hello\x0bo/\r")
    assert result.text == "helloø"

    # C-K /o  (reversed input.)
    result, _cli = feed("hello\x0b/o\r")
    assert result.text == "helloø"

    # C-K e:
    result, _cli = feed("hello\x0be:\r")
    assert result.text == "helloë"

    # C-K xxy (Unknown digraph.)
    result, _cli = feed("hello\x0bxxy\r")
    assert result.text == "helloy"


def test_vi_block_editing() -> None:
    """Test Vi Control-V style block insertion."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    operations = (
        # Six lines of text.
        "-line1\r-line2\r-line3\r-line4\r-line5\r-line6"
        # Go to the second character of the second line.
        "\x1b[27ukkkkkkkj0l"
        # Enter Visual block mode.
        "\x16"
        # Go down two more lines.
        "jj"
        # Go 3 characters to the right.
        "lll"
        # Go to insert mode.
        "insert"  # (Will be replaced.)
        # Insert stars.
        "***"
        # Escape again.
        "\x1b[27u\r"
    )

    # Control-I
    result, _cli = feed(operations.replace("insert", "I"))

    assert result.text == "-line1\n-***line2\n-***line3\n-***line4\n-line5\n-line6"

    # Control-A
    result, _cli = feed(operations.replace("insert", "A"))

    assert result.text == "-line1\n-line***2\n-line***3\n-line***4\n-line5\n-line6"


def test_vi_block_editing_empty_lines() -> None:
    """Test block editing on empty lines."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    operations = (
        # Six empty lines.
        "\r\r\r\r\r"
        # Go to beginning of the document.
        "\x1b[27ugg"
        # Enter Visual block mode.
        "\x16"
        # Go down two more lines.
        "jj"
        # Go 3 characters to the right.
        "lll"
        # Go to insert mode.
        "insert"  # (Will be replaced.)
        # Insert stars.
        "***"
        # Escape again.
        "\x1b[27u\r"
    )

    # Control-I
    result, _cli = feed(operations.replace("insert", "I"))

    assert result.text == "***\n***\n***\n\n\n"

    # Control-A
    result, _cli = feed(operations.replace("insert", "A"))

    assert result.text == "***\n***\n***\n\n\n"


def test_vi_visual_line_copy() -> None:
    """Test Vi visual line mode copy."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    operations = (
        # Three lines of text.
        "-line1\r-line2\r-line3\r-line4\r-line5\r-line6"
        # Go to the second character of the second line.
        "\x1b[27ukkkkkkkj0l"
        # Enter Visual linemode.
        "V"
        # Go down one line.
        "j"
        # Go 3 characters to the right (should not do much).
        "lll"
        # Copy this block.
        "y"
        # Go down one line.
        "j"
        # Insert block twice.
        "2p"
        # Escape again.
        "\x1b[27u\r"
    )

    result, _cli = feed(operations)

    assert (
        result.text
        == "-line1\n-line2\n-line3\n-line4\n-line2\n-line3\n-line2\n-line3\n-line5\n-line6"
    )


def test_vi_visual_empty_line() -> None:
    """Test edge case with an empty line in Visual-line mode."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    # 1. Delete first two lines.
    operations = (
        # Three lines of text. The middle one is empty.
        "hello\r\rworld"
        # Go to the start.
        "\x1b[27ugg"
        # Visual line and move down.
        "Vj"
        # Delete.
        "d\r"
    )
    result, _cli = feed(operations)
    assert result.text == "world"

    # 1. Delete middle line.
    operations = (
        # Three lines of text. The middle one is empty.
        "hello\r\rworld"
        # Go to middle line.
        "\x1b[27uggj"
        # Delete line
        "Vd\r"
    )

    result, _cli = feed(operations)
    assert result.text == "hello\nworld"


def test_vi_character_delete_after_cursor() -> None:
    """Test 'x' keypress."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    # Delete one character.
    result, _cli = feed("abcd\x1b[27uHx\r")
    assert result.text == "bcd"

    # Delete multiple characters.
    result, _cli = feed("abcd\x1b[27uH3x\r")
    assert result.text == "d"

    # Delete on empty line.
    result, _cli = feed("\x1b[27uo\x1b[27uo\x1b[27uggx\r")
    assert result.text == "\n\n"

    # Delete multiple on empty line.
    result, _cli = feed("\x1b[27uo\x1b[27uo\x1b[27ugg10x\r")
    assert result.text == "\n\n"

    # Delete multiple on empty line.
    result, _cli = feed("hello\x1b[27uo\x1b[27uo\x1b[27ugg3x\r")
    assert result.text == "lo\n\n"


def test_vi_character_delete_before_cursor() -> None:
    """Test 'X' keypress."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    # Delete one character.
    result, _cli = feed("abcd\x1b[27uX\r")
    assert result.text == "abd"  # codespell:ignore abd

    # Delete multiple characters.
    result, _cli = feed("hello world\x1b[27u3X\r")
    assert result.text == "hello wd"

    # Delete multiple characters on multiple lines.
    result, _cli = feed("hello\x1b[27uoworld\x1b[27ugg$3X\r")
    assert result.text == "ho\nworld"

    result, _cli = feed("hello\x1b[27uoworld\x1b[27u100X\r")
    assert result.text == "hello\nd"

    # Delete on empty line.
    result, _cli = feed("\x1b[27uo\x1b[27uo\x1b[27u10X\r")
    assert result.text == "\n\n"


def test_vi_character_paste() -> None:
    """Test Vi character paste commands."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Test 'p' character paste.
    result, _cli = feed("abcde\x1b[27uhhxp\r")
    assert result.text == "abdce"
    assert result.cursor_position == 3

    # Test 'P' character paste.
    result, _cli = feed("abcde\x1b[27uhhxP\r")
    assert result.text == "abcde"
    assert result.cursor_position == 2


def test_vi_temp_navigation_mode() -> None:
    """Test c-o binding: go for one action into navigation mode."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    result, _cli = feed("abcde\x0f3hx\r")  # c-o  # 3 times to the left.
    assert result.text == "axbcde"
    assert result.cursor_position == 2

    result, _cli = feed("abcde\x0fbx\r")  # c-o  # One word backwards.
    assert result.text == "xabcde"
    assert result.cursor_position == 1

    # In replace mode
    result, _cli = feed(
        "abcdef"
        "\x1b[27u"  # Navigation mode.
        "0l"  # Start of line, one character to the right.
        "R"  # Replace mode
        "78"
        "\x0f"  # c-o
        "l"  # One character forwards.
        "9\r"
    )
    assert result.text == "a78d9f"
    assert result.cursor_position == 5


def test_vi_macros() -> None:
    """Test Vi macro recording and execution."""
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Record and execute macro.
    result, _cli = feed("\x1b[27uqcahello\x1b[27uq@c\r")
    assert result.text == "hellohello"
    assert result.cursor_position == 9

    # Running unknown macro.
    result, _cli = feed("\x1b[27u@d\r")
    assert result.text == ""
    assert result.cursor_position == 0

    # When a macro is called within a macro.
    # It shouldn't result in eternal recursion.
    result, _cli = feed("\x1b[27uqxahello\x1b[27u@xq@x\r")
    assert result.text == "hellohello"
    assert result.cursor_position == 9

    # Nested macros.
    result, _cli = feed(
        # Define macro 'x'.
        "\x1b[27uqxahello\x1b[27uq"
        # Define macro 'y' which calls 'x'.
        "qya\x1b[27u@xaworld\x1b[27uq"
        # Delete line.
        "2dd"
        # Execute 'y'
        "@y\r"
    )

    assert result.text == "helloworld"


def test_accept_default() -> None:
    """Test `prompt(accept_default=True)`."""
    with create_pipe_input() as inp:
        session = PromptSession(input=inp, output=DummyOutput())
        result = session.prompt(default="hello", accept_default=True)
        assert result == "hello"

        # Test calling prompt() for a second time. (We had an issue where the
        # prompt reset between calls happened at the wrong time, breaking this.)
        result = session.prompt(default="world", accept_default=True)
        assert result == "world"
