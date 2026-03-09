"""Config subclass — user-editable configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from euporie.core import __app_name__, __copyright__
from euporie.core.config._layers import CliLayer, EnvironmentLayer, TomlFileLayer
from euporie.core.config._parser import ArgumentParser, MetavarTypeHelpFormatter
from euporie.core.config._store import SettingStore
from platformdirs import user_config_dir

if TYPE_CHECKING:
    from euporie.core.config._setting import Setting as Setting

log = logging.getLogger(__name__)


class Config(SettingStore):
    """User-editable configuration stored in user_config_dir.

    Resolution order (lowest to highest priority):
        1. Defaults
        2. Global config file (top-level values in config.toml)
        3. App config file section ([notebook] in config.toml)
        4. Global environment variables (EUPORIE_*)
        5. App environment variables (EUPORIE_NOTEBOOK_*)
        6. CLI arguments
        7. Programmatic overrides

    Attributes:
        parser: The argument parser for CLI arguments.
    """

    def __init__(
        self,
        app: str | None = None,
        *,
        settings: list[Setting] | None = None,
        _help: str = "",
        **kwargs: Any,
    ) -> None:
        """Create a new Config instance.

        Args:
            app: The application name.
            settings: The list of settings this config manages.
            _help: Help text for the argument parser.
            **kwargs: Initial override values.
        """
        app = app or kwargs.pop("app", None) or "euporie"
        self._help = _help

        config_dir = Path(user_config_dir(__app_name__, appauthor=None))
        config_dir.mkdir(exist_ok=True, parents=True)
        self._config_path = config_dir / "config.toml"

        # Build argument parser
        self.parser = ArgumentParser(
            description=_help,
            epilog=__copyright__,
            allow_abbrev=True,
            formatter_class=MetavarTypeHelpFormatter,
            syntax_theme=kwargs.get("syntax_theme", "euporie"),
            argument_default=None,
        )

        super().__init__(
            app=app,
            settings=settings or [],
            layers=[
                TomlFileLayer(self._config_path),
                TomlFileLayer(self._config_path, namespace=app, persistable=True),
                EnvironmentLayer(__app_name__),
                EnvironmentLayer(__app_name__, namespace=app),
                CliLayer(self.parser),
            ],
            overrides=kwargs,
        )

    def load(self) -> None:
        """Load configuration."""
        from euporie.core.log import BufferedLogs, setup_logs

        with BufferedLogs(logger=logging.getLogger("euporie")):
            try:
                super().load()
            finally:
                setup_logs(self)
