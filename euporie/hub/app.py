"""Run euporie as a multi-client SSH server."""

from __future__ import annotations

import asyncio
import logging
from asyncio import get_event_loop
from typing import TYPE_CHECKING

try:
    import asyncssh
except ModuleNotFoundError as err:
    raise ModuleNotFoundError(
        "Euporie hub requires the the `asyncssh` python package\n"
        'Install euporie hub with: "pip install euporie[hub]"'
    ) from err

from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession
from upath import UPath

from euporie.core.__main__ import available_apps
from euporie.core.app import APP_ALIASES
from euporie.core.app.base import ConfigurableApp
from euporie.core.config import add_setting

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from typing import Any, ClassVar

    from euporie.core.app.app import BaseApp

log = logging.getLogger(__name__)


def _euporie_hub_app_choices() -> list[str]:
    """List known euporie-apps and their aliases."""
    from euporie.core.__main__ import available_apps
    from euporie.core.app import APP_ALIASES

    return sorted(
        {entry.name for entry in available_apps().values()} - {"launch", "hub"}
        | APP_ALIASES.keys()
    )


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

    # ################################### Settings ####################################

    add_setting(
        name="hub_app",
        group="euporie.hub.app",
        flags=["hub_app"],
        type_=str,
        help_="The application to launch",
        choices=_euporie_hub_app_choices,
        description="""
            The name of the application to launch.
        """,
    )

    add_setting(
        name="host",
        group="euporie.hub.app",
        flags=["--host"],
        type_=str,
        help_="The host address to bind to",
        default="",
        description="""
            This determines the host address the euporie hub SSH server will bind to.
        """,
    )

    add_setting(
        name="port",
        group="euporie.hub.app",
        flags=["--port"],
        type_=int,
        help_="The port for the ssh server to use",
        default=8022,
        schema_={
            "minimum": 1,
            "maximum": 65535,
        },
        description="""
            This determines which port euporie will listen on for connections to
            euporie hub.
        """,
    )

    add_setting(
        name="host_keys",
        group="euporie.hub.app",
        flags=["--host-keys"],
        nargs="*",
        type_=UPath,
        help_="Host keys to use for the SSH server",
        default=["/etc/ssh/ssh_host_ecdsa_key"],
        schema={
            "type": "array",
            "items": {
                "description": "SSH host key file path",
                "type": "string",
            },
        },
        description="""
            One or more SSH host key files to use for the euporie hub SSH server.
        """,
    )

    add_setting(
        name="client_keys",
        group="euporie.hub.app",
        flags=["--client-keys"],
        nargs="*",
        type_=UPath,
        help_="Client public keys authorized to connect",
        default=["~/.ssh/authorized_keys"],
        schema={
            "type": "array",
            "items": {
                "description": "Path to file containing authorized public keys",
                "type": "string",
            },
        },
        description="""
            One or more OpenSSH-style :file:`authorized_keys` files, containing
            public keys for authorized clients.
        """,
    )

    add_setting(
        name="auth",
        group="euporie.hub.app",
        flags=["--auth"],
        type_=bool,
        help_="Allow unauthenticated access to euporie hub",
        default=True,
        description="""
            When set, users will be able to access euporie hub without authentication.

            .. warning::

               This option is dangerous, as arbitrary code can be executed through
               euporie apps.
        """,
    )
