"""Define a simple app for launching euporie apps."""

from __future__ import annotations

from euporie.core.app.base import ConfigurableApp


class LaunchApp(ConfigurableApp):
    """Launch a euporie application."""

    @classmethod
    def launch(cls) -> None:
        """Launch an app."""
        cls.config.parser.add_help = False
        # Load settings, including cli
        super().launch()
        # Detect selected app
        chosen_app = cls.config.app
        # Run the application's entry-point
        chosen_app()


if __name__ == "__main__":
    LaunchApp.launch()
