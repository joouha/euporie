"""Define a simple app for launching euporie apps."""

from __future__ import annotations

from euporie.core.app import APP_ALIASES
from euporie.core.app.base import ConfigurableApp


class LaunchApp(ConfigurableApp):
    """Launch a euporie application."""

    @classmethod
    def launch(cls) -> None:
        """Launch an app."""
        super().launch()

        # Detect selected app
        chosen_app = cls.config.app
        chosen_app = APP_ALIASES.get(chosen_app, chosen_app)

        # Run the application
        from euporie.core.__main__ import main

        main(chosen_app)


if __name__ == "__main__":
    LaunchApp.launch()
