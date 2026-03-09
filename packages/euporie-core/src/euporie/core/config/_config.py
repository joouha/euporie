"""Config subclass — user-editable configuration."""

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from euporie.core import __app_name__, __copyright__
from euporie.core.config._layers import (
    CliLayer,
    EnvironmentLayer,
    JsonFileLayer,
    TomlFileLayer,
)
from euporie.core.config._store import SettingStore
from platformdirs import user_config_dir

if TYPE_CHECKING:
    from euporie.core.config._layers import Layer
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
        self._json_config_path = config_dir / "config.json"

        # Add read-only JSON layers for legacy config if JSON exists
        # but TOML has not yet been created
        layers: list[Layer] = [
            JsonFileLayer(self._json_config_path),
            JsonFileLayer(self._json_config_path, namespace=app),
            TomlFileLayer(self._config_path),
            TomlFileLayer(self._config_path, namespace=app, persistable=True),
            EnvironmentLayer(__app_name__),
            EnvironmentLayer(__app_name__, namespace=app),
            CliLayer(
                validate=partial(self._validate, source="Command line"),
                description=_help,
                epilog=__copyright__,
                syntax_theme=partial(getattr, self, "syntax_theme"),
            ),
        ]

        super().__init__(
            app=app,
            settings=settings or [],
            layers=layers,
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

        if self._json_config_path.exists():
            log.warning(
                "Legacy JSON configuration file found at '%s'. "
                "Please migrate your settings to '%s' and remove the JSON file.",
                self._json_config_path,
                self._config_path,
            )
