"""State subclass — app-managed persistent state."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from euporie.core import __app_name__
from euporie.core.config._layers import TomlFileLayer
from euporie.core.config._store import SettingStore
from platformdirs import user_data_dir

if TYPE_CHECKING:
    from euporie.core.config._setting import Setting

log = logging.getLogger(__name__)


class State(SettingStore):
    """App-managed persistent state stored in user_data_dir.

    State is stored per-application in a state.toml file.
    Unlike configuration, state is not user-edited and represents
    transient UI state like recently opened files, sidebar width, etc.

    Resolution order (lowest to highest priority):
        1. Defaults
        2. App state file section ([app] in state.toml)
        3. Programmatic overrides
    """

    def __init__(
        self,
        app: str,
        *,
        settings: list[Setting] | None = None,
    ) -> None:
        """Create a new State instance.

        Args:
            app: The application name.
            settings: The list of settings this state manages.
        """
        state_dir = Path(user_data_dir(__app_name__, appauthor=None))
        state_dir.mkdir(exist_ok=True, parents=True)
        self._state_path = state_dir / "state.toml"

        super().__init__(
            app=app,
            settings=settings or [],
            layers=[TomlFileLayer(self._state_path, namespace=app, persistable=True)],
        )
