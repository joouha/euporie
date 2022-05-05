import logging

from prompt_toolkit.layout.containers import HSplit, VSplit, Window, to_container
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets.base import Box

from euporie.comm.base import Comm
from euporie.widgets.cell_outputs import CellOutputArea
from euporie.widgets.inputs import Button, Text, LabeledWidget, Slider
from euporie.widgets.layout import ReferencedSplit


log = logging.getLogger(__name__)


class JupyterWidget(Comm):
    target_name = "jupyter.widget"

    def __init__(self, nb, comm_id: "str", data: "dict") -> "None":
        super().__init__(nb, comm_id, data)

    def set_state(self, key, value):
        self.data.setdefault("state", {})[key] = value
        self.nb.kernel.kc_comm(
            comm_id=self.comm_id, data={"method": "update", "state": {key: value}}
        )

    def process_data(self, data):
        if data.get("method") == "update":
            self.data["state"].update(data.get("state", {}))
        self.update_views()


class UnimplementedWidget(JupyterWidget):
    ...


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


class HBoxIpyWidget(LayoutMixin, JupyterWidget):
    """A horizontal layout."""

    def _create_view(self, cell: "Cell"):
        return ReferencedSplit(VSplit, self.children(cell), padding=1)


class VBoxIpyWidget(LayoutMixin, JupyterWidget):
    """A vertical layout."""

    def _create_view(self, cell: "Cell"):
        return ReferencedSplit(HSplit, self.children(cell), padding=0)


class BoxIpyWidget(HBoxIpyWidget):
    """Appears to be the same a HBox."""


class ButtonIpyWidget(JupyterWidget):
    """A Button widget."""

    def _create_view(self, cell: "Cell"):
        return Box(
            Button(
                text=self.data["state"].get("description", ""),
                handler=self.click,
                style="class:ipywidget",
            ),
            padding_left=0,
        )

    def click(self) -> "None":
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
        return LabeledWidget(
            body=Text(
                text=self.data.get("state", {}).get("value", ""),
                style="class:ipywidget",
                on_text_changed=self.text_changed,
                validation=self.validation,
                height=self.height,
            ),
            label=lambda: "\n" + self.data.get("state", {}).get("description", ""),
            height=3,
        )

    def text_changed(self, buffer: "Buffer") -> "None":
        if (value := self.normalize(buffer.text)) is not None:
            self.set_state("value", value)
            self.nb.kernel.kc_comm(
                comm_id=self.comm_id,
                data={"method": "update", "state": {"value": value}},
            )
            self.update_views()

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.buffer.text = str(self.data.get("state", {}).get("value", ""))


class TextIpyWidget(TextBoxMixin, JupyterWidget):
    """A text input widget."""


class TextareaIpyWidget(TextBoxMixin, JupyterWidget):
    """A text input widget."""

    height = 3


class IntValueMixin:
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


class IntTextIpyWidget(IntValueMixin, TextBoxMixin, JupyterWidget):
    """An integer textbox widget."""


class BoundedIntTextIpyWidget(IntValueMixin, TextBoxMixin, JupyterWidget):
    """An integer textbox widget with upper and lover bounds."""


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


class FloatTextIpyWidget(FloatValueMixin, TextBoxMixin, JupyterWidget):
    """A float textbox widget."""


class BoundedFloatTextIpyWidget(IntValueMixin, TextBoxMixin, JupyterWidget):
    """An float textbox widget with upper and lover bounds."""


class OutputIpyWidget(JupyterWidget):
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


class IntSliderIpyWidget(IntValueMixin, JupyterWidget):
    def _create_view(self, cell: "Cell"):
        options = self.options
        return LabeledWidget(
            body=Slider(
                options=options,
                index=options.index(self.data["state"]["value"]),
                style="class:ipywidget",
                readout=self.data["state"]["readout"],
            ),
            label=lambda: self.data.get("state", {}).get("description", ""),
            height=1,
        )

    @property
    def options(self):
        return list(
            range(
                self.data["state"]["min"],
                self.data["state"]["max"] + self.data["state"]["step"],
                self.data["state"]["step"],
            )
        )

    def text_changed(self, buffer: "Buffer") -> "None":
        if (value := self.normalize(buffer.text)) is not None:
            self.set_state("value", value)
            self.nb.kernel.kc_comm(
                comm_id=self.comm_id,
                data={"method": "update", "state": {"value": value}},
            )
            self.update_views()

    def update_view(self, cell: "Cell", container: "AnyContainer") -> "None":
        container.body.index = [
            self.options.index(self.data.get("state", {})["value"]),
        ]


WIDGET_MODELS = {
    "HBoxModel": HBoxIpyWidget,
    "VBoxModel": VBoxIpyWidget,
    "OutputModel": OutputIpyWidget,
    "ButtonModel": ButtonIpyWidget,
    "TextModel": TextIpyWidget,
    "TextareaModel": TextareaIpyWidget,
    "IntTextModel": IntTextIpyWidget,
    "BoundedIntTextModel": BoundedIntTextIpyWidget,
    "FloatTextModel": FloatTextIpyWidget,
    "BoundedFloatTextModel": BoundedFloatTextIpyWidget,
    "IntSliderModel": IntSliderIpyWidget,
}


def open_comm_ipywidgets(nb, comm_id, data):
    model_name = data.get("state", {}).get("_model_name")
    log.debug("Creating new '%s' widget", model_name)
    return WIDGET_MODELS.get(model_name, UnimplementedWidget)(nb, comm_id, data)
