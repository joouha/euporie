"""Contains commands for the console."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.filters.app import (
    buffer_has_focus,
    has_selection,
)

from euporie.core.commands import add_cmd
from euporie.core.filters import (
    buffer_is_code,
    buffer_is_empty,
    kernel_tab_has_focus,
)
from euporie.core.tabs.kernel import KernelTab

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent


@add_cmd()
async def _convert_to_notebook() -> None:
    """Convert the current console session to a notebook."""
    from prompt_toolkit.application.run_in_terminal import in_terminal

    from euporie.console.app import get_app
    from euporie.console.tabs.console import Console
    from euporie.notebook.app import NotebookApp

    app = get_app()
    NotebookApp.config = app.config
    NotebookApp.load_settings()
    NotebookApp.config.__init__(app="notebook")  # type: ignore [misc]
    nb_app = NotebookApp()
    # Use same event loop
    nb_app.loop = app.loop
    for tab in app.tabs:
        if isinstance(tab, Console):
            from euporie.notebook.tabs.notebook import Notebook

            nb = Notebook(
                app=nb_app,
                path=tab.path,
                kernel=tab.kernel,
                comms=tab.comms,
                json=tab.json,
            )
            # Set the history to the console's history
            nb.history = tab.history
            # Add the current input
            nb.add(len(nb.json["cells"]) + 1, source=tab.input_box.buffer.text)
            # Add the new notebook to the notebook app
            nb_app.tabs.append(nb)
            # Tell notebook that the kernel has already started
            nb.kernel_started()

    async with in_terminal():
        await nb_app.run_async()

    app.exit()


@add_cmd()
def _accept_input() -> None:
    """Accept the current console input."""
    from euporie.console.app import get_app

    buffer = get_app().current_buffer
    if buffer:
        buffer.validate_and_handle()


@add_cmd(
    filter=buffer_is_code & buffer_has_focus & ~has_selection & ~buffer_is_empty,
)
def _clear_input() -> None:
    """Clear the console input."""
    from euporie.console.app import get_app

    buffer = get_app().current_buffer
    buffer.reset()


@add_cmd(
    filter=buffer_is_code & buffer_has_focus,
)
def _run_input() -> None:
    """Run the console input."""
    from euporie.console.app import get_app
    from euporie.console.tabs.console import Console

    if isinstance(console := get_app().tab, Console):
        console.run()


@add_cmd(
    name="cc-interrupt-kernel",
    hidden=True,
    filter=buffer_is_code & buffer_is_empty,
)
@add_cmd(filter=kernel_tab_has_focus)
def _interrupt_kernel() -> None:
    """Interrupt the notebook's kernel."""
    from euporie.console.app import get_app

    if isinstance(kt := get_app().tab, KernelTab):
        kt.interrupt_kernel()


@add_cmd(filter=kernel_tab_has_focus)
def _restart_kernel() -> None:
    """Restart the notebook's kernel."""
    from euporie.console.app import get_app

    if isinstance(kt := get_app().tab, KernelTab):
        kt.restart_kernel()


@add_cmd(
    filter=buffer_is_code & buffer_is_empty,
    hidden=True,
    description="Signals the end of the input, causing the console to exit.",
)
def _end_of_file(event: KeyPressEvent) -> None:
    """Exit when Control-D has been pressed."""
    event.app.exit(exception=EOFError)


@add_cmd()
def _clear_screen() -> None:
    """Clear the screen and the previous output."""
    from euporie.console.app import get_app
    from euporie.console.tabs.console import Console

    app = get_app()
    app.renderer.clear()

    if isinstance(console := app.tab, Console):
        console.reset()
        app.layout.focus(console.input_box)
