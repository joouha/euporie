"""Defines representations for :py:class:`ipywidget` comms."""

import logging
import re
from abc import ABCMeta, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.widgets.base import Box

from euporie.border import BorderVisibility
from euporie.comm.base import Comm, CommView
from euporie.widgets.cell_outputs import CellOutputArea
from euporie.widgets.decor import FocusedStyle
from euporie.widgets.display import Display
from euporie.widgets.inputs import (
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
from euporie.widgets.layout import AccordionSplit, ReferencedSplit, TabbedSplit

if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Dict,
        Iterable,
        List,
        Optional,
        Sequence,
        Tuple,
        Type,
        Union,
    )

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.layout.containers import AnyContainer, _Split

    from euporie.kernel import MsgCallbacks
    from euporie.widgets.cell import Cell
    from euporie.widgets.inputs import SelectableWidget, ToggleableWidget
    from euporie.widgets.layout import StackedSplit

    JSONType = Union[str, int, float, bool, None, Dict[str, Any], Iterable[Any]]

log = logging.getLogger(__name__)


class IpyWidgetComm(Comm, metaclass=ABCMeta):
    target_name = "jupyter.widget"

    def __init__(
        self, nb, comm_id: "str", data: "dict", buffers: "Sequence[bytes]"
    ) -> "None":
        super().__init__(nb, comm_id, data, buffers)
        self.sync = True

    def set_state(self, key: "str", value: "JSONType") -> "None":
        if self.sync:
            self.data.setdefault("state", {})[key] = value
            self.nb.kernel.kc_comm(
                comm_id=self.comm_id, data={"method": "update", "state": {key: value}}
            )
            self.update_views({key: value})

    def process_data(self, data, buffers: "Sequence[bytes]") -> "None":
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
    def create_view(self, cell: "Cell") -> "CommView":
        ...


class UnimplementedModel(IpyWidgetComm):
    def create_view(self, cell: "Cell") -> "CommView":
        return CommView(Display("[Widget not implemented]", format_="ansi"))


class OutputModel(IpyWidgetComm):
    """An Output widget."""

    model_name = "OutputModel"

    def __init__(
        self, nb, comm_id: "str", data: "dict", buffers: "Sequence[bytes]"
    ) -> "None":
        super().__init__(nb, comm_id, data, buffers)
        self.clear_output_wait = False
        self.prev_msg_id = ""
        self.original_callbacks: "MsgCallbacks" = {}
        self.callbacks: "MsgCallbacks" = {
            "add_output": self.add_output,
            "clear_output": self.clear_output,
        }

    def create_view(self, cell: "Cell") -> "CommView":
        container = CellOutputArea(self.data.get("state", {}).get("outputs", []), cell)
        return CommView(
            container,
            {"outputs": partial(setattr, container, "json")},
        )

    def add_output(self, json) -> "None":
        if self.clear_output_wait:
            self.set_state("outputs", [json])
        else:
            self.set_state("outputs", [*self.data["state"]["outputs"], json])

    def clear_output(self, wait=False) -> "None":
        if wait:
            self.clear_output_wait = True
        else:
            self.clear_output_wait = False
            self.set_state("outputs", [])

    def process_data(self, data, buffers: "Sequence[bytes]"):
        if data.get("method") == "update":
            changes = data.get("state", {})

            for key, value in data.get("state", {}).items():
                # Replace the kernel callbacks of the given message ID
                if key == "msg_id":
                    if value:
                        # Replace the message's callbacks
                        self.original_callbacks = self.nb.kernel.msg_id_callbacks[value]
                        del self.nb.kernel.msg_id_callbacks[value]
                        self.nb.kernel.msg_id_callbacks[value].update(self.callbacks)
                    else:
                        # Restore the message's callbacks
                        if self.original_callbacks:
                            self.nb.kernel.msg_id_callbacks[
                                self.prev_msg_id
                            ] = self.original_callbacks
                            self.original_callbacks = {}
                        else:
                            del self.nb.kernel.msg_id_callbacks[self.prev_msg_id]
                    self.prev_msg_id = value

            self.data.setdefault("state", {}).update(changes)
            self.update_views(changes)


class LayoutIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    def render_children(self, models, cell: "Cell") -> "List[AnyContainer]":
        return [
            self.nb.comms[
                ipy_model[ipy_model.startswith("IPY_MODEL_") and len("IPY_MODEL_") :]
            ].new_view(cell)
            for ipy_model in models
        ]

    def box_style(self):
        if style := self.data["state"]["box_style"]:
            return f"class:{style}"
        return "class:default"


class BoxModel(LayoutIpyWidgetComm):
    """A box layout (basically the same a HBox)."""

    padding = 1
    Split: "Type[_Split]" = VSplit

    def create_view(self, cell: "Cell"):
        container = ReferencedSplit(
            self.Split,
            self.render_children(self.data["state"]["children"], cell),
            padding=self.padding,
            style=self.box_style,
        )

        def set_children(models) -> "None":
            container.children = self.render_children(models, cell)

        return CommView(
            container,
            {"children": set_children},
        )


class HBoxModel(BoxModel):
    """A horizontal layout."""


class VBoxModel(BoxModel):
    """A vertical layout."""

    Split = HSplit
    padding = 0


class TabModel(LayoutIpyWidgetComm):
    """A tabbed layout."""

    def create_view(self, cell: "Cell"):
        children = self.data["state"]["children"]
        container = TabbedSplit(
            children=self.render_children(children, cell),
            titles=list(self.data["state"].get("_titles", {}).values())
            or [""] * len(children),
            active=self.data["state"].get("selected_index"),
            style=self.box_style,
            on_change=self.update_index,
        )

        def set_children(models) -> "None":
            container.children = self.render_children(models, cell)

        def set_titles(new) -> "None":
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

    def update_index(self, container: "StackedSplit") -> "None":
        self.set_state("selected_index", container.active)


class AccordionModel(LayoutIpyWidgetComm):
    """An accoridon layout."""

    def create_view(self, cell: "Cell"):
        children = self.data["state"]["children"]
        container = AccordionSplit(
            children=self.render_children(children, cell),
            titles=list(self.data["state"].get("_titles", {}).values())
            or [""] * len(children),
            active=self.data["state"].get("selected_index"),
            style=self.box_style,
            on_change=self.update_index,
        )

        def set_children(models) -> "None":
            container.children = self.render_children(models, cell)

        def set_titles(new) -> "None":
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

    def update_index(self, container: "StackedSplit") -> "None":
        self.set_state("selected_index", container.active)


class ButtonModel(IpyWidgetComm):
    """A Button widget."""

    def create_view(self, cell: "Cell"):
        button = Button(
            text=self.data["state"].get("description", ""),
            on_click=self.click,
            style=self.button_style,
        )
        return CommView(
            FocusedStyle(button),
            setters={"description": partial(setattr, button, "text")},
        )

    def button_style(self):
        if style := self.data["state"]["button_style"]:
            return f"class:{style}"
        return ""

    def click(self, button: "Button") -> "None":
        self.nb.kernel.kc_comm(
            comm_id=self.comm_id,
            data={"method": "custom", "content": {"event": "click"}},
        )


class TextBoxIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    default_rows = 1
    multiline = False

    def validation(self, x: "Any") -> "bool":
        return self.normalize(x) is not None

    def normalize(self, x):
        return x

    def value(self) -> "str":
        return self.data["state"].get("value", "")

    def create_view(self, cell: "Cell"):
        text = Text(
            text=self.value(),
            options=lambda: self.data["state"].get("options", []),
            on_text_changed=self.update_value,
            validation=self.validation,
            height=self.data["state"].get("rows") or self.default_rows,
            multiline=self.multiline,
            placeholder=self.data.get("state", {}).get("placeholder"),
        )
        container = FocusedStyle(
            LabelledWidget(
                body=text,
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            )
        )
        return CommView(
            container,
            setters={
                "value": lambda x: setattr(text.buffer, "text", str(x)),
                "rows": partial(setattr, text.text_area.window, "height"),
                "placeholder": partial(setattr, text, "placeholder"),
            },
        )

    def update_value(self, buffer: "Buffer") -> "None":
        if (value := self.normalize(buffer.text)) is not None:
            self.set_state("value", value)


class TextModel(TextBoxIpyWidgetComm):
    """A text input widget."""


class TextareaModel(TextBoxIpyWidgetComm):
    """A text input widget."""

    default_rows = 3
    multiline = True


class IntOptionsMixin:
    data: "Dict[str, Any]"

    def normalize(self, x: "Any") -> "Optional[int]":
        try:
            value = int(x)
        except ValueError:
            return None
        else:
            if minimum := self.data.get("state", {}).get("min"):
                if value < minimum:
                    return None
            if maximum := self.data.get("state", {}).get("max"):
                if maximum < value:
                    return None
            return value

    @property
    def options(self) -> "List[int]":
        return list(
            range(
                self.data["state"]["min"],
                self.data["state"]["max"] + self.data["state"]["step"],
                self.data["state"]["step"],
            )
        )


class FloatOptionsMixin:
    data: "Dict[str, Any]"

    def normalize(self, x: "Any") -> "Optional[float]":
        try:
            value = float(x)
        except ValueError:
            return None
        else:
            if minimum := self.data.get("state", {}).get("min"):
                if value < minimum:
                    return None
            if maximum := self.data.get("state", {}).get("max"):
                if maximum < value:
                    return None
            return value

    @property
    def options(self) -> "List[Decimal]":
        start = Decimal(str(self.data["state"]["min"]))
        stop = Decimal(str(self.data["state"]["max"] + self.data["state"]["step"]))
        step = Decimal(str(self.data["state"]["step"]))
        return [start + step * i for i in range(int((stop - start) / step))]


class FloatLogOptionsMixin(FloatOptionsMixin):
    data: "Dict[str, Any]"

    @property
    def options(self) -> "List[Decimal]":
        base = Decimal(str(self.data["state"]["base"]))
        start = Decimal(str(self.data["state"]["min"]))
        stop = Decimal(str(self.data["state"]["max"] + self.data["state"]["step"]))
        step = Decimal(str(self.data["state"]["step"]))
        return [base ** (start + step * i) for i in range(int((stop - start) / step))]


class SliderIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    def normalize(self, x):
        return x

    @property
    @abstractmethod
    def options(self) -> "List":
        return []

    def create_view(self, cell: "Cell"):
        vertical = Condition(lambda: self.data["state"]["orientation"] == "vertical")
        options = self.options
        slider = Slider(
            options=options,
            indices=self.indices,
            multiple=False,
            on_change=self.update_value,
            style="class:ipywidget",
            arrows=(
                lambda: "⮟" if vertical() else "⮜",
                lambda: "⮝" if vertical() else "⮞",
            ),
            show_arrows=True,
            vertical=Condition(lambda: self.data["state"]["orientation"] == "vertical"),
        )

        labelled = LabelledWidget(
            body=slider,
            label=lambda: self.data["state"].get("description", ""),
            height=1,
            style="class:ipywidget",
            vertical=Condition(lambda: self.data["state"]["orientation"] == "vertical"),
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
    def indices(self) -> "List[Any]":
        return [self.options.index(value) for value in [self.data["state"]["value"]]]

    def update_value(self, container: "SelectableWidget") -> "None":
        if index := container.index is not None:
            if (value := self.normalize(container.options[index])) is not None:
                self.set_state("value", value)

    def set_value(self, slider: "Slider", value: "Any") -> "None":
        if value in slider.options:
            slider.index = slider.options.index(value)
            slider.value_changed()


class RangeSliderIpyWidgetComm(SliderIpyWidgetComm, metaclass=ABCMeta):
    @property
    def indices(self) -> "List[int]":
        return [self.options.index(value) for value in self.data["state"]["value"]]

    def update_value(self, slider: "SelectableWidget") -> "None":
        self.set_state(
            "value", [self.normalize(slider.options[index]) for index in slider.indices]
        )

    def set_value(self, slider: "Slider", values: "Any") -> "None":
        if all(value in slider.options for value in values):
            slider.indices = [slider.options.index(value) for value in values]
            slider.value_changed()


class IntSliderModel(IntOptionsMixin, SliderIpyWidgetComm):
    """"""


class FloatSliderModel(FloatOptionsMixin, SliderIpyWidgetComm):
    """"""


class FloatLogSliderModel(FloatLogOptionsMixin, SliderIpyWidgetComm):
    """"""


class IntRangeSliderModel(IntOptionsMixin, RangeSliderIpyWidgetComm):
    """"""


class FloatRangeSliderModel(FloatOptionsMixin, RangeSliderIpyWidgetComm):
    """"""


class NumberTextBoxIpyWidgetComm(TextBoxIpyWidgetComm, metaclass=ABCMeta):
    def create_view(self, cell: "Cell"):
        text = Text(
            text=self.data.get("state", {}).get("value", ""),
            on_text_changed=self.update_value,
            validation=self.validation,
        )
        container = FocusedStyle(
            LabelledWidget(
                body=ReferencedSplit(
                    VSplit,
                    [
                        text,
                        Button(
                            "-",
                            show_borders=BorderVisibility(True, False, True, True),
                            on_click=self.decr,
                        ),
                        Button(
                            "+",
                            show_borders=BorderVisibility(True, True, True, False),
                            on_click=self.incr,
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

    def incr(self, button: "Button") -> "None":
        value = Decimal(str(self.data["state"]["value"]))
        step = Decimal(str(self.data["state"].get("step", 1) or 1))
        if (new := self.normalize(value + step)) is not None:
            self.set_state("value", new)

    def decr(self, button: "Button") -> "None":
        value = Decimal(str(self.data["state"]["value"]))
        step = Decimal(str(self.data["state"].get("step", 1) or 1))
        if (new := self.normalize(value - step)) is not None:
            self.set_state("value", new)


class IntTextModel(IntOptionsMixin, NumberTextBoxIpyWidgetComm):
    """An integer textbox widget."""


class BoundedIntTextModel(IntOptionsMixin, NumberTextBoxIpyWidgetComm):
    """An integer textbox widget with upper and lower bounds."""


class FloatTextModel(FloatOptionsMixin, NumberTextBoxIpyWidgetComm):
    """A float textbox widget."""


class BoundedFloatTextModel(FloatOptionsMixin, NumberTextBoxIpyWidgetComm):
    """An float textbox widget with upper and lower bounds."""


class ProgressIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    def create_view(self, cell: "Cell") -> "CommView":
        vertical = Condition(lambda: self.data["state"]["orientation"] == "vertical")
        progress = Progress(
            start=self.data["state"]["min"],
            stop=self.data["state"]["max"],
            step=self.data["state"].get("step", 1),
            value=self.data["state"]["value"],
            vertical=vertical,
            style=self.bar_style,
        )
        container = FocusedStyle(
            LabelledWidget(
                body=progress,
                vertical=vertical,
                label=lambda: self.data.get("state", {}).get("description", ""),
                height=1,
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

    def bar_style(self):
        if style := self.data["state"]["bar_style"]:
            return f"class:{style}"
        return ""


class IntProgressModel(IntOptionsMixin, ProgressIpyWidgetComm):
    """"""


class FloatProgressModel(FloatOptionsMixin, ProgressIpyWidgetComm):
    """"""


class ToggleableIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    def normalize(self, x: "Any") -> "Optional[float]":
        try:
            value = bool(x)
        except ValueError:
            return None
        else:
            return value

    def value_changed(self, button: "ToggleableWidget") -> "None":
        if (value := self.normalize(button.selected)) is not None:
            self.set_state("value", value)


class ToggleButtonModel(ToggleableIpyWidgetComm):
    """A toggleable button widget."""

    def create_view(self, cell: "Cell"):
        button = ToggleButton(
            text=self.data["state"].get("description", ""),
            on_click=self.value_changed,
            selected=self.data["state"]["value"],
            style=self.button_style,
        )
        return CommView(
            FocusedStyle(
                button,
            ),
            setters={"value": partial(setattr, button, "selected")},
        )

    def button_style(self):
        if style := self.data["state"]["button_style"]:
            return f"class:{style}"
        return ""


class CheckboxModel(ToggleableIpyWidgetComm):
    """A checkbox widget."""

    def create_view(self, cell: "Cell"):
        checkbox = Checkbox(
            text=self.data["state"].get("description", ""),
            on_click=self.value_changed,
            selected=self.data["state"]["value"],
        )
        return CommView(
            FocusedStyle(
                checkbox,
            ),
            setters={"value": partial(setattr, checkbox, "selected")},
        )


class ValidModel(ToggleableIpyWidgetComm):
    """A validity indicator widget."""

    def create_view(self, cell: "Cell"):
        checkbox = Checkbox(
            on_click=self.value_changed,
            selected=self.data["state"]["value"],
            prefix=("❌", "✔️"),
            style="class:valid",
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    checkbox, label=lambda: self.data["state"].get("description", "")
                ),
                style="class:ipywidget",
            ),
            setters={"value": partial(setattr, checkbox, "selected")},
        )


class SelectableIpyWidgetComm(IpyWidgetComm, metaclass=ABCMeta):
    def update_index(self, container: "SelectableWidget") -> "None":
        self.set_state("index", container.index)


class DropdownModel(SelectableIpyWidgetComm):
    def create_view(self, cell: "Cell"):
        dropdown = Dropdown(
            options=self.data["state"]["_options_labels"],
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:ipywidget",
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=dropdown,
                    label=lambda: self.data["state"].get("description", ""),
                    height=1,
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, dropdown, "index"),
                "_options_labels": partial(setattr, dropdown, "options"),
            },
        )


class RadioButtonsModel(SelectableIpyWidgetComm):
    def create_view(self, cell: "Cell"):
        select = Select(
            options=self.data["state"]["_options_labels"],
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:radio-buttons",
            prefix=("○", "◉"),
            multiple=False,
            border=None,
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=select,
                    label=lambda: self.data["state"].get("description", ""),
                    height=1,
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, select, "index"),
                "_options_labels": partial(setattr, select, "options"),
            },
        )


class SelectModel(SelectableIpyWidgetComm):
    def create_view(self, cell: "Cell"):
        select = Select(
            options=self.data["state"]["_options_labels"],
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:select,face",
            multiple=False,
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=select,
                    label=lambda: self.data["state"].get("description", ""),
                    height=1,
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, select, "index"),
                "_options_labels": partial(setattr, select, "options"),
            },
        )


class SelectMultipleModel(IpyWidgetComm):
    def create_view(self, cell: "Cell"):
        select = Select(
            options=self.data["state"]["_options_labels"],
            indices=self.data["state"]["index"],
            on_change=self.update_index,
            style="class:select,face",
            multiple=True,
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    body=select,
                    label=lambda: self.data["state"].get("description", ""),
                    height=1,
                    style="class:ipywidget",
                )
            ),
            setters={
                "index": partial(setattr, select, "indices"),
                "_options_labels": partial(setattr, select, "options"),
            },
        )

    def update_index(self, container: "SelectableWidget") -> "None":
        self.set_state("index", container.indices)


class SelectionSliderModel(SliderIpyWidgetComm):
    @property
    def options(self) -> "List[str]":
        return self.data["state"]["_options_labels"]

    @property
    def indices(self) -> "List[int]":
        return [self.data["state"]["index"]]

    def update_value(self, slider: "SelectableWidget") -> "None":
        self.set_state("index", slider.index)

    def set_value(self, slider: "Slider", index: "int") -> "None":
        self.sync = False
        slider.control.set_index(ab=index)
        self.sync = True


class SelectionRangeSliderModel(RangeSliderIpyWidgetComm):
    @property
    def options(self) -> "List[str]":
        return self.data["state"]["_options_labels"]

    @property
    def indices(self) -> "List[int]":
        return self.data["state"]["index"]

    def update_value(self, slider: "SelectableWidget") -> "None":
        self.set_state("index", slider.indices)

    def set_value(self, slider: "Slider", indices: "Tuple[int, int]") -> "None":
        self.sync = False
        for i, index in enumerate(indices):
            slider.control.set_index(handle=i, ab=index)
        self.sync = True


class ToggleButtonsModel(IpyWidgetComm):
    def create_view(self, cell: "Cell"):
        buttons = ToggleButtons(
            options=self.data["state"]["_options_labels"],
            index=self.data["state"]["index"],
            on_change=self.update_index,
            style=self.button_style,
            multiple=False,
        )
        return CommView(
            FocusedStyle(
                LabelledWidget(
                    buttons,
                    label=lambda: self.data["state"].get("description", ""),
                    height=1,
                    style="class:ipywidget",
                )
            ),
            setters={
                "_options_labels": partial(setattr, buttons, "options"),
                "index": partial(setattr, buttons, "index"),
            },
        )

    def button_style(self):
        if style := self.data["state"]["button_style"]:
            return f"class:{style}"
        return ""

    def update_index(self, container: "SelectableWidget") -> "None":
        self.set_state("index", container.index)


class ComboboxModel(TextBoxIpyWidgetComm):
    """A combobox input widget."""

    def normalize(self, x: "str") -> "Optional[str]":
        if self.data["state"].get("ensure_option", False):
            if x in self.data["state"].get("options", []):
                return x
            return None
        else:
            return x


class LabelModel(IpyWidgetComm):
    def create_view(self, cell: "Cell") -> "CommView":
        label = Label(lambda: self.data["state"].get("value", ""))
        return CommView(label)


class HTMLModel(IpyWidgetComm):
    def create_view(self, cell: "Cell"):
        html = Display(
            data=self.data["state"].get("value", ""),
            format_="html",
        )
        return CommView(
            Box(
                html,
                padding_left=0,
                padding_right=0,
            ),
            setters={
                "value": partial(setattr, html, "data"),
            },
        )


class HTMLMathModel(HTMLModel):
    """Alias for :class:`HTMLModel`, which can render maths."""


class ImageModel(IpyWidgetComm):
    def create_view(self, cell: "Cell"):
        image = Box(
            Display(
                data=self.data["state"]["value"],
                format_="png",
                px=int(self.data["state"].get("width", 0)) or None,
                py=int(self.data["state"].get("height", 0)) or None,
            ),
            padding_left=0,
            padding_right=0,
        )

        return CommView(
            image,
            setters={
                "value": partial(setattr, image, "data"),
                "width": lambda x: partial(setattr, image, "px")(int(x)),
                "height": lambda x: partial(setattr, image, "py")(int(x)),
            },
        )


class DatePickerModel(TextBoxIpyWidgetComm):
    def normalize(self, x: "str") -> "Optional[Dict[str, int]]":
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

    def create_view(self, cell: "Cell"):
        comm_view = super().create_view(cell)
        # Wrap the standard value setter to parse the date objects
        value_cb = comm_view.setters["value"]
        comm_view.setters["value"] = partial(
            lambda x: value_cb(self.parse_date(x).strftime("%Y-%m-%d"))
        )
        return comm_view

    def value(self) -> "str":
        value = self.data["state"].get("value")
        if value:
            return self.parse_date(value).strftime("%Y-%m-%d")
        else:
            return ""

    def parse_date(self, value) -> "date":
        return date(value["year"], value["month"] + 1, value["date"])


class ColorPickerModel(TextBoxIpyWidgetComm):
    """"""

    _named_colors = {
        "aliceblue": "#f0f8ff",
        "antiquewhite": "#faebd7",
        "aqua": "#00ffff",
        "aquamarine": "#7fffd4",
        "azure": "#f0ffff",
        "beige": "#f5f5dc",
        "bisque": "#ffe4c4",
        "black": "#000000",
        "blanchedalmond": "#ffebcd",
        "blue": "#0000ff",
        "blueviolet": "#8a2be2",
        "brown": "#a52a2a",
        "burlywood": "#deb887",
        "cadetblue": "#5f9ea0",
        "chartreuse": "#7fff00",
        "chocolate": "#d2691e",
        "coral": "#ff7f50",
        "cornflowerblue": "#6495ed",
        "cornsilk": "#fff8dc",
        "crimson": "#dc143c",
        "cyan": "#00ffff",
        "darkblue": "#00008b",
        "darkcyan": "#008b8b",
        "darkgoldenrod": "#b8860b",
        "darkgray": "#a9a9a9",
        "darkgreen": "#006400",
        "darkkhaki": "#bdb76b",
        "darkmagenta": "#8b008b",
        "darkolivegreen": "#556b2f",
        "darkorange": "#ff8c00",
        "darkorchid": "#9932cc",
        "darkred": "#8b0000",
        "darksalmon": "#e9967a",
        "darkseagreen": "#8fbc8b",
        "darkslateblue": "#483d8b",
        "darkslategray": "#2f4f4f",
        "darkturquoise": "#00ced1",
        "darkviolet": "#9400d3",
        "deeppink": "#ff1493",
        "deepskyblue": "#00bfff",
        "dimgray": "#696969",
        "dodgerblue": "#1e90ff",
        "firebrick": "#b22222",
        "floralwhite": "#fffaf0",
        "forestgreen": "#228b22",
        "fuchsia": "#ff00ff",
        "gainsboro": "#dcdcdc",
        "ghostwhite": "#f8f8ff",
        "gold": "#ffd700",
        "goldenrod": "#daa520",
        "gray": "#808080",
        "green": "#008000",
        "greenyellow": "#adff2f",
        "honeydew": "#f0fff0",
        "hotpink": "#ff69b4",
        "indianred": "#cd5c5c",
        "indigo": "#4b0082",
        "ivory": "#fffff0",
        "khaki": "#f0e68c",
        "lavender": "#e6e6fa",
        "lavenderblush": "#fff0f5",
        "lawngreen": "#7cfc00",
        "lemonchiffon": "#fffacd",
        "lightblue": "#add8e6",
        "lightcoral": "#f08080",
        "lightcyan": "#e0ffff",
        "lightgoldenrodyellow": "#fafad2",
        "lightgray": "#d3d3d3",
        "lightgreen": "#90ee90",
        "lightpink": "#ffb6c1",
        "lightsalmon": "#ffa07a",
        "lightseagreen": "#20b2aa",
        "lightskyblue": "#87cefa",
        "lightslategray": "#778899",
        "lightsteelblue": "#b0c4de",
        "lightyellow": "#ffffe0",
        "lime": "#00ff00",
        "limegreen": "#32cd32",
        "linen": "#faf0e6",
        "magenta": "#ff00ff",
        "maroon": "#800000",
        "mediumaquamarine": "#66cdaa",
        "mediumblue": "#0000cd",
        "mediumorchid": "#ba55d3",
        "mediumpurple": "#9370db",
        "mediumseagreen": "#3cb371",
        "mediumslateblue": "#7b68ee",
        "mediumspringgreen": "#00fa9a",
        "mediumturquoise": "#48d1cc",
        "mediumvioletred": "#c71585",
        "midnightblue": "#191970",
        "mintcream": "#f5fffa",
        "mistyrose": "#ffe4e1",
        "moccasin": "#ffe4b5",
        "navajowhite": "#ffdead",
        "navy": "#000080",
        "oldlace": "#fdf5e6",
        "olive": "#808000",
        "olivedrab": "#6b8e23",
        "orange": "#ffa500",
        "orangered": "#ff4500",
        "orchid": "#da70d6",
        "palegoldenrod": "#eee8aa",
        "palegreen": "#98fb98",
        "paleturquoise": "#afeeee",
        "palevioletred": "#db7093",
        "papayawhip": "#ffefd5",
        "peachpuff": "#ffdab9",
        "peru": "#cd853f",
        "pink": "#ffc0cb",
        "plum": "#dda0dd",
        "powderblue": "#b0e0e6",
        "purple": "#800080",
        "red": "#ff0000",
        "rosybrown": "#bc8f8f",
        "royalblue": "#4169e1",
        "saddlebrown": "#8b4513",
        "salmon": "#fa8072",
        "sandybrown": "#f4a460",
        "seagreen": "#2e8b57",
        "seashell": "#fff5ee",
        "sienna": "#a0522d",
        "silver": "#c0c0c0",
        "skyblue": "#87ceeb",
        "slateblue": "#6a5acd",
        "slategray": "#708090",
        "snow": "#fffafa",
        "springgreen": "#00ff7f",
        "steelblue": "#4682b4",
        "tan": "#d2b48c",
        "teal": "#008080",
        "thistle": "#d8bfd8",
        "tomato": "#ff6347",
        "transparent": "#ffffff",
        "turquoise": "#40e0d0",
        "violet": "#ee82ee",
        "wheat": "#f5deb3",
        "white": "#ffffff",
        "whitesmoke": "#f5f5f5",
        "yellow": "#ffff00",
        "yellowgreen": "#9acd32",
    }
    _hex_pattern = re.compile(
        r"#(?:[a-fA-F0-9]{3}(?:[a-fA-F0-9]{3})?|[a-fA-F0-9]{4}(?:[a-fA-F0-9]{4})?)$"
    )

    def create_view(self, cell: "Cell"):
        text = Text(
            text=self.value(),
            options=lambda: self.data["state"].get("options", []),
            on_text_changed=self.update_value,
            validation=self.validation,
            height=self.data["state"].get("rows") or self.default_rows,
            multiline=self.multiline,
            placeholder=self.data.get("state", {}).get("placeholder"),
            show_borders=BorderVisibility(True, True, True, False),
            input_processors=[BeforeInput(" ")],
        )

        container = FocusedStyle(
            LabelledWidget(
                body=VSplit(
                    [
                        Swatch(
                            self.format_color,
                            show_borders=BorderVisibility(True, False, True, True),
                        ),
                        text,
                    ],
                ),
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            )
        )
        return CommView(
            container,
            setters={
                "value": lambda x: setattr(text.buffer, "text", str(x)),
                "rows": partial(setattr, text.text_area.window, "height"),
                "placeholder": partial(setattr, text, "placeholder"),
            },
        )

    def format_color(self) -> "str":
        """Formats a color as a hex code for display."""
        # TODO - blend alpha colors with the terminal background
        value = self.value()
        if value in self._named_colors:
            value = self._named_colors[value]
        elif 4 <= len(value) < 7:
            value = f"#{value[1]*2}{value[2]*2}{value[3]*2}"
        else:
            value = value[:7]
        return value

    def normalize(self, x: "str") -> "Optional[str]":
        """Returns the color string if it is recognised as an allowed color."""
        if x in self._named_colors or self._hex_pattern.match(x) is not None:
            return x
        else:
            return None


WIDGET_MODELS = {
    "BoxModel": BoxModel,
    "HBoxModel": HBoxModel,
    "VBoxModel": VBoxModel,
    "OutputModel": OutputModel,
    "ButtonModel": ButtonModel,
    "TextModel": TextModel,
    "TextareaModel": TextareaModel,
    "IntTextModel": IntTextModel,
    "BoundedIntTextModel": BoundedIntTextModel,
    "FloatTextModel": FloatTextModel,
    "BoundedFloatTextModel": BoundedFloatTextModel,
    "IntSliderModel": IntSliderModel,
    "FloatSliderModel": FloatSliderModel,
    "FloatLogSliderModel": FloatLogSliderModel,
    "IntRangeSliderModel": IntRangeSliderModel,
    "FloatRangeSliderModel": FloatRangeSliderModel,
    "IntProgressModel": IntProgressModel,
    "FloatProgressModel": FloatProgressModel,
    "ToggleButtonModel": ToggleButtonModel,
    "CheckboxModel": CheckboxModel,
    "ValidModel": ValidModel,
    "DropdownModel": DropdownModel,
    "RadioButtonsModel": RadioButtonsModel,
    "SelectModel": SelectModel,
    "SelectMultipleModel": SelectMultipleModel,
    "SelectionSliderModel": SelectionSliderModel,
    "SelectionRangeSliderModel": SelectionRangeSliderModel,
    "ToggleButtonsModel": ToggleButtonsModel,
    "ComboboxModel": ComboboxModel,
    "LabelModel": LabelModel,
    "HTMLModel": HTMLModel,
    "HTMLMathModel": HTMLModel,
    "ImageModel": ImageModel,
    "DatePickerModel": DatePickerModel,
    "ColorPickerModel": ColorPickerModel,
    "TabModel": TabModel,
    "AccordionModel": AccordionModel,
}


def open_comm_ipywidgets(nb, comm_id, data, buffers):
    model_name = data.get("state", {}).get("_model_name")
    return WIDGET_MODELS.get(model_name, UnimplementedModel)(nb, comm_id, data, buffers)
