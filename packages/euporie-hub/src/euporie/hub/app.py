"""Run euporie as a multi-client SSH server."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, ClassVar

try:
    import asyncssh
except ModuleNotFoundError as err:
    raise ModuleNotFoundError(
        "Euporie hub requires the the `asyncssh` python package\n"
        'Install euporie hub with: "pip install euporie[hub]"'
    ) from err

from apptk.contrib.ssh import PromptToolkitSSHSession

from euporie.core.app import APP_ALIASES
from euporie.core.app.base import ConfigurableApp
from euporie.hub import settings as hub_settings

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from typing import Any

    from euporie.core.app.app import BaseApp
    from euporie.core.config._setting import Setting

log = logging.getLogger(__name__)


class EuporieSSHServer(asyncssh.SSHServer):  # type: ignore
    """Launch euporie hub, which serves a euporie app over SSH.

    Launch euporie hub, a multi-client SSH server running euporie, which
    allows multiple users to connect and run instances of a euporie app.

    """

    def __init__(self, app_cls: type[BaseApp]) -> None:
        """Set the interaction function for the SSH session."""
        self.app_cls = app_cls

    def begin_auth(self, username: str) -> bool | Awaitable[bool]:
        """Perform authentication in the SSH server."""
        if not self.app_cls.config.auth:
            # No authentication.
            return False
        return super().begin_auth(username)

    def session_requested(self) -> PromptToolkitSSHSession:
        """Return an SSH session."""
        # Not sure why mypy gives an error here
        return PromptToolkitSSHSession(self.app_cls.interact, enable_cpr=True)  # type: ignore [call-arg]


class HubApp(ConfigurableApp):
    """Hub App.

    An app which runs as a multi-user SSH server.

    This app never actually gets run, but is used to run another app in an SSH server.
    """

    name = "hub"

    states: ClassVar[list[Setting]] = []

    settings: ClassVar[list[Setting]] = [
        hub_settings.hub_app,
        hub_settings.host,
        hub_settings.port,
        hub_settings.host_keys,
        hub_settings.client_keys,
        hub_settings.auth,
    ]

    _config_defaults: ClassVar[dict[str, Any]] = {
        "log_level_stdout": "info",
        "log_config": {
            "handlers": {"stdout": {"share_stream": False}},
            "loggers": {"asyncssh": {"handlers": ["stdout"], "level": "DEBUG"}},
        },
    }

    @classmethod
    def launch(cls) -> None:
        """Launch the HubApp SSH server."""
        # Configure some setting defaults
        super().launch()

        if not cls.config.auth:
            log.warning(
                "This server has been configured without SSH authentication, "
                "meaning anyone can connect"
            )

        # Detect selected app
        chosen_app = cls.config.hub_app
        chosen_app = APP_ALIASES.get(chosen_app, chosen_app)

        # Import the hubbed app
        from euporie.core.__main__ import available_apps

        apps = available_apps()
        if entry := apps.get(chosen_app):
            app_cls = entry.load()
        else:
            raise ModuleNotFoundError("Application `%s` not found", cls.config.app)

        # Run the HubApp in an SSH server
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            asyncssh.create_server(
                lambda: EuporieSSHServer(app_cls=app_cls),
                host=cls.config.host,
                port=cls.config.port,
                server_host_keys=cls.config.host_keys,
                authorized_client_keys=cls.config.client_keys,
            )
        )
        log.info("Running euporie hub on port %s", cls.config.port)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            log.info("Exiting euporie hub")
