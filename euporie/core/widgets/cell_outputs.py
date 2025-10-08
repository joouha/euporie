"""Contain a container for the cell output area."""

from __future__ import annotations

import logging
import weakref
from abc import ABCMeta, abstractmethod
from functools import cache
from pathlib import PurePath
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.layout.containers import (
    DynamicContainer,
    to_container,
)

from euporie.core.app.current import get_app
from euporie.core.convert.registry import find_route
from euporie.core.layout.containers import HSplit
from euporie.core.widgets.display import Display
from euporie.core.widgets.layout import Box
from euporie.core.widgets.tree import JsonView

if TYPE_CHECKING:
    from typing import Any, Protocol, TypeVar
    from weakref import ReferenceType

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.config import Setting
    from euporie.core.tabs.kernel import KernelTab
    from euporie.core.widgets.display import DisplayWindow

    KTParent = TypeVar("KTParent", bound=KernelTab)

    class OutputParent(Protocol[KTParent]):
        """An output's parent."""

        kernel_tab: KTParent

        def refresh(self, now: bool = True) -> None:
            """Update the parent container."""


log = logging.getLogger(__name__)


class CellOutputElement(metaclass=ABCMeta):
    """Base class for the various types of cell outputs (display data or widgets)."""

    data: Any

    def __init__(
        self,
        mime: str,
        data: Any,
        metadata: dict,
        parent: OutputParent | None,
    ) -> None:
        """Create a new instances of the output element.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            parent: The cell the output-element is attached to

        """

    @property
    def width(self) -> int | None:
        """Return the current width of the output's content."""
        return None

    def scroll_left(self) -> None:
        """Scroll the output left."""

    def scroll_right(self, max: int | None = None) -> None:
        """Scroll the output right."""

    @abstractmethod
    def __pt_container__(self) -> AnyContainer:
        """Return the container representing the cell output element."""
        ...


class CellOutputDataElement(CellOutputElement):
    """A cell output element which display data."""

    def __init__(
        self,
        mime: str,
        data: Any,
        metadata: dict,
        parent: OutputParent | None,
    ) -> None:
        """Create a new data output element instance.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            parent: The cell the output-element is attached to
        """
        from euporie.core.convert.datum import Datum
        from euporie.core.convert.formats import BASE64_FORMATS
        from euporie.core.convert.mime import MIME_FORMATS

        self.parent = parent

        # Get foreground and background colors
        bg_color = {"light": "#FFFFFF", "dark": "#000000"}.get(
            str(metadata.get("needs_background"))
        )

        # Get internal format
        format_ = "ansi"
        mime_path = PurePath(mime)
        for mime_type, data_format in MIME_FORMATS.items():
            if mime_path.match(mime_type):
                if data_format in BASE64_FORMATS:
                    data_format = f"base64-{data_format}"
                if find_route(data_format, "ft") is not None:
                    format_ = data_format
                    break

        config = get_app().config

        # Limit size of text only outputs
        if (
            format_ == "ansi"
            and (limit := config.text_output_limit) > 0
            and len(data) > limit
        ):
            data = data[:limit] + "\n… (Output truncated)"

        self._datum = Datum(
            data,
            format_,
            px=metadata.get("width"),
            py=metadata.get("height"),
            bg=bg_color,
        )

        self.container = Display(
            self._datum,
            focusable=False,
            focus_on_click=False,
            wrap_lines=config.filters.wrap_cell_outputs,
            always_hide_cursor=True,
            style=f"class:mime-{mime.replace('/', '-')}",
            scrollbar=False,
        )

        # Ensure container gets invalidated if `wrap_cell_output` changes
        self.container.control.invalidate_events.append(config.events.wrap_cell_outputs)

        # Reset scroll position on `wrap_cell_outputs` config change
        def _unregister(win: ReferenceType[DisplayWindow]) -> None:
            config.events.wrap_cell_outputs -= _reset_scroll

        weak_win = weakref.ref(self.container.window, _unregister)

        def _reset_scroll(caller: Setting | None = None) -> None:
            if (win := weak_win()) is not None:
                win.reset()

        config.events.wrap_cell_outputs += _reset_scroll

    @property
    def data(self) -> Any:
        """Return the control's display data."""
        return self._datum.data

    @data.setter
    def data(self, value: Any) -> None:
        """Set the cell output's data."""
        from euporie.core.convert.datum import Datum

        self._datum = Datum(
            value,
            self._datum.format,
            self._datum.px,
            self._datum.py,
        )
        self.container.datum = self._datum

    @property
    def width(self) -> int:
        """Return the current width of the output's content."""
        return self.container.window.content.max_line_width

    def scroll_left(self) -> None:
        """Scroll the output left."""
        self.container.window._scroll_left()

    def scroll_right(self, max: int | None = None) -> None:
        """Scroll the output right."""
        self.container.window._scroll_right(max)

    def __pt_container__(self) -> AnyContainer:
        """Return the display container."""
        return self.container


class CellOutputWidgetElement(CellOutputElement):
    """A cell output element which displays ipywidgets."""

    def __init__(
        self,
        mime: str,
        data: dict[str, Any],
        metadata: dict,
        parent: OutputParent | None,
    ) -> None:
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

        if parent is not None and (comm := parent.kernel_tab.comms.get(self.comm_id)):
            self.container = Box(
                comm.new_view(parent),
                padding_left=0,
                padding_top=0,
                padding_bottom=0,
                style="class:ipywidget",
            )
        else:
            raise NotImplementedError

    def __pt_container__(self) -> AnyContainer:
        """Return a box container which holds a view of an ipywidget."""
        return self.container


class CellOutputJsonElement(CellOutputElement):
    """A cell output element which displays JSON."""

    def __init__(
        self,
        mime: str,
        data: dict[str, Any],
        metadata: dict,
        parent: OutputParent | None,
    ) -> None:
        """Create a new widget output element instance.

        Args:
            mime: The mime-type of the data to display: ``application/json``
            data: The data to display (a JSON object)
            metadata: Any metadata relating to the data
            parent: The parent container the output-element is attached to
        """
        self.parent = parent
        self.container = JsonView(
            data, title=metadata.get("root"), expanded=metadata.get("expanded", True)
        )

    def __pt_container__(self) -> AnyContainer:
        """Return a box container which holds a view of an ipywidget."""
        return self.container


MIME_RENDERERS: dict[str, type[CellOutputElement]] = {
    "application/vnd.jupyter.widget-view+json": CellOutputWidgetElement,
    "application/json": CellOutputJsonElement,
    "*": CellOutputDataElement,
}

MIME_ORDER = [
    "application/vnd.jupyter.widget-view+json",
    "application/json",
    "image/*",
    "text/html",
    "text/markdown",
    "text/x-markdown",
    "application/pdf",
    "text/latex",
    "text/x-python-traceback",
    "text/stderr",
    "text/*",
    "*",
]


@cache
def _calculate_mime_rank(mime: str, have_escapes: bool) -> int:
    """Score the richness of mime output types."""
    for i, ranked_mime in enumerate(MIME_ORDER):
        # Uprank plain text with escape sequences
        if mime == "text/plain" and have_escapes:
            i -= 7
        if PurePath(mime).match(ranked_mime):
            return i
    else:
        return 999


def _mime_ranker(mime_data: tuple[str, Any]) -> int:
    """Score the richness of mime output types."""
    mime, data = mime_data
    return _calculate_mime_rank(mime, isinstance(data, str) and "\x1b[" in data)


class CellOutput:
    """Represent a single cell output.

    Capable of displaying multiple mime representations of the same data.

    TODO - allow the visible mime-type to be rotated.
    """

    def __init__(self, json: dict[str, Any], parent: OutputParent | None) -> None:
        """Create a new cell output instance.

        Args:
            json: The cell output's json
            parent: The output's parent container
        """
        # Select the first mime-type to render
        self.parent = parent
        self.json = json
        self._selected_mime: str | None = None
        self._elements: dict[str, CellOutputElement] = {}

    @property
    def selected_mime(self) -> str:
        """Return the selected mime-type, selecting the first by default."""
        if self._selected_mime is None:
            self._selected_mime = next(x for x in self.data)
        return self._selected_mime

    @selected_mime.setter
    def selected_mime(self, value: str) -> None:
        self._selected_mime = value

    @property
    def data(self) -> dict[str, Any]:
        """Return dictionary of mime types and data for this output.

        This generates similarly structured data objects for markdown cells and text
        output streams.

        Returns:
            JSON dictionary mapping mimes type to representation data.

        """
        data = {}
        output_type = self.json.get("output_type", "unknown")
        if output_type == "stream":
            data = {f"stream/{self.json.get('name')}": self.json.get("text", "")}
        elif output_type == "error":
            ename = self.json.get("ename", "")
            evalue = self.json.get("evalue", "")
            traceback = "\n".join(self.json.get("traceback", ""))
            data = {"text/x-python-traceback": f"{ename}: {evalue}\n{traceback}"}
        else:
            data = self.json.get("data", {"text/plain": ""})
        return dict(sorted(data.items(), key=_mime_ranker))

    def update(self) -> None:
        """Update the output by updating all child containers."""
        # log.debug("Updating %s", self)
        data = self.data
        for mime_type, element in list(self._elements.items()):
            if mime_type in data:
                element.data = data[mime_type]
            else:
                del self._elements[mime_type]

    def make_element(self, mime: str) -> CellOutputElement:
        """Create a container for the cell output mime-type if it doesn't exist.

        Args:
            mime: The mime-type for which to create an output element

        Returns:
            A :class:`OutputElement` container for the currently selected mime-type.
        """
        data = self.data
        for mime_pattern, OutputElement in MIME_RENDERERS.items():
            if PurePath(mime).match(mime_pattern):
                try:
                    element = OutputElement(
                        mime=mime,
                        data=data[mime],
                        metadata=self.json.get("metadata", {}).get(mime, {}),
                        parent=self.parent,
                    )
                except (NotImplementedError, KeyError):
                    self.selected_mime = mime = list(data.keys())[-1]
                    continue
                else:
                    return element
        return CellOutputDataElement(
            "text/plain", "(Cannot display output)", {}, self.parent
        )

    def get_element(self, mime: str) -> CellOutputElement:
        """Return the currently displayed cell element."""
        if mime not in self._elements:
            element = self.make_element(mime)
            self._elements[mime] = element
            return element
        return self._elements[mime]

    @property
    def element(self) -> CellOutputElement:
        """Get the element for the currently selected mime type."""
        return self.get_element(self.selected_mime)

    def __pt_container__(self) -> AnyContainer:
        """Return the cell output container (an :class:`OutputElement`)."""
        return DynamicContainer(lambda: self.element)

    def scroll_left(self) -> None:
        """Scroll the currently visible output left."""
        self.element.scroll_left()

    def scroll_right(self, max: int | None = None) -> None:
        """Scroll the currently visible output right."""
        self.element.scroll_right(max)


class CellOutputArea:
    """An area below a cell where one or more cell outputs can be shown."""

    output_cache: SimpleCache[str, CellOutput] = SimpleCache()

    def __init__(
        self,
        json: list[dict[str, Any]],
        parent: OutputParent | None,
        style: str = "",
    ) -> None:
        """Create a new cell output area instance.

        Args:
            json: The cell's output json
            parent: The parent container the output belongs to
            style: Additional style to apply to the output

        """
        self._json: list[dict[str, Any]] = []
        self.parent = parent
        self.style = style
        self.display_json: list[dict[str, Any]] = []
        self.rendered_outputs: list[CellOutput] = []
        self.container = HSplit([], style=lambda: self.style)
        self.children = self.container.children
        self.json = json

    @property
    def json(self) -> Any:
        """Return the control's display data."""
        return self._json

    @json.setter
    def json(self, value: Any) -> None:
        """Set the cell output area JSON data."""
        # Reset if we have lost existing outputs
        if any(old_output_json not in value for old_output_json in self._json):
            self.reset()
        # Add any new outputs we do not already have
        for new_output_json in value:
            if new_output_json not in self._json:
                self.add_output(new_output_json, refresh=False)
        get_app().invalidate()

    def add_output(self, output_json: dict[str, Any], refresh: bool = True) -> None:
        """Add a new output to the output area."""
        # Update json
        self._json.append(output_json)
        # Update display json
        add_output = True
        if name := output_json.get("name"):
            for existing_output, rendered_output in zip(
                self.display_json, self.rendered_outputs
            ):
                if name == existing_output.get("name"):
                    existing_output["text"] += output_json.get("text", "")
                    rendered_output.update()
                    add_output = False
                    break
        if add_output:
            # Add a copy to the display json so the original does not get modified
            output_json_copy = dict(output_json)
            self.display_json.append(output_json_copy)
            # Create an output container with the copy
            output = CellOutput(output_json_copy, self.parent)
            self.rendered_outputs.append(output)
            self.children.append(to_container(output))
        if refresh:
            get_app().invalidate()

    def update(self) -> None:
        """Update all existing outputs."""
        for output in self.rendered_outputs:
            output.update()

    def reset(self) -> None:
        """Clear all outputs from the output area."""
        self.style = ""
        self._json.clear()
        self.display_json.clear()
        self.rendered_outputs.clear()
        self.children.clear()

    def scroll_left(self) -> None:
        """Scroll the outputs left."""
        for cell_output in self.rendered_outputs:
            cell_output.scroll_left()

    def scroll_right(self) -> None:
        """Scroll the outputs right."""
        max_width = max(
            (cell_output.element.width or 0 for cell_output in self.rendered_outputs),
            default=None,
        )
        for cell_output in self.rendered_outputs:
            cell_output.scroll_right(max_width)

    def __pt_container__(self) -> AnyContainer:
        """Return the cell output area container (an :class:`HSplit`)."""
        return self.container

    def to_plain_text(self) -> str:
        """Convert the contents of the output to plain text."""
        from prompt_toolkit.formatted_text.utils import to_plain_text

        outputs = []
        app = get_app()
        config = app.config
        for cell_output in self.rendered_outputs:
            if isinstance(cell_output.element, CellOutputDataElement):
                control = cell_output.element.container.control
                for line in control.get_lines(
                    control.datum,
                    width=88,
                    height=None,
                    fg=(cp := app.color_palette).fg.base_hex,
                    bg=cp.bg.base_hex,
                    wrap_lines=config.wrap_cell_outputs,
                ):
                    outputs.append(to_plain_text(line))
        return "\n".join(outputs)
