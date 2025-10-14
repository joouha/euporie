"""This module contains ipympl Comm implementations."""

from __future__ import annotations

import json
import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters.base import Condition
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.mouse_events import MouseButton, MouseEventType, MouseModifier

from euporie.core.comm.base import CommView
from euporie.core.comm.ipywidgets import IpyWidgetComm
from euporie.core.convert.datum import Datum
from euporie.core.convert.mime import MIME_FORMATS
from euporie.core.layout.containers import HSplit, VSplit
from euporie.core.layout.decor import FocusedStyle
from euporie.core.mouse_events import RelativePosition
from euporie.core.widgets.display import Display
from euporie.core.widgets.forms import Button, Label, ToggleButton
from euporie.core.widgets.layout import Box

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.mouse_events import MouseEvent as PtkMouseEvent

    from euporie.core.tabs.kernel import KernelTab
    from euporie.core.widgets.cell_outputs import OutputParent
log = logging.getLogger(__name__)


MOUSE_BUTTON_MAP = {
    MouseButton.NONE: -1,
    MouseButton.LEFT: 0,
    MouseButton.MIDDLE: 1,
    MouseButton.RIGHT: 2,
    # MouseButton.BACK: 3,
    # MouseButton.FORWARD: 4,
}

MOUSE_BUTTONS_MAP = {-1: 0, 0: 1, 1: 4, 2: 2, 3: 8, 4: 16}

MOUSE_EVENT_TYPE_MAP = {
    MouseEventType.MOUSE_UP: "button_release",
    MouseEventType.MOUSE_DOWN: "button_press",
    MouseEventType.SCROLL_UP: "scroll",
    MouseEventType.SCROLL_DOWN: "scroll",
    MouseEventType.MOUSE_MOVE: "motion_notify",
}

MOUSE_MODIFIER_MAP = {
    MouseModifier.SHIFT: "shift",
    MouseModifier.ALT: "alt",
    MouseModifier.CONTROL: "ctrl",
}


class MPLCanvasModel(IpyWidgetComm):
    """A ipywidget which displays an image."""

    def __init__(
        self,
        comm_container: KernelTab,
        comm_id: str,
        data: dict,
        buffers: Sequence[bytes],
    ) -> None:
        """Create a new instance of the ipywidget."""
        super().__init__(comm_container, comm_id, data, buffers)
        self._waiting_for_image = False

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the image widget."""
        self.comm_container.kernel.kc_comm(
            comm_id=self.comm_id,
            data={"method": "custom", "content": {"type": "refresh"}},
        )
        self.comm_container.kernel.kc_comm(
            comm_id=self.comm_id,
            data={"method": "custom", "content": {"type": "send_image_mode"}},
        )
        self.comm_container.kernel.kc_comm(
            comm_id=self.comm_id,
            data={"method": "custom", "content": {"type": "initialized"}},
        )

        # Figure label
        label = Label(self.data["state"]["_figure_label"])

        # Image data
        data_uri = self.data["state"]["_data_url"]
        _proto, _, data_path = data_uri.rpartition(":")
        data_format, _, encoded_data = data_path.partition(",")
        mime, *_params = data_format.split(";")
        format_ = f"base64-{MIME_FORMATS.get(mime, 'png')}"
        size = self.data["state"]["_size"]
        display = Display(
            Datum(data=encoded_data, format=format_, px=int(size[0]), py=int(size[1])),
            mouse_handler=self.mouse_handler,
            focusable=True,
            focus_on_click=True,
        )

        # Message
        message = Label(self.data["state"]["_message"])

        # Toolbar
        toolbar_comm_id = (
            self.data["state"].get("toolbar", "").removeprefix("IPY_MODEL_")
        )
        toolbar_model = self.comm_container.comms[toolbar_comm_id]
        toolbar_view = toolbar_model.new_view(parent)

        box = Box(
            HSplit(
                [
                    ConditionalContainer(
                        label,
                        filter=Condition(
                            partial(self.data["state"].get, "header_visible", True)
                        ),
                    ),
                    display,
                    ConditionalContainer(
                        message,
                        filter=Condition(
                            partial(self.data["state"].get, "footer_visible", True)
                        ),
                    ),
                    toolbar_view,
                ]
            ),
            padding_left=0,
            padding_right=0,
        )

        def _set_toolbar_nav_mode(value: str) -> None:
            toolbar_view.update({"_current_action": value.lower()})

        return CommView(
            box,
            setters={
                "_data_url": partial(self.set_url, display),
                "_data": partial(self.set_data, display),
                "_size": partial(self.set_size, display),
                "_figure_label": partial(setattr, label, "value"),
                "_message": partial(setattr, message, "value"),
                "__navigate_mode": _set_toolbar_nav_mode,
            },
        )

    def mouse_handler(self, mouse_event: PtkMouseEvent) -> NotImplementedOrNone:
        """Process a mouse event, and forward it to the kernel.

        Args:
            mouse_event: The prompt-toolkit mouse event to process.

        """
        if self.comm_container.kernel and (
            msg_type := MOUSE_EVENT_TYPE_MAP.get(mouse_event.event_type)
        ):
            px, py = self.comm_container.app.cell_size_px
            cell_position = getattr(
                mouse_event, "cell_position", RelativePosition(0.5, 0.5)
            )
            x = (mouse_event.position.x + cell_position.x) * px
            y = (mouse_event.position.y + cell_position.y) * py

            # Translate PTK mouse buttons to javascript buttons
            button = MOUSE_BUTTON_MAP[mouse_event.button]
            buttons = sum([MOUSE_BUTTONS_MAP[idx] for idx in [button]])

            modifiers = [
                MOUSE_MODIFIER_MAP[modifier]
                for modifier in mouse_event.modifiers
                if modifier in MOUSE_MODIFIER_MAP
            ]

            step = None
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                step = 1
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                step = -1

            content: dict[str, Any] = {
                "type": msg_type,
                "x": x,
                "y": y,
                "button": button,
                "buttons": buttons,
                "modifiers": modifiers,
                "step": step,
                "guiEvent": {},
            }
            self.comm_container.kernel.kc_comm(
                comm_id=self.comm_id,
                data={"method": "custom", "content": content},
            )
        return NotImplemented

    def set_size(self, display: Display, value: list[float]) -> None:
        """Set the size of the canvas display.

        Args:
            display: The display to resize.
            value: The new [width, height] of the canvas.

        """
        display.datum.px = int(value[0])
        display.datum.py = int(value[1])

    def set_url(self, display: Display, data_uri: str) -> None:
        """Set the image data for a display from a data URI.

        Args:
            display: The display to update.
            data_uri: The data URI of the new image.

        """
        _proto, _, data_path = data_uri.rpartition(":")
        data_format, _, encoded_data = data_path.rpartition(",")
        mime, *_params = data_format.split(";")
        format_ = f"base64-{MIME_FORMATS.get(mime, 'png')}"
        display.datum = Datum(encoded_data, format=format_)

    def set_data(self, display: Display, value: bytes) -> None:
        """Set the image data for a display from bytes.

        Args:
            display: The display to update.
            value: The new image data.

        """
        # Only display full png images (ipymlp sometimes sends raw RGB data to clear the canvas)
        if value.startswith(b"\x89PNG"):
            image_mode = self.data["state"].get("_image_mode")
            datum = Datum(data=value, format="png")
            # If image is sent using diff mode, paste new image onto previous
            if image_mode == "diff":
                bg = display.datum.convert("pil")
                fg = datum.convert("pil")
                bg.paste(fg, (0, 0), fg)
                datum = Datum(bg, format="pil")
            display.datum = datum
            self.data["state"]["_data_url"] = (
                f"data:image/png;base64,{datum.convert('base64-png')}"
            )

    def process_data(
        self, data: dict, buffers: Sequence[memoryview | bytearray | bytes]
    ) -> None:
        """Process data received from the kernel.

        Args:
            data: The data dictionary from the comm message.
            buffers: The binary buffers from the comm message.

        """
        super().process_data(data, buffers)
        method = data.get("method")
        if method == "custom":
            msg = json.loads(data.get("content", {}).get("data", "{}"))
            msg_type = msg.get("type")

            if msg_type == "binary":
                buffer = buffers[0]
                if isinstance(buffer, memoryview):
                    buffer = buffer.tobytes()
                elif isinstance(buffer, bytearray):
                    buffer = bytes(buffer)
                self.update_views({"_data": buffer})
                self._waiting_for_image = False

            elif msg_type == "draw":
                if not self._waiting_for_image:
                    self.comm_container.kernel.kc_comm(
                        comm_id=self.comm_id,
                        data={"method": "custom", "content": {"type": "draw"}},
                    )
                    self._waiting_for_image = True

            elif msg_type == "navigate_mode":
                self.update_views({"__navigate_mode": msg["mode"]})

            elif msg_type == "save":
                import tempfile
                from base64 import b64decode
                from pathlib import Path

                with tempfile.NamedTemporaryFile(
                    "wb", suffix=".png", delete=False
                ) as f:
                    data_uri = self.data["state"].get("_data_url", "")
                    _proto, _, data_path = data_uri.rpartition(":")
                    _data_format, _, encoded_data = data_path.rpartition(",")
                    f.write(b64decode(encoded_data))
                    self.comm_container.app.open_file(Path(f.name))

            # elif msg_type == "history_buttons":
            #     pass

            # elif msg_type == "resize":
            #     pass

            # else:
            #     log.debug(data)


class ToolbarModel(IpyWidgetComm):
    """A toolbar with a list of buttons."""

    def create_view(self, parent: OutputParent) -> CommView:
        """Create a new view of the toolbar ipywidget."""
        from euporie.core.reference import FA_ICONS

        buttons = {}
        children = []
        for name, _tooltip, image, method in self.data["state"]["toolitems"]:
            ButtonClass = ToggleButton if method in {"pan", "zoom"} else Button
            button = ButtonClass(
                text=f"{FA_ICONS.get(image.removesuffix('-o'), '#')} {name}",
                on_click=partial(self.click, method),
            )
            buttons[method] = button
            children.append(FocusedStyle(button))

        split = VSplit(children)

        def _set_current_action(value: str) -> None:
            for name, button in buttons.items():
                button.selected = name.lower() == value.lower()

        return CommView(
            split,
            setters={"_current_action": _set_current_action},
        )

    def click(self, method: str, button: Button) -> None:
        """Send a ``comm_msg`` describing a click event."""
        if method in ("pan", "zoom"):
            if self.data["state"].get("_current_action") == method:
                self.data["state"]["_current_action"] = ""
            else:
                self.data["state"]["_current_action"] = method
        if self.comm_container.kernel:
            self.comm_container.kernel.kc_comm(
                comm_id=self.comm_id,
                data={
                    "method": "custom",
                    "content": {"type": "toolbar_button", "name": method},
                },
            )
