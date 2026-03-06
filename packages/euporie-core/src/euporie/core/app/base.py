"""Define a base class for configurable apps."""

from __future__ import annotations

from abc import ABC
from inspect import isabstract
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.config._config import Config
    from euporie.core.config._state import State


class ConfigurableApp(ABC):
    """An application with configuration.

    Each non-abstract subclass gets its own Config and AppState instances,
    created during class definition via __init_subclass__.

    Attributes:
        name: The application name (e.g., "notebook", "console").
        config: The configuration instance for this app class.
        state: The state instance for this app class.
    """

    name: str | None = None
    config: Config
    state: State
    _config_defaults: ClassVar[dict[str, Any]] = {"log_level_stdout": "error"}

    def __init_subclass__(cls) -> None:
        """Create config and state instances for each non-abstract subclass."""
        if not isabstract(cls):
            from euporie.core.config._config import Config
            from euporie.core.config._migrate import migrate_json_to_toml
            from euporie.core.config._state import State

            # Load settings from _settings.py modules
            cls.load_settings()

            # Create config instance for this app
            cls.config = Config(
                app=cls.name,
                _help=cls.__doc__ or "",
                **cls._config_defaults,
            )

            # Create state instance for this app
            cls.state = State(app=cls.name)

            # Migrate old JSON config, partitioning between config and state
            json_path = cls.config._config_path.with_name("config.json")
            migrate_json_to_toml(
                json_path=json_path,
                config_path=cls.config._config_path,
                state_path=cls.state._state_path,
                config_keys=set(Config._registry),
                state_keys=set(State._registry),
            )

    @classmethod
    def load_settings(cls) -> None:
        """Load all known settings for this class.

        This imports all _settings.py and _commands.py modules from the
        euporie package hierarchy.
        """
        from euporie.core.utils import import_submodules, root_module

        roots = {
            root_module(base.__module__)
            for base in cls.__mro__
            if base.__module__.startswith("euporie.")
        }
        for root in roots:
            import_submodules(root, ("_settings", "_commands"))

    @classmethod
    def launch(cls) -> None:
        """Launch the app.

        Loads configuration and state, then starts the application.
        """
        cls.config.load()
        cls.state.load()
