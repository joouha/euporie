"""Define a base class for configurable apps."""

from __future__ import annotations

from abc import ABC
from inspect import isabstract
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from typing import Any

    from euporie.core.config._config import Config
    from euporie.core.config._setting import Setting
    from euporie.core.config._state import State


class ConfigurableApp(ABC):
    """An application with configuration.

    Each non-abstract subclass gets its own Config and AppState instances,
    created during class definition via __init_subclass__.

    Subclasses declare their settings and states as class variables:
        - ``settings``: list of Setting objects for Config
        - ``states``: list of Setting objects for State

    Attributes:
        name: The application name (e.g., "notebook", "console").
        config: The configuration instance for this app class.
        state: The state instance for this app class.
    """

    name: str | None = None
    config: Config
    state: State
    settings: ClassVar[list[Setting]] = []
    states: ClassVar[list[Setting]] = []
    _config_defaults: ClassVar[dict[str, Any]] = {"log_level_stdout": "error"}

    def __init_subclass__(cls) -> None:
        """Create config and state instances for each non-abstract subclass."""
        if not isabstract(cls):
            from euporie.core.config._config import Config
            from euporie.core.config._state import State

            # Load commands from _commands.py modules
            cls.load_commands()

            # Create config instance for this app from declared settings
            cls.config = Config(
                app=cls.name,
                settings=cls.settings,
                _help=cls.__doc__ or "",
                **cls._config_defaults,
            )

            # Create state instance for this app from declared states
            cls.state = State(
                app=cls.name,
                settings=cls.states,
            )

    @classmethod
    def load_commands(cls) -> None:
        """Load command modules for this class.

        This imports all _commands.py modules from the euporie package hierarchy.
        """
        from euporie.core.utils import import_submodules, root_module

        roots = {
            root_module(base.__module__)
            for base in cls.__mro__
            if base.__module__.startswith("euporie.")
        }
        for root in roots:
            import_submodules(root, ("_commands",))

    @classmethod
    def launch(cls, args: list[str] | None = None) -> None:
        """Launch the app.

        Loads configuration and state, then starts the application.

        Args:
            args: Explicit CLI argument list. When ``None``, ``sys.argv``
                is used. Pass an explicit list to avoid re-parsing args
                that were already consumed by a parent app (e.g. the
                launcher).
        """
        cls.config.load(args=args)
        cls.state.load()
