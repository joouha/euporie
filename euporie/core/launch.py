"""Defines a simple app for launching euporie apps."""

from __future__ import annotations

from importlib.metadata import entry_points

from euporie.core.config import Config, add_setting

APP_ALIASES = {
    "edit": "notebook",
}


class CoreApp:
    """Launch a euporie application."""

    config = Config()

    @classmethod
    def launch(cls) -> "None":
        """Launches the app."""
        # Load the launcher's configuration
        cls.config.load(cls)
        app = cls.config.app

        # Add aliases
        app = APP_ALIASES.get(app, app)

        # Run the application
        from euporie.core.__main__ import main

        main(app)

    # ################################## Settings #####################################

    add_setting(
        name="app",
        flags=["app"],
        default="notebook",
        type_=str,
        required=False,
        help_="The application to launch",
        choices=sorted(
            {entry.name for entry in entry_points()["euporie.apps"]} - {"launch"}
            | APP_ALIASES.keys()
        ),
        description="""
            The name of the application to launch.
        """,
    )
