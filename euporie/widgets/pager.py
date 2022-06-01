"""Contains a container for the cell output area."""

import logging
from pathlib import PurePath
from typing import TYPE_CHECKING

from euporie.convert.base import MIME_FORMATS, find_route
from euporie.widgets.cell_outputs import CellOutput, CellOutputDataElement
from euporie.widgets.display import Display

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

    from euporie.widgets.cell import Cell
    from euporie.widgets.cell_outputs import CellOutputElement

log = logging.getLogger(__name__)


class PagerOutputDataElement(CellOutputDataElement):
    """A cell output element which display data."""

    def __init__(
        self,
        mime: "str",
        data: "Dict[str, Any]",
        metadata: "Dict",
        cell: "Optional[Cell]",
    ) -> "None":
        """Create a new data output element instance.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            cell: The cell the output-element is attached to
        """
        # Get internal format
        format_ = "ansi"
        mime_path = PurePath(mime)
        for format_mime, mime_format in MIME_FORMATS.items():
            if mime_path.match(format_mime):
                if find_route(mime_format, "formatted_text") is not None:
                    format_ = mime_format
                    break

        self.container = Display(
            data=data,
            format_=format_,
            focusable=True,
            focus_on_click=True,
            show_scrollbar=True,
            wrap_lines=True,
            always_hide_cursor=True,
            style="class:pager",
        )


class Pager(CellOutput):
    """Display pager output."""

    @property
    def container(self) -> "CellOutputElement":
        """Creates a container for the pager output mime-type if it doesn't exist.

        Returns:
            A :class:`PagerOutputDataElement` container for the currently selected mime-type.
        """
        if self.selected_mime not in self._containers:
            self._containers[self.selected_mime] = PagerOutputDataElement(
                mime=self.selected_mime,
                data=self.data[self.selected_mime],
                metadata=self.json.get("metadata", {}).get(self.selected_mime, {}),
                cell=self.cell,
            )
        return self._containers[self.selected_mime]
