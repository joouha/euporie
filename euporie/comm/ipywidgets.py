import logging
from decimal import Decimal

from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.widgets.base import Box

from euporie.comm.base import Comm
from euporie.widgets.cell_outputs import CellOutputArea
from euporie.widgets.decor import Border, FocusedStyle
from euporie.widgets.display import Display
from euporie.widgets.inputs import (
    Button,
    Checkbox,
    Dropdown,
    LabeledWidget,
    Progress,
    Selection,
    Slider,
    Text,
    ToggleButton,
    WidgetGrid,
)
from euporie.widgets.layout import ReferencedSplit

log = logging.getLogger(__name__)


class JupyterWidget(Comm):
    target_name = "jupyter.widget"

    def __init__(self, nb, comm_id: "str", data: "dict") -> "None":
        super().__init__(nb, comm_id, data)
        self.sync = True

    def set_state(self, key, value):
        if self.sync:
            self.data.setdefault("state", {})[key] = value
            self.nb.kernel.kc_comm(
                comm_id=self.comm_id, data={"method": "update", "state": {key: value}}
            )
            self.update_views()

    def process_data(self, data):
        if data.get("method") == "update":
            self.data["state"].update(data.get("state", {}))
        self.update_views()


class UnimplementedWidget(JupyterWidget):
    def _create_view(self, cell: "Cell"):
        return Display(f"[Widget not implemented]", format_="ansi")


class OutputModel(JupyterWidget):
    """An Output widget."""

    model_name = "OutputModel"

    def __init__(self, nb, comm_id: "str", data: "dict") -> "None":
        super().__init__(nb, comm_id, data)
        self.original_callbacks = {}
        self.clear_output_wait = False

        self.prev_msg_id = ""
        self.callbacks = {
            "add_output": self.add_output,
            "clear_output": self.clear_output,
        }

    def _create_view(self, cell: "Cell"):
        return CellOutputArea(self.data.get("state", {}).get("outputs", []), cell)

    def add_output(self, json):
        if self.clear_output_wait:
            self.set_state("outputs", [json])
        else:
            self.set_state("outputs", [*self.data["state"]["outputs"], json])
        self.update_views()

    def clear_output(self, wait=False):
        if wait:
            self.clear_output_wait = True
        else:
            self.clear_output_wait = False
            self.set_state("outputs", [])
            self.update_views()

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.json = self.data["state"].setdefault("outputs", [])

    def process_data(self, data):
        if data.get("method") == "update":

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

            self.data["state"].update(data.get("state", {}))
        self.update_views()


class LayoutMixin:
    def children(self, cell):
        return [
            self.nb.comms[
                ipy_model[ipy_model.startswith("IPY_MODEL_") and len("IPY_MODEL_") :]
            ].create_view(cell)
            for ipy_model in self.data.get("state", {}).get("children", [])
        ]

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.children = self.children(cell)


class HBoxModel(LayoutMixin, JupyterWidget):
    """A horizontal layout."""

    def _create_view(self, cell: "Cell"):
        return ReferencedSplit(VSplit, self.children(cell), padding=1)


class VBoxModel(LayoutMixin, JupyterWidget):
    """A vertical layout."""

    def _create_view(self, cell: "Cell"):
        return ReferencedSplit(HSplit, self.children(cell), padding=0)


class BoxModel(HBoxModel):
    """Appears to be the same a HBox."""


class ButtonModel(JupyterWidget):
    """A Button widget."""

    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            Box(
                Button(
                    text=self.data["state"].get("description", ""),
                    on_click=self.click,
                ),
                padding_left=0,
                style="class:ipywidget",
            )
        )

    def click(self, button: "Button") -> "None":
        self.nb.kernel.kc_comm(
            comm_id=self.comm_id,
            data={"method": "custom", "content": {"event": "click"}},
        )


class TextBoxMixin:
    height = 1

    def validation(self, x: "Any") -> "bool":
        return self.normalize(x) is not None

    def normalize(self, x):
        return x

    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=Text(
                    text=self.data.get("state", {}).get("value", ""),
                    on_text_changed=self.text_changed,
                    validation=self.validation,
                    height=self.height,
                ),
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            )
        )

    def text_changed(self, buffer: "Buffer") -> "None":
        if (value := self.normalize(buffer.text)) is not None:
            self.set_state("value", value)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.body.buffer.text = str(
            self.data.get("state", {}).get("value", "")
        )


class TextModel(TextBoxMixin, JupyterWidget):
    """A text input widget."""


class TextareaModel(TextBoxMixin, JupyterWidget):
    """A text input widget."""

    height = 3


class IntValueMixin:
    def normalize(self, x: "Any") -> "Optional[int]":
        try:
            value = int(x)
        except ValueError:
            return
        else:
            if minimum := self.data.get("state", {}).get("min"):
                if value < minimum:
                    return
            if maximum := self.data.get("state", {}).get("max"):
                if maximum < value:
                    return
            return value


class NumberTextMixin:
    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=ReferencedSplit(
                    VSplit,
                    [
                        Text(
                            text=self.data.get("state", {}).get("value", ""),
                            on_text_changed=self.text_changed,
                            validation=self.validation,
                            height=self.height,
                        ),
                        Button(
                            "-",
                            show_borders=(True, False, True, True),
                            on_click=self.decr,
                        ),
                        Button(
                            "+",
                            show_borders=(True, True, True, False),
                            on_click=self.incr,
                        ),
                    ],
                ),
                label=lambda: self.data.get("state", {}).get("description", ""),
                style="class:ipywidget",
            )
        )

    def incr(self, button: "Button") -> "None":
        value = Decimal(str(self.data["state"]["value"]))
        step = Decimal(str(self.data["state"].get("step", 1)))
        if (new := self.normalize(value + step)) is not None:
            self.set_state("value", new)

    def decr(self, button: "Button") -> "None":
        value = Decimal(str(self.data["state"]["value"]))
        step = Decimal(str(self.data["state"].get("step", 1)))
        if (new := self.normalize(value - step)) is not None:
            self.set_state("value", new)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body._children[0].buffer.text = str(
            self.data.get("state", {}).get("value", "")
        )


class IntTextModel(IntValueMixin, NumberTextMixin, TextBoxMixin, JupyterWidget):
    """An integer textbox widget."""


class BoundedIntTextModel(IntValueMixin, NumberTextMixin, TextBoxMixin, JupyterWidget):
    """An integer textbox widget with upper and lower bounds."""


class FloatValueMixin:
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


class FloatTextModel(FloatValueMixin, NumberTextMixin, TextBoxMixin, JupyterWidget):
    """A float textbox widget."""


class BoundedFloatTextModel(
    FloatValueMixin, NumberTextMixin, TextBoxMixin, JupyterWidget
):
    """An float textbox widget with upper and lover bounds."""


class SliderMixin:
    def value_changed(self, slider_data: "Slider") -> "None":
        if (value := self.normalize(slider_data.value[0])) is not None:
            self.set_state("value", value)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        value = self.data.get("state", {})["value"]
        if value in self.options:
            index = self.options.index(value)
            self.sync = False
            container.body.body.body.data.set_index(ab=index)
            self.sync = True

    def _create_view(self, cell: "Cell"):
        options = self.options
        orientation = self.data["state"]["orientation"]
        return FocusedStyle(
            Box(
                LabeledWidget(
                    body=Slider(
                        options=options,
                        index=options.index(self.data["state"]["value"]),
                        show_readout=Condition(lambda: self.data["state"]["readout"]),
                        arrows=("⮜", "⮞")
                        if orientation == "horizontal"
                        else ("⮟", "⮝"),
                        show_arrows=True,
                        on_value_change=self.value_changed,
                        orientation=orientation,
                    ),
                    orientation=orientation,
                    label=lambda: self.data.get("state", {}).get("description", ""),
                    height=1,
                ),
                padding_left=0,
                style="class:ipywidget",
            )
        )


class IntSliderModel(SliderMixin, IntValueMixin, JupyterWidget):
    @property
    def options(self) -> "List[int]":
        return list(
            range(
                self.data["state"]["min"],
                self.data["state"]["max"] + self.data["state"]["step"],
                self.data["state"]["step"],
            )
        )


class FloatSliderModel(SliderMixin, FloatValueMixin, JupyterWidget):
    @property
    def options(self) -> "List[float]":
        start = Decimal(str(self.data["state"]["min"]))
        stop = Decimal(str(self.data["state"]["max"] + self.data["state"]["step"]))
        step = Decimal(str(self.data["state"]["step"]))
        return [start + step * i for i in range(int((stop - start) / step))]


class FloatLogSliderModel(SliderMixin, FloatValueMixin, JupyterWidget):
    @property
    def options(self) -> "List[float]":
        from decimal import Decimal

        base = Decimal(str(self.data["state"]["base"]))
        start = Decimal(str(self.data["state"]["min"]))
        stop = Decimal(str(self.data["state"]["max"] + self.data["state"]["step"]))
        step = Decimal(str(self.data["state"]["step"]))
        return [base ** (start + step * i) for i in range(int((stop - start) / step))]


class RangeSliderMixin:
    def value_changed(self, slider_data: "Slider") -> "None":
        if (value := [self.normalize(x) for x in slider_data.value]) is not None:
            self.set_state("value", value)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        value = self.data.get("state", {})["value"]
        if value in self.options:
            index = self.options.index(value)
            self.sync = False
            container.body.body.data.set_index(ab=index)
            self.sync = True

    def _create_view(self, cell: "Cell"):
        options = self.options
        orientation = self.data["state"]["orientation"]
        return FocusedStyle(
            Box(
                LabeledWidget(
                    body=Slider(
                        options=options,
                        index=[options.index(x) for x in self.data["state"]["value"]],
                        show_readout=Condition(lambda: self.data["state"]["readout"]),
                        arrows=("⮜", "⮞")
                        if orientation == "horizontal"
                        else ("⮟", "⮝"),
                        show_arrows=True,
                        on_value_change=self.value_changed,
                        orientation=orientation,
                    ),
                    orientation=orientation,
                    label=lambda: self.data.get("state", {}).get("description", ""),
                    height=1,
                ),
                padding_left=0,
                style="class:ipywidget",
            )
        )


class IntRangeSliderModel(RangeSliderMixin, FloatSliderModel):
    ...


class FloatRangeSliderModel(RangeSliderMixin, FloatSliderModel):
    ...


class ProgressMixin:
    def _create_view(self, cell: "Cell") -> "AnyContainer":
        orientation = self.data["state"]["orientation"]
        step = self.data["state"].get("step", 1)
        return FocusedStyle(
            Box(
                LabeledWidget(
                    body=Progress(
                        start=self.data["state"]["min"],
                        stop=self.data["state"]["max"],
                        step=step,
                        value=self.data["state"]["value"],
                        orientation=orientation,
                        style=self.style,
                    ),
                    orientation=orientation,
                    label=lambda: self.data.get("state", {}).get("description", ""),
                    height=1,
                ),
                padding_left=0,
                style="class:ipywidget",
            )
        )

    def style(self):
        style = self.data["state"]["bar_style"]
        if style:
            return f"class:{style}"
        return ""

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.body.style = self.style
        container.body.body.value = self.data["state"]["value"]
        container.body.body.control.start = self.data["state"]["min"]
        container.body.body.control.stop = self.data["state"]["max"]


class IntProgressModel(ProgressMixin, IntValueMixin, JupyterWidget):
    """"""


class FloatProgressModel(ProgressMixin, FloatValueMixin, JupyterWidget):
    """"""


class BoolMixin:
    def normalize(self, x: "Any") -> "Optional[float]":
        try:
            value = bool(x)
        except ValueError:
            return None
        else:
            return value

    def value_changed(self, button: "ToggleButton") -> "None":
        if (value := self.normalize(button.selected)) is not None:
            self.set_state("value", value)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.selected = self.data["state"]["value"]


class ToggleButtonModel(BoolMixin, JupyterWidget):
    """A toggleable button widget."""

    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            Box(
                ToggleButton(
                    text=self.data["state"].get("description", ""),
                    on_click=self.value_changed,
                    selected=self.data["state"]["value"],
                ),
                padding_left=0,
                style="class:ipywidget",
            )
        )


class CheckboxModel(BoolMixin, JupyterWidget):
    """A checkbox widget."""

    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            Box(
                Checkbox(
                    text=self.data["state"].get("description", ""),
                    on_click=self.value_changed,
                    selected=self.data["state"]["value"],
                ),
                padding_left=0,
                style="class:ipywidget",
            )
        )


class ValidModel(BoolMixin, JupyterWidget):
    """A validity indicator widget."""

    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=Box(
                    Checkbox(
                        on_click=self.value_changed,
                        selected=self.data["state"]["value"],
                        prefix=("❌", "✔️"),
                    ),
                    padding_left=0,
                ),
                label=self.data["state"].get("description", ""),
            ),
            style="class:ipywidget",
        )


class DropdownModel(JupyterWidget):
    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=Box(
                    Dropdown(
                        options=self.data["state"]["_options_labels"],
                        index=self.data["state"]["index"],
                        on_change=self.update_index,
                        style="class:ipywidget",
                    ),
                    padding_left=0,
                ),
                label=lambda: self.data["state"].get("description", ""),
                height=1,
                style="class:ipywidget",
            )
        )

    def update_index(self, container: "Select") -> "None":
        self.set_state("index", container.index)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.body.index = self.data["state"]["index"]
        container.body.body.options = self.data["state"]["_options_labels"]


class RadioButtonsModel(JupyterWidget):
    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=Box(
                    Selection(
                        options=self.data["state"]["_options_labels"],
                        index=self.data["state"]["index"],
                        on_change=self.update_index,
                        style="class:radio-buttons",
                        prefix=("○", "◉"),
                        multiple=False,
                    ),
                    padding_left=0,
                ),
                label=lambda: self.data["state"].get("description", ""),
                height=1,
                style="class:ipywidget",
            )
        )

    def update_index(self, container: "Select") -> "None":
        self.set_state("index", container.index)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.body.index = self.data["state"]["index"]
        container.body.body.options = self.data["state"]["_options_labels"]


class SelectModel(JupyterWidget):
    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=Box(
                    Border(
                        Selection(
                            options=self.data["state"]["_options_labels"],
                            index=self.data["state"]["index"],
                            on_change=self.update_index,
                            style="class:select",
                            multiple=False,
                        ),
                        border=WidgetGrid,
                        style="class:select.border",
                    ),
                    padding_left=0,
                ),
                label=lambda: self.data["state"].get("description", ""),
                height=1,
                style="class:ipywidget",
            )
        )

    def update_index(self, container: "Select") -> "None":
        self.set_state("index", container.index)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.body.body.body.options = self.data["state"]["_options_labels"]
        container.body.body.body.body.index = self.data["state"]["index"]


class SelectMultipleModel(JupyterWidget):
    def _create_view(self, cell: "Cell"):
        return FocusedStyle(
            LabeledWidget(
                body=Box(
                    Border(
                        Selection(
                            options=self.data["state"]["_options_labels"],
                            indices=self.data["state"]["index"],
                            on_change=self.update_index,
                            style="class:select",
                            multiple=True,
                        ),
                        border=WidgetGrid,
                        style="class:select.border",
                    ),
                    padding_left=0,
                ),
                label=lambda: self.data["state"].get("description", ""),
                height=1,
                style="class:ipywidget",
            )
        )

    def update_index(self, container: "Select") -> "None":
        self.set_state("index", container.indices)

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.body.body.body.options = self.data["state"]["_options_labels"]
        container.body.body.body.body.indices = self.data["state"]["index"]


WIDGET_MODELS = {
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
}


def open_comm_ipywidgets(nb, comm_id, data):
    model_name = data.get("state", {}).get("_model_name")
    log.debug("Creating new '%s' widget", model_name)
    return WIDGET_MODELS.get(model_name, UnimplementedWidget)(nb, comm_id, data)
