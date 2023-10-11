"""Test format conversion utility functions."""

from __future__ import annotations

from unittest.mock import patch

from euporie.core.convert.utils import (
    call_subproc,
    commands_exist,
    data_pixel_size,
    have_modules,
    pixels_to_cell_size,
)
from euporie.core.terminal import TerminalInfo


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


def test_data_pixel_size() -> None:
    """Check data pixel sizes are correctly determined."""
    # Assert that px and py are None since format is "ansi"
    px, py = data_pixel_size(data="Test data", format_="ansi")
    assert px is None
    assert py is None

    # Check SVG size is correctly determined
    px, py = data_pixel_size(data='<svg width="10" height="20"></svg>', format_="svg")
    assert px == 10
    assert py == 20


def test_pixels_to_cell_size() -> None:
    """Ensure pixel to cell size conversion works correctly."""
    px = 256
    py = 128

    with patch.object(TerminalInfo, "cell_size_px", (8, 16)):
        cols, aspect = pixels_to_cell_size(px, py)

    # Assert the calculated cols and aspect values
    assert cols == 32
    assert aspect == 0.25
