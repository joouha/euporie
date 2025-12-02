"""Define representations for :py:class:`ipywidget` comms."""

from __future__ import annotations

import bisect
import logging
import re
from abc import ABCMeta, abstractmethod
from base64 import standard_b64encode
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.processors import BeforeInput

from euporie.core.border import InsetGrid
from euporie.core.comm.base import Comm, CommView
from euporie.core.data_structures import DiBool
from euporie.core.kernel.jupyter import MsgCallbacks
from euporie.core.layout.decor import FocusedStyle
from euporie.core.widgets.decor import Border
from euporie.core.widgets.forms import (
    BaseButton,
    Button,
    Checkbox,
    Dropdown,
    Label,
    LabelledWidget,
    Progress,
    Select,
    Slider,
    Swatch,
    Text,
    ToggleButton,
    ToggleButtons,
)
from euporie.core.widgets.layout import (
    AccordionSplit,
    Box,
    ReferencedSplit,
    TabbedSplit,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableSequence, Sequence
    from typing import Any

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text.base import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer, _Split

    from euporie.core.tabs.kernel import KernelTab
    from euporie.core.widgets.cell_outputs import OutputParent
    from euporie.core.widgets.forms import SelectableWidget, ToggleableWidget
    from euporie.core.widgets.layout import StackedSplit

    JSONType = str | int | float | bool | None | dict[str, Any] | Iterable[Any]

log = logging.getLogger(__name__)


_binary_types = (memoryview, bytearray, bytes)

WIDGET_MODELS: dict[str, type[IpyWidgetComm]] = {}


def _separate_buffers(
    substate: dict | list | tuple,
    path: list[str | int],
    buffer_paths: list[list[str | int]],
    buffers: MutableSequence[memoryview | bytearray | bytes],
) -> dict | list | tuple:
    """Remove binary types from dicts and lists, but keep track of their paths.

    Any part of the dict/list that needs modification will be cloned, so the original
    stays untouched.

    Args:
        substate: A dictionary or list like containing binary data
        path: A list of dictionary/list keys describing the path root to the substate
        buffer_paths: A list to which binary buffer paths will be added
        buffers: A list to which binary buffers will be added

    Raises:
        ValueError: Raised when the substate is not a list, tuple or dictionary

    Returns:
        The updated substrate without buffers
    """
    cloned_substrate: list | dict | None = None
    if isinstance(substate, (list, tuple)):
        for i, v in enumerate(substate):
            if isinstance(v, _binary_types):
                if cloned_substrate is None:
                    cloned_substrate = list(substate)  # shallow clone list/tuple
                assert isinstance(cloned_substrate, list)
                cloned_substrate[i] = None
                buffers.append(v)
                buffer_paths.append([*path, i])
            elif isinstance(v, (dict, list, tuple)):
                vnew = _separate_buffers(v, [*path, i], buffer_paths, buffers)
                if v is not vnew:  # only assign when value changed
                    if cloned_substrate is None:
                        cloned_substrate = list(substate)  # shallow clone list/tuple
                    assert isinstance(cloned_substrate, list)
                    cloned_substrate[i] = vnew
    elif isinstance(substate, dict):
        for k, v in substate.items():
            if isinstance(v, _binary_types):
                if cloned_substrate is None:
                    cloned_substrate = dict(substate)  # shallow clone dict
                del cloned_substrate[k]
                buffers.append(v)
                buffer_paths.append([*path, k])
            elif isinstance(v, (dict, list, tuple)):
                vnew = _separate_buffers(v, [*path, k], buffer_paths, buffers)
                if v is not vnew:  # only assign when value changed
                    if cloned_substrate is None:
                        cloned_substrate = dict(substate)  # clone list/tuple
                    cloned_substrate[k] = vnew
    else:
        raise ValueError(f"Expected state to be a list or dict, not {substate!r}")
    return cloned_substrate if cloned_substrate is not None else substate


class IpyWidgetComm(Comm, metaclass=ABCMeta):
    """A Comm object which represents ipython widgets."""

    target_name = "jupyter.widget"

    def __init__(
        self,
        comm_container: KernelTab,
        comm_id: str,
        data: dict,
        buffers: Sequence[memoryview | bytearray | bytes],
    ) -> None:
        """Create a new instance of the ipywidget."""
        super().__init__(comm_container, comm_id, data, buffers)
        self.sync = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Add ipywidget model classes to a registry when they are created."""
        super().__init_subclass__(**kwargs)
        if cls.__name__.endswith("Model"):
            WIDGET_MODELS[cls.__name__] = cls

    def set_state(self, key: str, value: JSONType) -> None:
        """Send a ``comm_msg`` to the kernel with local state changes."""
        if self.sync:
            self.data.setdefault("state", {})[key] = value
            if self.comm_container.kernel:
                self.comm_container.kernel.kc_comm(
                    comm_id=self.comm_id,
                    data={"method": "update", "state": {key: value}},
                )
            self.update_views({key: value})

    def process_data(
        self, data: dict, buffers: Sequence[memoryview | bytearray | bytes]
    ) -> None:
        """Handle incoming Comm update messages, updating the state and views."""
        # Add buffers to data based on buffer paths
        self.buffers = list(buffers)
        for buffer_path, buffer in zip(
            data.get("buffer_paths", []),
            buffers,
        ):
            parent = data["state"]
            for key in buffer_path[:-1]:
                parent = parent[key]
            parent[buffer_path[-1]] = buffer

        method = data.get("method")
        if method is None:
            self.data = data
        elif method == "update":
            changes = data.get("state", {})
            self.data["state"].update(changes)
            self.update_views(changes)

    @abstractmethod
    def create_view(self, parent: OutputParent) -> CommView:
        """Abstract method for creating a view of the ipywidget."""

    def _get_embed_state(self) -> dict[str, Any]:
        """Convert the ipywidgets state to embeddable json."""
        buffer_paths: list[list[str | int]] = []
        buffers: list[bytes] = []
        state = _separate_buffers(self.data["state"], [], buffer_paths, buffers)
        assert isinstance(state, dict)
        return {
            "model_name": state.get("_model_name"),
            "model_module": state.get("_model_module"),
            "model_module_version": state.get("_model_module_version"),
            "state": {
                **dict(state.items()),
                "buffers": [
                    {
                        "encoding": "base64",
                        "path": p,
                        "data": standard_b64encode(d).decode("ascii"),
                    }
                    for p, d in zip(buffer_paths, buffers)
                ],
            },
        }


class UnimplementedModel(IpyWidgetComm):
    """An ipywidget used to represent unimplemented widgets."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view."""
        from euporie.core.convert.datum import Datum
        from euporie.core.widgets.display import Display

        return CommView(Display(Datum("[Widget not implemented]", format="ansi")))


class OutputModel(IpyWidgetComm):
    """An Output ipywidget."""

    model_name = "OutputModel"

    def __init__(
        self,
        comm_container: KernelTab,
        comm_id: str,
        data: dict,
        buffers: Sequence[memoryview | bytearray | bytes],
    ) -> None:
        """Create a new output ipywidget instance."""
        super().__init__(comm_container, comm_id, data, buffers)
        self.clear_output_wait = False
        self.prev_msg_id = ""
        self.original_callbacks = MsgCallbacks()
        self.callbacks: MsgCallbacks = MsgCallbacks(
            {
                "add_output": self.add_output,
                "clear_output": self.clear_output,
            }
        )

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of this output ipywidget."""
        from euporie.core.widgets.cell_outputs import CellOutputArea

        container = CellOutputArea(
            self.data.get("state", {}).get("outputs", []), parent
        )
        return CommView(
            container,
            {"outputs": partial(setattr, container, "json")},
        )

    def add_output(self, json: dict[str, Any], own: bool) -> None:
        """Add a new output to this widget."""
        if self.clear_output_wait:
            self.set_state("outputs", [json])
        else:
            self.set_state("outputs", [*self.data["state"]["outputs"], json])

    def clear_output(self, wait: bool = False) -> None:
        """Remove all outputs from this widget."""
        if wait:
            self.clear_output_wait = True
        else:
            self.clear_output_wait = False
            self.set_state("outputs", [])

    def process_data(
        self, data: dict, buffers: Sequence[memoryview | bytearray | bytes]
    ) -> None:
        """Modify the callbacks of a given message to add outputs to this ipywidget."""
        if (
            data.get("method") == "update"
            and self.comm_container.kernel
            and (msg_id := data.get("state", {}).get("msg_id")) is not None
        ):
            # Replace the kernel callbacks of the given message ID
            if msg_id:
                # Replace the message's callbacks, saving a copy
                self.original_callbacks = copy(
                    self.comm_container.kernel.msg_id_callbacks[msg_id]
                )
                del self.comm_container.kernel.msg_id_callbacks[msg_id]
                self.comm_container.kernel.msg_id_callbacks[msg_id].update(
                    self.callbacks
                )
            else:
                # Restore the message's callbacks
                if self.original_callbacks:
                    self.comm_container.kernel.msg_id_callbacks[self.prev_msg_id] = (
                        self.original_callbacks
                    )
                    self.original_callbacks = MsgCallbacks()
                else:
                    del self.comm_container.kernel.msg_id_callbacks[self.prev_msg_id]
            self.prev_msg_id = msg_id

        super().process_data(data, buffers)


class LayoutIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    """Base class for layout widgets with children."""

    def render_children(
        self, models: list[str], parent: OutputParent
    ) -> list[AnyContainer]:
        """Create views for the child Comms in the layout."""
        return [
            self.comm_container.comms[
                ipy_model[ipy_model.startswith("IPY_MODEL_") and len("IPY_MODEL_") :]
            ].new_view(parent)
            for ipy_model in models
        ]

    def box_style(self) -> str:
        """Convert the ipywidget box_style to a prompt_toolkit style string."""
        if style := self.data["state"].get("box_style", ""):
            return f"class:{style}"
        return "class:default"


class BoxModel(LayoutIpyWidgetComm):
    """A box layout ipywidget (basically the same a HBox)."""

    padding = 1
    Split: type[_Split] = VSplit

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the layout ipywidget."""
        container = ReferencedSplit(
            self.Split,
            self.render_children(self.data["state"]["children"], parent),
            padding=self.padding,
            style=self.box_style,
        )

        def set_children(models: list[str]) -> None:
            """Set the children in they layout view when they change."""
            container.children = self.render_children(models, parent)

        return CommView(
            container,
            {"children": set_children},
        )


class HBoxModel(BoxModel):
    """A horizontal layout ipywidget."""


class VBoxModel(BoxModel):
    """A vertical layout ipywidget."""

    Split = HSplit
    padding = 0


class TabModel(LayoutIpyWidgetComm):
    """A tabbed layout ipywidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the tabbed ipywidget."""
        children = self.data["state"]["children"]
        container = TabbedSplit(
            children=self.render_children(children, parent),
            titles=list(self.data["state"].get("_titles", {}).values())
            or [""] * len(children),
            active=self.data["state"].get("selected_index"),
            style=self.box_style,
            on_change=self.update_index,
        )

        def set_children(models: list[str]) -> None:
            """Set the children of the tab view when they change."""
            container.children = self.render_children(models, parent)

        def set_titles(new: dict[int, str]) -> None:
            """Set the titles on the tabs when they change."""
            titles = container.titles
            for index, value in new.items():
                titles[int(index)] = value
            container.titles = titles

        return CommView(
            container,
            {
                "children": set_children,
                "_titles": set_titles,
                "selected_index": partial(setattr, container, "active"),
            },
        )

    def update_index(self, container: StackedSplit) -> None:
        """Send a ``comm_message`` updating the selected index when it changes."""
        self.set_state("selected_index", container.active)


class AccordionModel(LayoutIpyWidgetComm):
    """An accoridon layout ipywidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the accordion ipywidget."""
        children = self.data["state"]["children"]
        container = AccordionSplit(
            children=self.render_children(children, parent),
            titles=list(self.data["state"].get("_titles", {}).values())
            or [""] * len(children),
            active=self.data["state"].get("selected_index"),
            style=self.box_style,
            on_change=self.update_index,
        )

        def set_children(models: list[str]) -> None:
            """Set the children of the accordion when they change."""
            container.children = self.render_children(models, parent)

        def set_titles(new: dict[int, str]) -> None:
            """Set the titles on the accordion when they change."""
            titles = container.titles
            for index, value in new.items():
                titles[int(index)] = value
            container.titles = titles

        return CommView(
            container,
            {
                "children": set_children,
                "_titles": set_titles,
                "selected_index": partial(setattr, container, "active"),
            },
        )

    def update_index(self, container: StackedSplit) -> None:
        """Send a ``comm_message`` updating the selected index when it changes."""
        self.set_state("selected_index", container.active)


class ButtonModel(IpyWidgetComm):
    """A Button ipywidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the button ipywidget."""
        button = Button(
            text=self.text,
            on_click=self.click,
            style=self.button_style,
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(button),
            setters={"description": partial(setattr, button, "text")},
        )

    def text(self) -> str:
        """Generate the button text, optionally including an icon if specified."""
        text = self.data["state"].get("description", "")
        if icon := self.data["state"].get("icon", ""):
            from euporie.core.reference import FA_ICONS

            text = f"{FA_ICONS.get(icon, '#')} {text}"
        return text

    def button_style(self) -> str:
        """Convert the ipywidget button_style to a prompt_toolkit style string."""
        if style := self.data["state"].get("button_style", ""):
            return f"class:ipywidget,{style}"
        return "class:ipywidget"

    def click(self, button: BaseButton) -> None:
        """Send a ``comm_msg`` describing a click event."""
        if self.comm_container.kernel:
            self.comm_container.kernel.kc_comm(
                comm_id=self.comm_id,
                data={"method": "custom", "content": {"event": "click"}},
            )


class TextBoxIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    """A mixin for ipywidgets which use text-box entry."""

    default_rows = 1
    multiline = False

    def validation(self, x: Any) -> bool:
        """Enure the entered text can be normalized."""
        return self.normalize(x) is not None

    def normalize(self, x: Any) -> Any | None:
        """Enure the selected value is permitted and the correct type."""
        return x

    def value(self) -> str:
        """Return the ipywidget's value."""
        return self.data["state"].get("value", "")

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the text-box ipywidget."""
        text = Text(
            text=self.value(),
            options=lambda: self.data["state"].get("options", []),
            on_text_changed=self.update_value,
            validation=self.validation,
            height=self.data["state"].get("rows") or self.default_rows,
            multiline=self.multiline,
            placeholder=self.data.get("state", {}).get("placeholder"),
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
            style="class:ipywidget",
        )
        labelled_widget = LabelledWidget(
            body=text,
            label=lambda: self.data.get("state", {}).get("description", ""),
            style="class:ipywidget",
            html=self.data.get("state", {}).get("description_allow_html", False),
        )
        container = FocusedStyle(labelled_widget)
        return CommView(
            container,
            setters={
                "value": lambda x: setattr(text.buffer, "text", str(x)),
                "rows": partial(setattr, text.window, "height"),
                "placeholder": partial(setattr, text, "placeholder"),
                "description_allow_html": partial(setattr, labelled_widget, "html"),
            },
        )

    def update_value(self, buffer: Buffer) -> None:
        """Set the selected index when the ipywidget's entered value changes."""
        if (value := self.normalize(buffer.text)) is not None:
            self.set_state("value", value)


class TextModel(TextBoxIpyWidgetComm):
    """A text input widget."""


class TextareaModel(TextBoxIpyWidgetComm):
    """A text input widget."""

    default_rows = 3
    multiline = True


class IntOptionsMixin:
    """A mixin for ipywidgets which accept a range of integer values."""

    data: dict[str, Any]

    def normalize(self, x: Any) -> int | None:
        """Enure the selected value is within the permitted range and is a integer."""
        try:
            value = int(x)
        except ValueError:
            return None
        else:
            if (minimum := self.data.get("state", {}).get("min")) and value < minimum:
                return None
            if (maximum := self.data.get("state", {}).get("max")) and maximum < value:
                return None
            return value

    @property
    def options(self) -> list[int]:
        """Generate a list of available options in a range of integers."""
        step = self.data["state"].get("step", 1)
        return list(
            range(
                self.data["state"].get("min", 0),
                self.data["state"].get("max", 100) + step,
                step,
            )
        )


class FloatOptionsMixin:
    """A mixin for ipywidgets which accept a range of float values."""

    data: dict[str, Any]

    def normalize(self, x: Any) -> float | None:
        """Enure the selected value is within the permitted range and is a float."""
        try:
            value = float(x)
        except ValueError:
            return None
        else:
            if (
                (minimum := self.data.get("state", {}).get("min")) and value <= minimum
            ) or (
                (maximum := self.data.get("state", {}).get("max")) and maximum <= value
            ):
                return None
            return value

    @property
    def options(self) -> list[float]:
        """Generate a list of available options in a range of floats."""
        step = Decimal(str(self.data["state"].get("step", 0.1)))
        start = Decimal(str(self.data["state"].get("min", 0)))
        stop = Decimal(str(self.data["state"].get("max", 100))) + step
        options = [float(start + step * i) for i in range(int((stop - start) / step))]
        # Ensure value is in list of options
        value = self.data["state"].get("value", 0.0)
        if value not in options:
            values = value if isinstance(value, list) else [value]
            for value in values:
                bisect.insort(options, value)
        return options


class FloatLogOptionsMixin(FloatOptionsMixin):
    """A mixin for ipywidgets which accept a value from range of exponents."""

    data: dict[str, Any]

    def normalize(self, x: Any) -> float | None:
        """Enure the selected value is within the permitted range and is a float."""
        try:
            value = float(x)
        except ValueError:
            return None
        else:
            base = Decimal(str(self.data["state"].get("base", 10)))
            start = Decimal(str(self.data["state"].get("min", 0)))
            if value <= base**start:
                return None
            stop = Decimal(str(self.data["state"].get("max", 4)))
            if base**stop <= value:
                return None
            return value

    @property
    def options(self) -> list[float]:
        """Generate a list of available options in a range of log values."""
        base = Decimal(str(self.data["state"].get("base", 10)))
        start = Decimal(str(self.data["state"].get("min", 0)))
        step = Decimal(str(self.data["state"].get("step", 1)))
        stop = Decimal(str(self.data["state"].get("max"))) + step
        options = [
            float(base ** (start + step * i)) for i in range(int((stop - start) / step))
        ]
        # Ensure value is in list of options
        value = self.data["state"].get("value", 0.0)
        if value not in options:
            bisect.insort(options, value)
        return options


class SliderIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    """Base class for slider ipywidgets."""

    def normalize(self, x: Any) -> Any:
        """Convert the internal widget's value to one compatible with the ipywidget."""
        return x

    @property
    @abstractmethod
    def options(self) -> list:
        """Abstract method to return a list of available options."""
        return []

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the slider ipywidget."""
        vertical = Condition(
            lambda: self.data["state"].get("orientation", "horizontal") == "vertical"
        )
        options = self.options
        slider = Slider(
            options=options,
            indices=self.indices,
            multiple=False,
            on_change=self.update_value,
            style="class:ipywidget",
            arrows=(
                lambda: "▼" if vertical() else "◀",
                lambda: "▲" if vertical() else "▶",
            ),
            show_arrows=True,
            vertical=Condition(
                lambda: self.data["state"].get("orientation", "horizontal")
                == "vertical"
            ),
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )

        labelled = LabelledWidget(
            body=slider,
            label=lambda: self.data["state"].get("description", ""),
            style="class:ipywidget",
            vertical=Condition(
                lambda: self.data["state"].get("orientation", "horizontal")
                == "vertical"
            ),
        )
        return CommView(
            FocusedStyle(labelled),
            setters={
                "value": partial(self.set_value, slider),
                "index": partial(self.set_value, slider),
                "_options_labels": partial(setattr, slider, "options"),
                "min": partial(lambda x: setattr(slider, "options", self.options)),
                "max": partial(lambda x: setattr(slider, "options", self.options)),
                "step": partial(lambda x: setattr(slider, "options", self.options)),
            },
        )

    @property
    def indices(self) -> list[Any]:
        """Return the selected index as a list."""
        return [
            self.options.index(value) for value in [self.data["state"].get("value", 0)]
        ]

    def update_value(self, container: SelectableWidget) -> None:
        """Send a ``comm_message`` updating the value when it changes."""
        if (index := container.index) is not None and (
            value := self.normalize(container.options[index])
        ) is not None:
            self.set_state("value", value)

    def set_value(self, slider: Slider, value: Any) -> None:
        """Set the selected index when the ipywidget's selected value changes."""
        if value in slider.options:
            slider.index = slider.options.index(value)
            slider.value_changed()


class RangeSliderIpyWidgetComm(SliderIpyWidgetComm):
    """Base class for range slider ipywidgets."""

    @property
    def indices(self) -> list[int]:
        """Return the first and last selected indices."""
        output = []
        for value in self.data["state"]["value"]:
            if value in self.options:
                output.append(self.options.index(value))
        return output

    def update_value(self, slider: SelectableWidget) -> None:
        """Send a ``comm_message`` updating the values when they change."""
        self.set_state(
            "value", [self.normalize(slider.options[index]) for index in slider.indices]
        )

    def set_value(self, slider: Slider, values: Any) -> None:
        """Any float value is permitted - we might need to add an option."""
        indices = slider.indices
        norm_values = [self.normalize(value) for value in values]
        for i, value in enumerate(norm_values):
            # Ensure value is in list of options
            if value not in slider.options:
                bisect.insort(slider.options, value)
            indices[i] = slider.options.index(value)
        slider.indices = indices
        slider.value_changed()


class IntSliderModel(IntOptionsMixin, SliderIpyWidgetComm):
    """A slider ipywidget that accepts a single integer value."""


class FloatSliderModel(FloatOptionsMixin, SliderIpyWidgetComm):
    """A slider ipywidget that accepts a single float value."""


class FloatLogSliderModel(FloatLogOptionsMixin, SliderIpyWidgetComm):
    """A slider ipywidget that accepts a single value on a log scale."""


class IntRangeSliderModel(IntOptionsMixin, RangeSliderIpyWidgetComm):
    """A slider ipywidget that accepts a range of integer values."""


class FloatRangeSliderModel(FloatOptionsMixin, RangeSliderIpyWidgetComm):
    """A slider ipywidget that accepts a range of float values."""


class NumberTextBoxIpyWidgetComm(TextBoxIpyWidgetComm, metaclass=ABCMeta):
    """Base class for text-box ipywidgets with numerical values."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the numerical text-box ipywidget."""
        disabled = disabled = Condition(
            lambda: self.data["state"].get("disabled", False)
        )

        text = Text(
            text=self.data.get("state", {}).get("value", ""),
            on_text_changed=self.update_value,
            validation=self.validation,
            disabled=disabled,
            style="class:ipywidget",
        )
        container = FocusedStyle(
            LabelledWidget(
                body=ReferencedSplit(
                    VSplit,
                    [
                        text,
                        Button(
                            "-",
                            show_borders=DiBool(True, False, True, True),
                            on_click=self.decr,
                            disabled=disabled,
                            style="class:ipywidget",
                        ),
                        Button(
                            "+",
                            show_borders=DiBool(True, True, True, False),
                            on_click=self.incr,
                            disabled=disabled,
                            style="class:ipywidget",
                        ),
                    ],
                ),
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            )
        )
        return CommView(
            container,
            setters={"value": partial(lambda x: setattr(text.buffer, "text", str(x)))},
        )

    def incr(self, button: BaseButton) -> None:
        """Increment the widget's value by one step."""
        value = Decimal(str(self.data["state"]["value"]))
        step = Decimal(str(self.data["state"].get("step", 1) or 1))
        if (new := self.normalize(value + step)) is not None:
            self.set_state("value", new)

    def decr(self, button: BaseButton) -> None:
        """Decrement the widget's value by one step."""
        value = Decimal(str(self.data["state"]["value"]))
        step = Decimal(str(self.data["state"].get("step", 1) or 1))
        if (new := self.normalize(value - step)) is not None:
            self.set_state("value", new)


class IntTextModel(IntOptionsMixin, NumberTextBoxIpyWidgetComm):
    """An integer textbox ipwidget."""


class BoundedIntTextModel(IntOptionsMixin, NumberTextBoxIpyWidgetComm):
    """An integer textbox ipwidget with upper and lower bounds."""


class FloatTextModel(FloatOptionsMixin, NumberTextBoxIpyWidgetComm):
    """A float textbox ipwidget."""


class BoundedFloatTextModel(FloatOptionsMixin, NumberTextBoxIpyWidgetComm):
    """An float textbox ipwidget with upper and lower bounds."""


class ProgressIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    """The base class for progress bar ipywidgets."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the progress bar."""
        vertical = Condition(
            lambda: self.data["state"].get("orientation", "horizontal") == "vertical"
        )
        progress = Progress(
            start=self.data["state"].get("min", 0),
            stop=self.data["state"].get("max", 100),
            step=self.data["state"].get("step", 1),
            value=self.data["state"].get("value", 0),
            vertical=vertical,
            style=self.bar_style,
        )
        container = FocusedStyle(
            LabelledWidget(
                body=progress,
                vertical=vertical,
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            ),
        )
        return CommView(
            container,
            setters={
                "value": partial(setattr, progress, "value"),
                "min": partial(setattr, progress.control, "start"),
                "max": partial(setattr, progress.control, "stop"),
            },
        )

    def bar_style(self) -> str:
        """Convert the ipywidget ``bar_style`` to a prompt_toolkit style string."""
        if style := self.data["state"].get("bar_style", ""):
            return f"class:{style}"
        return ""


class IntProgressModel(IntOptionsMixin, ProgressIpyWidgetComm):
    """A progress bar ipywidget that accepts integer values."""


class FloatProgressModel(FloatOptionsMixin, ProgressIpyWidgetComm):
    """A progress bar ipywidget that accepts float values."""


class ToggleableIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    """Base class for toggleable ipywidgets."""

    def normalize(self, x: Any) -> float | None:
        """Cat the container's selected value to a bool if possible."""
        try:
            value = bool(x)
        except ValueError:
            return None
        else:
            return value

    def value_changed(self, button: ToggleableWidget) -> None:
        """Send a ``comm_message`` updating the value when it changes."""
        if (value := self.normalize(button.selected)) is not None:
            self.set_state("value", value)


class ToggleButtonModel(ToggleableIpyWidgetComm):
    """A toggleable button ipywidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the toggle button ipywidget."""
        button = ToggleButton(
            text=self.text,
            on_click=self.value_changed,
            selected=self.data["state"].get("value", False),
            style=self.button_style,
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(
                button,
            ),
            setters={"value": partial(setattr, button, "selected")},
        )

    def text(self) -> str:
        """Generate the button text, optionally including an icon if specified."""
        text = self.data["state"].get("description", "")
        if icon := self.data["state"].get("icon", ""):
            from euporie.core.reference import FA_ICONS

            text = f"{FA_ICONS.get(icon, '#')} {text}"
        return text

    def button_style(self) -> str:
        """Convert the ipywidget button_style to a prompt_toolkit style string."""
        if style := self.data["state"].get("button_style", ""):
            return f"class:ipywidget,{style}"
        return "class:ipywidget"


class CheckboxModel(ToggleableIpyWidgetComm):
    """A checkbox ipywidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the checkbox ipywidget."""
        checkbox = Checkbox(
            text=self.data["state"].get("description", ""),
            on_click=self.value_changed,
            selected=self.data["state"]["value"],
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(
                checkbox,
            ),
            setters={"value": partial(setattr, checkbox, "selected")},
        )


class ValidModel(ToggleableIpyWidgetComm):
    """A validity indicator ipywidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the validity ipywidget."""
        checkbox = Checkbox(
            on_click=self.value_changed,
            selected=self.data["state"].get("value", False),
            prefix=("❌", "✔️"),
            style="class:valid",
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    checkbox,
                    label=lambda: self.data["state"].get("description", ""),
                    style="class:ipywidget",
                ),
            ),
            setters={"value": partial(setattr, checkbox, "selected")},
        )


class SelectableIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    """Base class for selectable ipywidgets."""

    def update_index(self, container: SelectableWidget) -> None:
        """Send a ``comm_message`` updating the selected index when it changes."""
        self.set_state("index", container.index)


class DropdownModel(SelectableIpyWidgetComm):
    """An ipywidget allowing an item to be selected using a drop-down menu."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the drop-down widget."""
        dropdown = Dropdown(
            options=self.data["state"].get("_options_labels", []),
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:ipywidget",
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=dropdown,
                    label=lambda: self.data["state"].get("description", ""),
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, dropdown, "index"),
                "_options_labels": partial(setattr, dropdown, "options"),
            },
        )


class RadioButtonsModel(SelectableIpyWidgetComm):
    """An ipywidget allowing an item to be selected using radio buttons."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the radio-buttons widget."""
        select = Select(
            options=self.data["state"].get("_options_labels", []),
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:ipywidget,radio-buttons",
            prefix=("○", "◉"),
            multiple=False,
            border=None,
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
            rows=None,
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=select,
                    label=lambda: self.data["state"].get("description", ""),
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, select, "index"),
                "_options_labels": partial(setattr, select, "options"),
            },
        )


class SelectModel(SelectableIpyWidgetComm):
    """An ipywidget allowing a value to be selected from a list of options."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the select widget."""
        select = Select(
            options=self.data["state"].get("_options_labels", []),
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:select",
            multiple=False,
            rows=self.data["state"].get("rows", 5),
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=select,
                    label=lambda: self.data["state"].get("description", ""),
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, select, "index"),
                "_options_labels": partial(setattr, select, "options"),
                "rows": partial(setattr, select, "rows"),
            },
        )


class SelectMultipleModel(IpyWidgetComm):
    """An ipywidget allowing one or more value to be selected from a list of options."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the multiple select widget."""
        select = Select(
            options=self.data["state"].get("_options_labels", []),
            indices=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:select",
            multiple=True,
            rows=self.data["state"]["rows"],
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=select,
                    label=lambda: self.data["state"].get("description", ""),
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, select, "indices"),
                "_options_labels": partial(setattr, select, "options"),
                "rows": partial(setattr, select, "rows"),
            },
        )

    def update_index(self, container: SelectableWidget) -> None:
        """Send a ``comm_message`` updating the selected index when it changes."""
        self.set_state("index", container.indices)


class SelectionSliderModel(SliderIpyWidgetComm):
    """A slider ipywidget where one of a list of options can be selected."""

    @property
    def options(self) -> list[str]:
        """Return a list of the available options."""
        return self.data["state"].get("_options_labels", [])

    @property
    def indices(self) -> list[int]:
        """Return the selected index as a list."""
        return [self.data["state"]["index"]]

    def update_value(self, slider: SelectableWidget) -> None:
        """Send a ``comm_message`` updating the selected index when it changes."""
        self.set_state("index", slider.index)

    def set_value(self, slider: Slider, index: int) -> None:
        """Set the selected index on the selection slider when the value changes."""
        self.sync = False
        slider.control.set_index(ab=index)
        self.sync = True


class SelectionRangeSliderModel(SliderIpyWidgetComm):
    """A slider ipywidget where one or more of a list of options can be selected."""

    @property
    def options(self) -> list[str]:
        """Return a list of the available options."""
        return self.data["state"].get("_options_labels", [])

    @property
    def indices(self) -> list[int]:
        """Return a list of the selected indices."""
        return self.data["state"]["index"]

    def update_value(self, slider: SelectableWidget) -> None:
        """Send a ``comm_message`` updating the selected indices when they change."""
        self.set_state("index", slider.indices)

    def set_value(self, slider: Slider, indices: tuple[int, int]) -> None:
        """Set the selected indices on the selection slider when the value changes."""
        self.sync = False
        for i, index in enumerate(indices):
            slider.control.set_index(handle=i, ab=index)
        self.sync = True


class ToggleButtonsModel(IpyWidgetComm):
    """An ipywidget where a single value can be selected using togglable buttons."""

    def get_label(self, index: int) -> AnyFormattedText:
        """Return the label for each toggle button (optionally including the icon)."""
        label = str(self.data["state"].get("_options_labels", [])[index])
        if index < len(self.data["state"].get("icons", [])) and (
            icon := self.data["state"]["icons"][index]
        ):
            from euporie.core.reference import FA_ICONS

            label = f"{FA_ICONS.get(icon, '#')} {label}"
        return label

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the toggle button widget."""
        options = self.data["state"].get("_options_labels", [])
        buttons = ToggleButtons(
            options=options,
            labels=[partial(self.get_label, i) for i in range(len(options))],
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style=self.button_style,
            multiple=False,
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    buttons,
                    label=lambda: self.data["state"].get("description", ""),
                    style="class:ipywidget",
                )
            ),
            setters={
                "_options_labels": lambda x: self.set_options(buttons),
                "index": partial(setattr, buttons, "index"),
            },
        )

    def set_options(self, buttons: ToggleButtons) -> None:
        """Set the list of selectable options in the toggle buttons."""
        options = self.data["state"].get("_options_labels", [])
        buttons.options = options
        # Update the button label functions in case the number of options has changed
        buttons.labels = [partial(self.get_label, i) for i in range(len(options))]

    def button_style(self) -> str:
        """Convert the ipywidget button_style to a prompt_toolkit style string."""
        if style := self.data["state"].get("button_style", ""):
            return f"class:ipywidget,{style}"
        return "class:ipywidget"

    def update_index(self, container: SelectableWidget) -> None:
        """Set the selected index be sending a comm update message."""
        self.set_state("index", container.index)


class ComboboxModel(TextBoxIpyWidgetComm):
    """A combobox input widget."""

    def normalize(self, x: str) -> str | None:
        """Enure that the entered text matches a permitted option, if required."""
        if self.data["state"].get("ensure_option", False):
            if x in self.data["state"].get("options", []):
                return x
            return None
        else:
            return x


class LabelModel(IpyWidgetComm):
    """A label ipwidget."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the Label widget."""
        label = Label(lambda: self.data["state"].get("value", ""))
        return CommView(label)


class HTMLModel(IpyWidgetComm):
    """A label ipywidget which displays HTML."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the HTML widget."""
        from euporie.core.convert.datum import Datum
        from euporie.core.widgets.display import Display

        html = Display(
            Datum(data=self.data["state"].get("value", ""), format="html"),
            dont_extend_width=True,
        )
        return CommView(
            Box(
                html,
                padding_left=0,
                padding_right=0,
            ),
            setters={
                "value": lambda data: setattr(
                    html, "datum", Datum(data, format="html")
                ),
            },
        )


class HTMLMathModel(HTMLModel):
    """Alia for :class:`HTMLModel`, which can render maths."""


class ImageModel(IpyWidgetComm):
    """A ipywidget which displays an image."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the image widget."""
        from euporie.core.convert.datum import Datum
        from euporie.core.widgets.display import Display

        display = Display(
            Datum(
                data=self.data["state"].get("value", b""),
                format="png",
                px=int(self.data["state"].get("width", 0)),
                py=int(self.data["state"].get("height", 0)),
            )
        )
        box = Box(
            display,
            padding_left=0,
            padding_right=0,
        )

        return CommView(
            box,
            setters={
                "value": lambda data: setattr(
                    display, "datum", Datum(data, format="html")
                ),
                "width": lambda x: setattr(display, "px", int(x)),
                "height": lambda y: setattr(display, "py", int(y)),
            },
        )


class DatePickerModel(TextBoxIpyWidgetComm):
    """A date-picker ipywidget."""

    def normalize(self, x: str) -> dict[str, int] | None:
        """Attempt to convert entered text to the internal date representation."""
        if not x:
            return None
        try:
            value = datetime.strptime(x, "%Y-%m-%d").date()
        except ValueError:
            return None
        else:
            return {
                "year": value.year,
                "month": value.month - 1,
                "date": value.day,
            }

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the date-picker widget."""
        comm_view = super().create_view(parent)
        # Wrap the standard value setter to parse the date objects
        value_cb = comm_view.setters["value"]
        comm_view.setters["value"] = partial(
            lambda x: value_cb(self.parse_date(x).strftime("%Y-%m-%d"))
        )
        return comm_view

    def value(self) -> str:
        """Return the text to display in the widget's text area."""
        value = self.data["state"].get("value")
        if value:
            return self.parse_date(value).strftime("%Y-%m-%d")
        else:
            return ""

    def parse_date(self, value: dict[str, int]) -> date:
        """Convert the internal date representation to a python date."""
        return date(value["year"], value["month"] + 1, value["date"])


class ColorPickerModel(TextBoxIpyWidgetComm):
    """A color picker ipywidget."""

    _hex_pattern = re.compile(
        r"#(?:[a-fA-F0-9]{3}(?:[a-fA-F0-9]{3})?|[a-fA-F0-9]{4}(?:[a-fA-F0-9]{4})?)$"
    )

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the color-picker widget."""
        text = Text(
            text=self.value(),
            options=lambda: self.data["state"].get("options", []),
            on_text_changed=self.update_value,
            validation=self.validation,
            height=self.data["state"].get("rows") or self.default_rows,
            multiline=self.multiline,
            placeholder=self.data.get("state", {}).get("placeholder"),
            show_borders=DiBool(False, False, False, False),
            input_processors=[BeforeInput(" ")],
            disabled=Condition(lambda: self.data["state"].get("disabled", False)),
            style="class:ipywidget",
        )

        container = FocusedStyle(
            LabelledWidget(
                body=Border(
                    VSplit(
                        [
                            Swatch(
                                self.format_color,
                                show_borders=DiBool(False, False, False, False),
                                style=text.border_style,
                            ),
                            text,
                        ],
                    ),
                    border=InsetGrid,
                    style=lambda: f"{text.border_style()}",
                ),
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            )
        )
        return CommView(
            container,
            setters={
                "value": lambda x: setattr(text.buffer, "text", str(x)),
                "rows": partial(setattr, text.window, "height"),
                "placeholder": partial(setattr, text, "placeholder"),
            },
        )

    def format_color(self) -> str:
        """Format a color as a hex code for display."""
        from euporie.core.reference import NAMED_COLORS

        # TODO - blend alpha colors with the terminal background
        value = self.value()
        if value in NAMED_COLORS:
            value = NAMED_COLORS[value]
        elif 4 <= len(value) < 7:
            value = f"#{value[1] * 2}{value[2] * 2}{value[3] * 2}"
        else:
            value = value[:7]
        return value

    def normalize(self, x: str) -> str | None:
        """Return the color string if it is recognised as an allowed color."""
        from euporie.core.reference import NAMED_COLORS

        if x in NAMED_COLORS or self._hex_pattern.match(x) is not None:
            return x
        else:
            return None


def open_comm_ipywidgets(
    comm_container: KernelTab,
    comm_id: str,
    data: dict,
    buffers: Sequence[memoryview | bytearray | bytes],
) -> IpyWidgetComm:
    """Create a new Comm for an :py:mod:`ipywidgets` widget.

    The relevant widget model is selected based on the model name given in the
    ``comm_open`` message data.

    Args:
        comm_container: The notebook this Comm belongs to
        comm_id: The ID of the Comm
        data: The data field from the ``comm_open`` message
        buffers: The buffers field from the ``comm_open`` message

    Returns:
        The initialized widget Comm object.
    """
    model_name = data.get("state", {}).get("_model_name")
    return WIDGET_MODELS.get(model_name, UnimplementedModel)(
        comm_container, comm_id, data, buffers
    )


# Load ``ipympl`` widget
from . import ipympl as ipympl  # noqa: E402
