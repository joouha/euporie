"""Define a base class for configurable apps."""

from __future__ import annotations

from abc import ABC
from inspect import isabstract
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from euporie.core.config import Config


class ConfigurableApp(ABC):
    """An application with configuration."""

    name: str | None = None
    config: Config
    _config_defaults: ClassVar[dict[str, Any]] = {"log_level_stdout": "error"}

    def __init_subclass__(cls) -> None:
        """Create a config instance for each non-abstract subclass."""
        if not isabstract(cls):
            from euporie.core.config import Config

            # Load settings
            cls.load_settings()
            cls.config = Config(
                app=cls.name,
                _help=cls.__doc__ or "",
                **cls._config_defaults,
            )

    @classmethod
    def load_settings(cls) -> None:
        """Load all known settings for this class."""
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
        """Launch the app."""
        cls.config.load()
