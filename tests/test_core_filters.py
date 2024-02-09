"""Test filter functions functions."""

from __future__ import annotations

from euporie.core.filters import command_exists, have_modules


def test_command_exists() -> None:
    """Existing commands are correctly detected."""
    # Test with existing commands
    assert command_exists("python")()

    # Test with non-existing command
    assert not command_exists("nonexistent_command")()


def test_have_modules() -> None:
    """Existing python modules are correctly detected."""
    # Test with existing modules
    assert have_modules("os", "subprocess")()

    # Test with non-existing module
    assert not have_modules("nonexistent_module")()
