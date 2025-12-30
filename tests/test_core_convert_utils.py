"""Test format conversion utility functions."""

from __future__ import annotations

from euporie.apptk.convert.utils import call_subproc


async def test_call_subproc() -> None:
    """Test calling a sub-process."""
    # Call the function and check the output
    assert (await call_subproc("Test", ["cat"], use_tempfile=False)) == b"Test"

    # Call the function using a temporary file and check the output
    assert (
        await call_subproc("Test", ["cat"], use_tempfile=True, suffix=".txt")
    ) == b"Test"
