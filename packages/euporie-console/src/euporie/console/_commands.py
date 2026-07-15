"""Contains commands for the console."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apptk.commands import add_cmd
from apptk.filters.app import (
    buffer_has_focus,
    has_selection,
)
from apptk.filters.buffer import buffer_is_code, buffer_is_empty

if TYPE_CHECKING:
    from apptk.key_binding.key_processor import KeyPressEvent


@add_cmd()
def _convert_to_notebook() -> None:
    """Convert the current console session to a notebook."""
    from euporie.console.app import get_app
    from euporie.console.panes import Console
    from euporie.core.kernel.base import NoKernel
    from euporie.notebook.app import NotebookApp
    from euporie.notebook.panes.notebook import Notebook

    app = get_app()

    NotebookApp.config.load(args=[])
    NotebookApp.state.load()
    nb_app = NotebookApp()

    for tab in app.panes:
        if isinstance(tab, Console):
            # Capture live state before detaching the kernel from the console
            kernel = tab.kernel
            comms = tab.comms
            history = tab.history
            current_input = tab.input_box.buffer.text

            # Flush any pending live output into the console's json so it is
            # preserved when transferred to the notebook
            tab.flush_live_output()

            # Stop the console driving the transferred kernel
            tab.app.before_render -= tab.render_outputs

            # Detach the kernel from the console so it isn't shut down on exit
            tab.kernel = NoKernel(tab)

            nb = Notebook(
                app=nb_app,
                path=tab.path,
                kernel=kernel,
                comms=comms,
                json=tab.json,
            )
            # The notebook was created with a path, so kernel init was deferred.
            # Mark it loaded and explicitly re-initialise the notebook's kernel
            # with the captured kernel and comms. This guarantees nb.kernel is the
            # real transferred kernel (not NoKernel) before kernel_started() is
            # called, avoiding the wait_for_status("idle") hang.
            nb.loaded = True
            nb._really_init_kernel = None
            nb.init_kernel(kernel=kernel, comms=comms)

            # Transfer the console's history
            nb.history = history
            # Add the current input as a new cell
            nb.add(len(nb.json["cells"]) + 1, source=current_input)
            # Add the notebook to the notebook app
            nb_app.add_tab(nb)
            # Tell the notebook the kernel has already started
            nb.kernel_started()

    # Schedule the notebook app to run after the console app exits, then exit
    app._handoff_app = nb_app
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
    keys=["c-c", "<sigint>"],
)
def _clear_input() -> None:
    """Clear the console input."""
    from euporie.console.app import get_app

    buffer = get_app().current_buffer
    buffer.reset()


@add_cmd(
    filter=buffer_is_code & buffer_has_focus,
    keys=["c-enter", "c-e"],
)
def _run_input() -> None:
    """Run the console input."""
    from euporie.console.app import get_app
    from euporie.console.panes import Console

    if isinstance(console := get_app().pane, Console):
        console.run()


@add_cmd(
    filter=buffer_is_code & buffer_is_empty,
    hidden=True,
    description="Signals the end of the input, causing the console to exit.",
    keys=["c-d"],
)
def _end_of_file(event: KeyPressEvent) -> None:
    """Exit when Control-D has been pressed."""
    event.app.exit(exception=EOFError)


@add_cmd(keys=["c-l"])
def _clear_screen() -> None:
    """Clear the screen and the previous output."""
    from euporie.console.app import get_app
    from euporie.console.panes import Console

    app = get_app()
    app.renderer.clear()

    if isinstance(console := app.pane, Console):
        console.reset()
        app.layout.focus(console.input_box)
