"""Defines a simple app for launching euporie apps."""

from importlib.metadata import entry_points

from euporie.core.config import Config, add_setting


class CoreApp:
    """Launch a euporie application."""

    config = Config()

    @classmethod
    def launch(cls) -> "None":
        """Launches the app."""
        # Load the launcher's configuration
        cls.config.load(cls)
        app = cls.config.app
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
        choices=[entry.name for entry in entry_points()["euporie.apps"]],
        description="""
            The name of the application to launch.
        """,
    )
