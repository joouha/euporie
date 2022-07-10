"""Contains a container for the cell output area."""

import logging
from abc import ABCMeta, abstractmethod
from pathlib import PurePath
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import HSplit, to_container
from prompt_toolkit.widgets.base import Box

from euporie.core.app import get_app
from euporie.core.convert.base import MIME_FORMATS, find_route
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Protocol, Tuple

    from prompt_toolkit.layout.containers import AnyContainer, Container

    from euporie.core.comm.base import CommContainer

    class OutputParent(Protocol):
        """An output's parent."""

        nb: "CommContainer"

        def refresh(self, now: "bool" = True) -> "None":
            """Update the parent container."""
            ...


log = logging.getLogger(__name__)


class CellOutputElement(metaclass=ABCMeta):
    """Base class for the various types of cell outputs (display data or widgets)."""

    def __init__(
        self,
        mime: "str",
        data: "str",
        metadata: "Dict",
        parent: "Optional[OutputParent]",
    ) -> "None":
        """Create a new instances of the output element.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            parent: The cell the output-element is attached to

        """
        ...

    def scroll_left(self) -> "None":
        """Scrolls the output left."""
        pass

    def scroll_right(self) -> "None":
        """Scrolls the output right."""
        pass

    @abstractmethod
    def __pt_container__(self) -> "AnyContainer":
        """Return the container representing the cell output element."""
        ...


class CellOutputDataElement(CellOutputElement):
    """A cell output element which display data."""

    def __init__(
        self,
        mime: "str",
        data: "Dict[str, Any]",
        metadata: "Dict",
        parent: "Optional[OutputParent]",
    ) -> "None":
        """Create a new data output element instance.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            parent: The cell the output-element is attached to
        """
        self.parent = parent

        # Get foreground and background colors
        fg_color = None
        if parent is not None:
            fg_color = get_app().color_palette.fg.base_hex
        bg_color = {"light": "#FFFFFF", "dark": "#000000"}.get(
            str(metadata.get("needs_background"))
        )

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
            fg_color=fg_color,
            bg_color=bg_color,
            px=metadata.get("width"),
            py=metadata.get("height"),
            focusable=False,
            focus_on_click=False,
            wrap_lines=False,
            always_hide_cursor=True,
            style=f"class:cell.output.element.data class:mime.{mime.replace('/','.')}",
        )

    def scroll_left(self) -> "None":
        """Scrolls the output left."""
        self.container.window._scroll_left()

    def scroll_right(self) -> "None":
        """Scrolls the output right."""
        self.container.window._scroll_right()

    def __pt_container__(self) -> "AnyContainer":
        """Return the display container."""
        return self.container


class CellOutputWidgetElement(CellOutputElement):
    """A cell output element which displays ipywidgets."""

    def __init__(
        self,
        mime: "str",
        data: "Dict[str, Any]",
        metadata: "Dict",
        parent: "Optional[OutputParent]",
    ) -> "None":
        """Create a new widget output element instance.

        Args:
            mime: The mime-type of the data to display:
                ``application/vnd.jupyter.widget-view+json``
            data: The data to display (the widget model ID)
            metadata: Any metadata relating to the data
            parent: The parent container the output-element is attached to

        Raises:
            NotImplementedError: Raised when an ipywidget cannot be rendered
        """
        self.parent = parent
        self.comm_id = str(data.get("model_id"))

        if parent is not None and (comm := parent.nb.comms.get(self.comm_id)):
            self.container = Box(
                comm.new_view(parent),
                padding_left=0,
                style="class:ipywidget",
            )
        else:
            raise NotImplementedError

    def __pt_container__(self) -> "AnyContainer":
        """Return a box container which holds a view of an ipywidget."""
        return self.container


MIME_RENDERERS = {
    "application/vnd.jupyter.widget-view+json": CellOutputWidgetElement,
    "*": CellOutputDataElement,
}

MIME_ORDER = [
    "application/vnd.jupyter.widget-view+json",
    "image/*",
    "application/pdf",
    "text/latex",
    "text/markdown",
    "text/x-markdown",
    "text/x-python-traceback",
    "text/stderr",
    "text/html",
    "text/*",
    "*",
]


def _calculate_mime_rank(mime_data: "Tuple[str, Any]") -> "int":
    """Scores the richness of mime output types."""
    mime, data = mime_data
    for i, ranked_mime in enumerate(MIME_ORDER):
        # Uprank plain text with escape sequences
        if mime == "text/plain" and "\x1b[" in data:
            i -= 2
        if mime == "text/html" and "<" not in data:
            i += 2
        if PurePath(mime).match(ranked_mime):
            return i
    else:
        return 999


class CellOutput:
    """Represents a single cell output.

    Capable of displaying multiple mime representations of the same data.

    TODO - allow the visible mime-type to be rotated.
    """

    def __init__(
        self, json: "Dict[str, Any]", parent: "Optional[OutputParent]"
    ) -> "None":
        """Creates a new cell output instance.

        Args:
            json: The cell output's json
            parent: The output's parent container
        """
        # Select the first mime-type to render
        self.parent = parent
        self._json = json
        self._selected_mime: "Optional[str]" = None
        self._containers: "Dict[str, CellOutputElement]" = {}

    @property
    def selected_mime(self) -> "str":
        """Return the selected mime-type, defaulting to the first."""
        data = self.data
        # If an mime-type has not been explicitly selected, display the first
        if self._selected_mime not in data:
            return next(x for x in self.data)
        return self._selected_mime

    @property
    def json(self) -> "Dict":
        """Returns the cell output JSON object."""
        return self._json

    @json.setter
    def json(self, outputs_json: "Dict") -> "None":
        self._json = outputs_json
        self._containers = {}
        self._selected_mime = None

    @property
    def container(self) -> "CellOutputElement":
        """Creates a container for the cell output mime-type if it doesn't exist.

        Returns:
            A :class:`OutputElement` container for the currently selected mime-type.
        """
        if self.selected_mime not in self._containers:
            for mime_pattern, OutputElement in MIME_RENDERERS.items():
                if PurePath(self.selected_mime).match(mime_pattern):
                    try:
                        element = OutputElement(
                            mime=self.selected_mime,
                            data=self.data[self.selected_mime],
                            metadata=self.json.get("metadata", {}).get(
                                self.selected_mime, {}
                            ),
                            parent=self.parent,
                        )
                    except NotImplementedError:
                        self._selected_mime = list(self.data.keys())[-1]
                        continue
                    else:
                        self._containers[self.selected_mime] = element
                        return element

        return self._containers[self.selected_mime]

    @property
    def data(self) -> "Dict[str, Any]":
        """Return dictionary of mime types and data for this output.

        This generates similarly structured data objects for markdown cells and text
        output streams.

        Returns:
            JSON dictionary mapping mimes type to representation data.

        """
        data = {}
        output_type = self.json.get("output_type", "unknown")
        if output_type == "stream":
            data = {f'stream/{self.json.get("name")}': self.json.get("text", "")}
        elif output_type == "error":
            data = {
                "text/x-python-traceback": "\n".join(self.json.get("traceback", ""))
            }
        else:
            data = self.json.get("data", {"text/plain": ""})
        return dict(sorted(data.items(), key=_calculate_mime_rank))

    def scroll_left(self) -> "None":
        """Scrolls the currently visible output left."""
        self.container.scroll_left()

    def scroll_right(self) -> "None":
        """Scrolls the currently visible output right."""
        self.container.scroll_right()

    def __pt_container__(self):
        """Return the cell output container (an :class:`OutputElement`)."""
        return self.container


class CellOutputArea:
    """An area below a cell where one or more cell outputs can be shown."""

    def __init__(
        self,
        json: "List[Dict[str, Any]]",
        parent: "Optional[OutputParent]",
        style: "str" = "",
    ) -> "None":
        """Creates a new cell output area instance.

        Args:
            json: The cell's output json
            parent: The parent container the output belongs to
            style: Additional style to apply to the output

        """
        self.parent = parent
        self._rendered_outputs: "List[CellOutput]" = []
        self.style = style
        self.container = HSplit([], style=lambda: self.style)
        self.json = json

    def reset(self) -> "None":
        """Clears all outputs from the output area."""
        self.style = ""
        self.json = []

    @property
    def json(self) -> "List[Dict[str, Any]]":
        """Returns the output area's JSON data."""
        return self._json

    @json.setter
    def json(self, outputs_json: "List[Dict[str, Any]]") -> "None":
        self._json = outputs_json
        self.container.children = self.rendered_outputs

    @property
    def rendered_outputs(self) -> "List[Container]":
        """Generates a list of rendered outputs."""
        n_existing_outputs = len(self._rendered_outputs)
        rendered_outputs: "List[CellOutput]" = []
        for i, output_json in enumerate(self.json):
            if i < n_existing_outputs:
                output = self._rendered_outputs[i]
                output.json = output_json
            else:
                output = CellOutput(output_json, self.parent)
            rendered_outputs.append(output)
        self._rendered_outputs = rendered_outputs
        return [to_container(x) for x in rendered_outputs]

    def scroll_left(self) -> "None":
        """Scrolls the outputs left."""
        for cell_output in self._rendered_outputs:
            cell_output.scroll_left()

    def scroll_right(self) -> "None":
        """Scrolls the outputs right."""
        for cell_output in self._rendered_outputs:
            cell_output.scroll_right()

    def __pt_container__(self) -> "AnyContainer":
        """Return the cell output area container (an :class:`HSplit`)."""
        return self.container
