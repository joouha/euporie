"""Define the global command toolbar."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion.base import Completer, Completion
from prompt_toolkit.filters import (
    buffer_has_focus,
    has_focus,
)
from prompt_toolkit.layout.containers import ConditionalContainer, Container, Window
from prompt_toolkit.layout.controls import (
    BufferControl,
)
from prompt_toolkit.layout.processors import BeforeInput, HighlightSelectionProcessor
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.validation import Validator

from euporie.core.app.current import get_app
from euporie.core.bars import COMMAND_BAR_BUFFER
from euporie.core.commands import add_cmd, commands, get_cmd
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from prompt_toolkit.completion.base import CompleteEvent
    from prompt_toolkit.document import Document
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

    from euporie.core.commands import Command

log = logging.getLogger(__name__)


class CommandCompleter(Completer):
    """Completer of commands."""

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Complete registered commands."""
        prefix = document.text
        found_so_far: set[Command] = set()
        for alias, command in commands.items():
            if alias.startswith(prefix) and command not in found_so_far:
                yield Completion(
                    command.name,
                    start_position=-len(prefix),
                    display=command.name,
                    display_meta=command.description,
                )
                found_so_far.add(command)


class CommandBar:
    """Command mode toolbar.

    A modal editor like toolbar to allow entry of commands.
    """

    def __init__(self) -> None:
        """Create a new command bar instance."""
        self.buffer = Buffer(
            completer=CommandCompleter(),
            complete_while_typing=True,
            name=COMMAND_BAR_BUFFER,
            multiline=False,
            accept_handler=self._accept,
            validator=Validator.from_callable(
                validate_func=self._validate,
                error_message="Command not recognised",
                move_cursor_to_end=True,
            ),
        )
        self.control = BufferControl(
            buffer=self.buffer,
            lexer=SimpleLexer(style="class:toolbar.text"),
            input_processors=[
                BeforeInput(":", style="class:toolbar.title"),
                HighlightSelectionProcessor(),
            ],
            include_default_input_processors=False,
            key_bindings=load_registered_bindings(
                "euporie.core.bars.command:CommandBar",
                config=get_app().config,
            ),
        )
        self.window = Window(
            self.control,
            height=1,
            style="class:toolbar",
        )

        self.container = ConditionalContainer(
            content=self.window,
            filter=has_focus(self.buffer),
        )

    def _validate(self, text: str) -> bool:
        """Verify that a valid command has been entered."""
        cmd, _, args = text.partition(" ")
        try:
            get_cmd(cmd)
        except KeyError:
            return False
        else:
            return True

    def _accept(self, buffer: Buffer) -> bool:
        """Return value determines if the text is kept."""
        # TODO - lookup and run command with args
        get_app().layout.focus_last()
        text = buffer.text.strip()
        cmd, _, args = text.partition(" ")
        get_cmd(cmd).run(args)
        return False

    def __pt_container__(self) -> Container:
        """Magic method for widget container."""
        return self.container

    register_bindings(
        {
            "euporie.core.app.app:BaseApp": {
                "activate-command-bar": ":",
                "activate-command-bar-alt": "A-:",
                "activate-command-bar-shell": "!",
                "activate-command-bar-shell-alt": "A-!",
            },
            "euporie.core.bars.command:CommandBar": {
                "deactivate-command-bar": "escape",
            },
        }
    )

    @staticmethod
    @add_cmd(name="activate-command-bar-alt", hidden=True)
    @add_cmd(filter=~buffer_has_focus)
    def _activate_command_bar(event: KeyPressEvent) -> None:
        """Enter command mode."""
        event.app.layout.focus(COMMAND_BAR_BUFFER)

    @staticmethod
    @add_cmd(filter=~buffer_has_focus)
    @add_cmd(name="activate-command-bar-shell-alt", hidden=True)
    def _activate_command_bar_shell(event: KeyPressEvent) -> None:
        """Enter command mode."""
        layout = event.app.layout
        layout.focus(COMMAND_BAR_BUFFER)
        if isinstance(control := layout.current_control, BufferControl):
            buffer = control.buffer
            buffer.text = "shell "
            buffer.cursor_position = 6

    @staticmethod
    @add_cmd(hidden=True)
    def _deactivate_command_bar(event: KeyPressEvent) -> None:
        """Exit command mode."""
        layout = event.app.layout
        layout.focus(COMMAND_BAR_BUFFER)
        if isinstance(control := layout.current_control, BufferControl):
            buffer = control.buffer
            buffer.reset()
            event.app.layout.focus_previous()

    @staticmethod
    @add_cmd(aliases=["shell"])
    async def _run_shell_command(event: KeyPressEvent) -> None:
        """Run system command."""
        app = event.app
        if event._arg:
            await app.run_system_command(
                event._arg,
                display_before_text=[("bold", "$ "), ("", f"{event._arg}\n")],
            )
