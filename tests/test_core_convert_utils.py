"""Test format conversion utility functions."""

from __future__ import annotations

from euporie.core.convert.utils import (
    call_subproc,
    commands_exist,
    have_modules,
)


def test_commands_exist() -> None:
    """Existing commands are correctly detected."""
    # Test with existing commands
    assert commands_exist("python")()

    # Test with non-existing command
    assert not commands_exist("nonexistent_command")()


def test_have_modules() -> None:
    """Existing python modules are correctly detected."""
    # Test with existing modules
    assert have_modules("os", "subprocess")()

    # Test with non-existing module
    assert not have_modules("nonexistent_module")()


async def test_call_subproc() -> None:
    """Test calling a sub-process."""
    # Call the function and check the output
    assert (await call_subproc("Test", ["cat"], use_tempfile=False)) == b"Test"

    # Call the function using a temporary file and check the output
    assert (
        await call_subproc("Test", ["cat"], use_tempfile=True, suffix=".txt")
    ) == b"Test"
