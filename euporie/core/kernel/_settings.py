"""Defines kernel settings."""

from euporie.core.config import add_setting

add_setting(
    name="warn_venv",
    # Kernel implementations are loaded lazily, so we add kernel settings to the root
    # kernel module group, causing them to get loaded before any kernel implementations
    group="euporie.core.kernel",
    flags=["--warn-venv"],
    type_=bool,
    default=True,
    help_="Warn when running in a virtual environment",
    description="""
    When enabled, displays a warning message when the kernel is running inside a
    virtual environment.

    This can be helpful to remind users that they are working in an isolated Python
    environment with potentially different package versions than their system Python
    installation.

    Disable this setting if you prefer not to see these warnings.
    """,
)
