"""Define a simple app for launching euporie apps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from euporie.core import settings as core_settings
from euporie.core.app.base import ConfigurableApp

if TYPE_CHECKING:
    from typing import ClassVar

    from euporie.core.config._setting import Setting


class LaunchApp(ConfigurableApp):
    """Launch a euporie application."""

    settings: ClassVar[list[Setting]] = [
        core_settings.app,
        core_settings.log_file,
        core_settings.log_level,
        core_settings.log_config,
        core_settings.log_level_stdout,
        core_settings.syntax_theme,
    ]

    @classmethod
    def launch(cls) -> None:
        """Launch an app."""
        # Load settings, including cli
        super().launch()
        # Detect selected app
        chosen_app = cls.config.app
        # Pass only the args the launcher did not consume so the child
        # app doesn't misinterpret the launcher's positional "app"
        # argument as its own (e.g. a file path).
        chosen_app(args=cls.config.remaining_args)


if __name__ == "__main__":
    LaunchApp.launch()
