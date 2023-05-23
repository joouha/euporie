from __future__ import annotations

import json
import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.mouse_events import MouseButton, MouseEventType, MouseModifier
from prompt_toolkit.widgets.base import Box

from euporie.core.comm.base import CommView
from euporie.core.comm.ipywidgets import IpyWidgetComm
from euporie.core.path import DataPath
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    from typing import Sequence

    from prompt_toolkit.mouse_events import MouseEvent

log = logging.getLogger(__name__)


MOUSE_BUTTON_MAP = {
    MouseButton.NONE: -1,
    MouseButton.LEFT: 0,
    MouseButton.MIDDLE: 1,
    MouseButton.RIGHT: 2,
}

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

        size = self.data["state"]["_size"]

        data_uri = self.data["state"]["_data_url"]
        data_format, _, encoded_data = data_uri.partition(",")
        # _mime, *params = data_format.split(";")

        display = Display(
            data=encoded_data,
            format_="base64-png",
            px=int(size[0]),
            py=int(size[1]),
            mouse_handler=self.mouse_handler,
        )
        box = Box(
            display,
            padding_left=0,
            padding_right=0,
        )

        return CommView(
            box,
            setters={
                "_data_url": partial(self.set_url, display),
                "_data": partial(self.set_data, display),
                "_size": partial(self.set_size, display),
                # "_message": log.debug,
                # "data": log.debug,
            },
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        if self.comm_container.kernel:
            if msg_type := MOUSE_EVENT_TYPE_MAP.get(mouse_event.event_type):
                px, py = get_app().term_info.cell_size_px
                x = (mouse_event.position.x + mouse_event.cell_position.x) * px
                y = (mouse_event.position.y + mouse_event.cell_position.y) * py

                button = MOUSE_BUTTON_MAP[mouse_event.button]

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

                content = {
                    "type": msg_type,
                    "x": x,
                    "y": y,
                    "button": button,
                    "modifiers": modifiers,
                    "step": step,
                    # "guiEvent": {"isTrusted": True},
                }

                self.comm_container.kernel.kc_comm(
                    comm_id=self.comm_id,
                    data={"method": "custom", "content": content},
                )

    def set_size(self, display: Display, value: list[float]) -> None:
        display.px = int(value[0])
        display.py = int(value[1])

    def set_url(self, display: Display, value: str) -> None:
        # data_format, _, encoded_data = self._url.path.partition(",")
        # _mime, *params = data_format.split(";")
        # display.format =
        display.data = DataPath(value).read_bytes()

    def set_data(self, display: Display, value: bytes) -> None:
        # display.overlay(value)
        display.format_ = "png"
        display.data = value

    def process_data(self, data: dict, buffers: Sequence[bytes]) -> None:
        try:
            super().process_data(data, buffers)
            method = data.get("method")
            if method == "custom":
                msg = json.loads(data.get("content", {}).get("data", "{}"))
                msg_type = msg.get("type")

                if msg_type == "binary":
                    data = buffers[0].tobytes()
                    self.update_views({"_data": data})

                else:
                    log.debug(msg_type)

        except:
            log.exception("")


"""
name = motion_notify
send_message(name, {
                x: x,
                y: y,
                button: event.button,
                step: event.step,
                modifiers: utils.getModifiers(event),
                guiEvent: utils.get_simple_keys(event),
            });
"""
