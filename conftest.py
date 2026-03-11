"""Root conftest for euporie test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --e2e command line option."""
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Include end-to-end tests in the test run",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Remove the 'not e2e' deselection when --e2e is passed."""
    if config.getoption("--e2e"):
        # Clear the marker expression so e2e tests are included
        config.option.markexpr = ""
