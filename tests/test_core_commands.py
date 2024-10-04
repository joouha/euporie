"""Tests for `Command`s."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest
from prompt_toolkit.application.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.key_binding.key_bindings import Binding
from prompt_toolkit.key_binding.key_processor import KeyPressEvent, KeyProcessor

from euporie.core.commands import Command, add_cmd, commands, get_cmd
from euporie.core.keys import Keys

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone

    from euporie.core.commands import CommandHandler


@pytest.fixture
def mock_handler() -> CommandHandler:
    """Command handler fixture."""
    return Mock(return_value=None)


@pytest.fixture
def command(mock_handler: CommandHandler) -> Command:
    """Command fixture."""
    return Command(
        mock_handler,
        name="test-command",
        title="Test Command",
        menu_title="Test Command Menu Title",
        description="This is a test command.",
    )


def test_command_init(command: Command, mock_handler: CommandHandler) -> None:
    """Commands are initalialized as expected."""
    assert command.handler == mock_handler
    assert command.filter() is True
    assert command.hidden() is False
    assert command.name == "test-command"
    assert command.title == "Test Command"
    assert command.menu_title == "Test Command Menu Title"
    assert command.description == "This is a test command."
    assert command.toggled is None
    assert command.eager() is False
    assert command.is_global() is False
    assert command.record_in_macro() is True
    assert command.keys == []


def test_command_run(command: Command, mock_handler: CommandHandler) -> None:
    """Running a command runs the handler."""
    command.run()
    cast("Mock", mock_handler).assert_called_once()


def test_command_key_handler() -> None:
    """Command handlers are translated into key-binding handlers."""
    check = {"handled": False}

    def check_cmd_handler(
        handler: CommandHandler,
        check: dict[str, bool],
        invalidate_count: int,
        is_async: bool,
    ) -> None:
        check["handled"] = False
        cmd = Command(handler)
        app = Mock(spec=Application)
        app.key_processor = KeyProcessor(Mock())
        # Run the command
        with set_app(app):
            cmd.run()

        if is_async:
            app.create_background_task.assert_called_once()
            coro = app.create_background_task.call_args_list[0].args[0]
            asyncio.run(coro)

        assert check["handled"]
        assert app.invalidate.call_count == invalidate_count

    def check_cmd_key_handler(
        handler: CommandHandler,
        check: dict[str, bool],
        invalidate_count: int,
        is_async: bool,
    ) -> None:
        check["handled"] = False
        cmd = Command(handler)
        app = Mock(spec=Application)
        # Create a key-press event
        with set_app(app):
            event = KeyPressEvent(
                key_processor_ref=Mock(),
                arg=None,
                key_sequence=[],
                previous_key_sequence=[],
                is_repeat=False,
            )
        # Create a key-bindings from the command handler
        binding = Binding(
            keys=(),
            handler=cmd.key_handler,
        )
        # Call the key-binding
        binding.call(event)

        if is_async:
            app.create_background_task.assert_called_once()
            coro = app.create_background_task.call_args_list[0].args[0]
            asyncio.run(coro)

        assert check["handled"]
        assert app.invalidate.call_count == invalidate_count

    # Test the key handler when the command handler accepts arguments
    # and returns `None`

    def handler_with_args_none(event: KeyPressEvent) -> NotImplementedOrNone:
        nonlocal check
        check["handled"] = True
        return None

    check_cmd_handler(handler_with_args_none, check, 1, False)
    check_cmd_key_handler(handler_with_args_none, check, 1, False)

    # Test the key handler when the command handler accepts arguments
    # and returns `NotImplemented`

    def handler_with_args_notimplemented(event: KeyPressEvent) -> NotImplementedOrNone:
        nonlocal check
        check["handled"] = True
        return NotImplemented

    check_cmd_key_handler(handler_with_args_notimplemented, check, 0, False)

    # Test the key handler when the command handler doesn't accept arguments
    # and returns `None`

    def handler_without_args_none(event: KeyPressEvent) -> NotImplementedOrNone:
        nonlocal check
        check["handled"] = True
        return None

    check_cmd_handler(handler_without_args_none, check, 1, False)
    check_cmd_key_handler(handler_without_args_none, check, 1, False)

    # Test the key handler when the command handler doesn't accept arguments
    # and returns `NotImplemented`

    def handler_without_args_notimplemented(
        event: KeyPressEvent,
    ) -> NotImplementedOrNone:
        nonlocal check
        check["handled"] = True
        return NotImplemented

    check_cmd_handler(handler_without_args_notimplemented, check, 0, False)
    check_cmd_key_handler(handler_without_args_notimplemented, check, 0, False)

    # Test the key handler when the command handler is async and does not accepts
    # arguments and returns `None`

    async def async_handler_without_args_none() -> NotImplementedOrNone:
        nonlocal check
        check["handled"] = True
        return None

    check_cmd_handler(async_handler_without_args_none, check, 1, True)
    check_cmd_key_handler(async_handler_without_args_none, check, 1, True)

    # Test the key handler when the command handler is async and does not accepts
    # arguments and returns `NotImplemented`

    async def async_handler_without_args_notimplemented() -> NotImplementedOrNone:
        nonlocal check
        check["handled"] = True
        return NotImplemented

    check_cmd_handler(async_handler_without_args_notimplemented, check, 0, True)
    check_cmd_key_handler(async_handler_without_args_notimplemented, check, 0, True)


def test_command_bind(command: Command) -> None:
    """Adding binding keys adds a key and key-binding."""
    key_bindings = Mock()
    command.bind(key_bindings, "a")
    assert command.keys == [("a",)]
    key_bindings.bindings.append.assert_called_once()


def test_key_str(command: Command) -> None:
    """Key strings are formatted as expected."""
    kb = Mock()

    command.keys = []
    command.bind(kb, Keys.ControlA)
    assert command.key_str() == "Ctrl+A"

    command.keys = []
    command.bind(kb, "c-a")
    assert command.key_str() == "Ctrl+A"

    command.keys = []
    command.bind(kb, ("escape", "a"))
    assert command.key_str() == "Alt+A"

    command.keys = []
    command.bind(kb, ("a", "b"))
    assert command.key_str() == "A, B"

    command.keys = []
    command.bind(kb, [("a", "b"), ("c-a", "c-b")])
    assert command.key_str() == "A, B"


def test_command_menu_handler(command: Command, mock_handler: CommandHandler) -> None:
    """Commands menu handlers run the command's handler."""
    # Run the menu handler
    handler = command.menu_handler
    result = handler()
    # Assert that the command handler gets run
    cast("Mock", mock_handler).assert_called_once()
    # Assert that the command handler returns `None`
    assert result is None


def test_command_menu(command: Command) -> None:
    """Command's menu items are created as expected."""
    command.bind(Mock(), [("a", "b")])
    menu = command.menu

    assert menu._formatted_text == "Test Command Menu Title"
    assert menu.description == "This is a test command."
    assert to_formatted_text(menu.shortcut) == [("", "A, B")]


def test_add_cmd() -> None:
    """Commands are added to the commands dictionary with the correct parameters."""

    # Test adding a command with required parameters only
    @add_cmd(name="my_cmd")
    def my_cmd() -> None:
        pass

    assert isinstance(commands["my_cmd"], Command)
    assert commands["my_cmd"].name == "my_cmd"

    # Test adding a command with optional parameters
    @add_cmd(name="my_cmd_2", description="This is my second command")
    def my_cmd_2() -> None:
        pass

    assert isinstance(commands["my_cmd_2"], Command)
    assert commands["my_cmd_2"].name == "my_cmd_2"
    assert commands["my_cmd_2"].description == "This is my second command"


def test_get_cmd() -> None:
    """Command are retrieved."""

    # Test getting a command that exists in the commands dictionary
    @add_cmd(name="my_cmd")
    def my_cmd() -> None:
        pass

    cmd = get_cmd("my_cmd")
    assert isinstance(cmd, Command)
    assert cmd.name == "my_cmd"

    # Test getting a command that doesn't exist in the commands dictionary
    with pytest.raises(KeyError):
        get_cmd("nonexistent_cmd")
