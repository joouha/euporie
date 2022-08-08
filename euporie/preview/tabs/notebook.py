"""A notebook which renders cells one cell at a time."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    VSplit,
    Window,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Box

from euporie.core.config import add_setting
from euporie.core.tabs.notebook import BaseNotebook
from euporie.core.widgets.cell import Cell
from euporie.core.widgets.page import PrintingContainer

if TYPE_CHECKING:
    from typing import Any, Callable

    from prompt_toolkit.application.application import Application
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.layout.containers import AnyContainer
    from upath import UPath

    from euporie.core.app import BaseApp

log = logging.getLogger(__name__)


class PreviewNotebook(BaseNotebook):
    """A notebook tab which renders cells sequentially."""

    def __init__(
        self,
        app: "BaseApp",
        path: "Optional[UPath]" = None,
        use_kernel_history: "bool" = False,
    ) -> "None":
        """Create a new instance."""
        super().__init__(app, path, use_kernel_history=use_kernel_history)
        self.cell_index = 0
        self.app.before_render += self.before_render
        self.app.after_render += self.after_render
        self.cells: "FastDictCache[tuple[int], Cell]" = FastDictCache(
            get_value=self.get_cell
        )

        # If we are running the notebook, pause rendering util the kernel has started
        if self.app.config.run:
            self.app.pause_rendering()
            self.kernel.start(self.kernel_started, wait=True)

        # Filter the cells to be shown
        n_cells = len(self.json["cells"]) - 1
        start: "Optional[int]" = None
        stop: "Optional[int]" = None
        if self.app.config.cell_start is not None:
            start = min(max(self.app.config.cell_start, -n_cells), n_cells)
        if self.app.config.cell_stop is not None:
            stop = min(max(self.app.config.cell_stop, -n_cells), n_cells)
        log.debug("Showing cells %s to %s", start, stop)
        self.json["cells"] = self.json["cells"][start:stop]

    def print_title(self) -> "None":
        """Print a notebook's filename."""
        from euporie.core.formatted_text.utils import (
            FormattedTextAlign,
            add_border,
            align,
            wrap,
        )

        width = self.app.output.get_size().columns
        ft: "StyleAndTextTuples" = [("bold", str(self.path))]
        ft = wrap(ft, width - 4)
        ft = align(FormattedTextAlign.CENTER, ft, width=width - 4)
        ft = add_border(ft, width=width)
        self.app.print_text(ft)

    def kernel_started(self, result: "Optional[dict]" = None) -> "None":
        """Resumes rendering the app when the kernel has started."""
        self.app.resume_rendering()

    def close(self, cb: "Optional[Callable]" = None) -> "None":
        """Clean up render hooks before the tab is closed."""
        self.app.after_render -= self.after_render
        if self.app.config.run and self.app.config.save:
            self.save()
        super().close(cb)

    def before_render(self, app: "Application[Any]") -> "None":
        """Run the cell before rendering it if needed."""
        if (
            self.app.tab == self
            and self.cell_index == 0
            and self.app.config.show_filenames
        ):
            self.print_title()

        if not self.json["cells"]:
            log.error("No cells")
            self.app.print_text([("", "(No cells to display)\n")])
            self.app.close_tab(self)

        elif self.app.config.run:
            cell = self.cell()
            cell.run_or_render(wait=True)
            # self.kernel.wait_for_status("idle")

    def after_render(self, app: "Application[Any]") -> "None":
        """Close the tab if all cells have been rendered."""
        if self.app.tab == self:
            if self.cell_index < len(self.json["cells"]) - 1:
                self.cell_index += 1
            else:
                self.app.close_tab(self)

    def get_cell(self, index: "int") -> "Cell":
        """Render a cell by its index."""
        if index < len(self.json["cells"]):
            return Cell(index, self.json["cells"][index], self)
        else:
            return Cell(0, {}, self)

    def cell(self) -> "Cell":
        """Return the current cell."""
        return self.cells[(self.cell_index,)]

    def load_container(self) -> "AnyContainer":
        """Abscract method for loading the notebook's main container."""
        return PrintingContainer(
            [
                VSplit(
                    [
                        ConditionalContainer(
                            Window(), filter=~self.app.config.filter("expand")
                        ),
                        Box(
                            body=DynamicContainer(lambda: self.cell()),
                            padding=0,
                            width=Dimension(
                                preferred=self.app.config.max_notebook_width
                            ),
                        ),
                        ConditionalContainer(
                            Window(), filter=~self.app.config.filter("expand")
                        ),
                    ]
                )
            ]
        )

    # ################################### Settings ####################################

    add_setting(
        name="run",
        flags=["--run"],
        type_=bool,
        help_="Run the notebook files when loaded",
        default=False,
        description="""
            If set, notebooks will be run automatically when opened, or if previewing a
            file, the notebooks will be run before being output.
        """,
    )

    add_setting(
        name="save",
        flags=["--save"],
        type_=bool,
        help_="Save the notebook after running it",
        default=False,
        description="""
            If set, notebooks will be saved after they have been run. This setting only
            has any affect if the :option:`run` setting is active.
        """,
    )

    add_setting(
        name="show_filenames",
        flags=["--show-filenames"],
        type_=bool,
        help_="Show the notebook filenames when previewing multiple notebooks",
        default=False,
        description="""
            If set, the notebook filenames will be printed above each notebook's output
            when multiple notebooks are being previewed.
        """,
    )

    add_setting(
        name="cell_start",
        flags=["--cell-start"],
        type_=int,
        help_="The first cell to include in the preview",
        default=None,
        description="""
            When set, only cells after the given cell index will be shown.
        """,
    )

    add_setting(
        name="cell_stop",
        flags=["--cell-stop"],
        type_=int,
        help_="The last cell to include in the preview",
        default=None,
        description="""
            When set, only cells before the given cell index will be shown.
        """,
    )
