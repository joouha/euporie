import asyncio
import logging
from functools import partial
from math import ceil, floor
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.filters import Always, to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_width
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.validation import Validator
from prompt_toolkit.widgets.base import TextArea

from euporie.border import EighthBlockUpperRight, EighthBlockLowerLeft, Thin
from euporie.formatted_text.utils import (
    FormattedTextAlign,
    add_border,
    align,
    apply_style,
)
from euporie.margins import ScrollbarMargin
from euporie.widgets.decor import Border

if TYPE_CHECKING:
    from typing import Callable, List, Optional, TypeVar, Tuple, Union

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import Container

    T = TypeVar("T")

log = logging.getLogger(__name__)

WidgetGrid = (
    EighthBlockLowerLeft.top_edge
    + EighthBlockLowerLeft.right_edge
    + EighthBlockUpperRight.left_edge
    + EighthBlockUpperRight.bottom_edge
    + Thin.inner
)


def is_iterable(x):
    try:
        iterator = iter(x)
    except TypeError:
        return False
    else:
        return True


class Button:
    """Clickable button.

    :param text: The caption for the button.
    :param handler: `None` or callable. Called when the button is clicked. No
        parameters are passed to this callable. Use for instance Python's
        `functools.partial` to pass parameters to this callable if needed.
    :param width: Width of the button.
    """

    def __init__(
        self,
        text: "AnyFormattedText",
        handler: "Optional[Callable[[], None]]" = None,
        width: "Optional[int]" = None,
        style: "str" = "",
    ) -> None:
        self.text = to_formatted_text(text)
        self.handler = handler
        self.width = width or fragment_list_width(self.text)
        self.window = Window(
            FormattedTextControl(
                self._get_text_fragments,
                key_bindings=self._get_key_bindings(),
                focusable=True,
            ),
            style=style,
            dont_extend_width=True,
            dont_extend_height=True,
        )

    def _get_style(self) -> str:
        if get_app().layout.has_focus(self):
            return "class:button.focused"
        else:
            return "class:button"

    def _get_text_fragments(self) -> "StyleAndTextTuples":
        def handler(mouse_event: MouseEvent) -> None:
            if (
                self.handler is not None
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.handler()

        ft = [
            ("[SetCursorPosition]", ""),
            *self.text,
        ]
        ft = align(FormattedTextAlign.CENTER, ft, self.width)
        ft = add_border(
            ft,
            style="class:button.border",
            border=WidgetGrid,
            # padding=(0, 1, 0, 1),
        )
        ft = apply_style(ft, self._get_style())
        ft = [(style, text, handler) for style, text, *_ in ft]
        return ft

    def _get_key_bindings(self) -> "KeyBindings":
        "Key bindings for the Button."
        kb = KeyBindings()

        @kb.add(" ")
        @kb.add("enter")
        def _(event: "KeyPressEvent") -> None:
            if self.handler is not None:
                self.handler()

        return kb

    def __pt_container__(self) -> "Container":
        return self.window


class Text:
    """A text input."""

    def __init__(
        self,
        text: "str" = "",
        style: "str" = "",
        height: "int" = 1,
        on_text_changed: "Optional[Callable[[Buffer], None]]" = None,
        validation: "Optional[Callable[[str], bool]]" = None,
    ):
        self.style = style
        self.text_area = TextArea(
            str(text),
            multiline=height > 1,
            height=height,
            focusable=True,
            focus_on_click=True,
            style=style,
            validator=Validator.from_callable(validation) if validation else None,
        )
        self.buffer = self.text_area.buffer
        if validation:
            self.text_area.buffer.validate_while_typing = Always()
        if height > 1:
            self.text_area.window.right_margins += [ScrollbarMargin()]
        self.text_area.buffer.on_text_changed += on_text_changed
        self.container = Border(
            self.text_area,
            border=WidgetGrid,
            style=self.border_style,
        )

    def border_style(self):
        if self.text_area.buffer.validation_state == ValidationState.INVALID:
            return f"{self.style} class:text-area.border,invalid"
        else:
            return f"{self.style} class:text-area.border"

    @property
    def text(self) -> "str":
        return self.text_area.text

    @text.setter
    def text(self, value: "str") -> "None":
        self.text_area.text = value

    def __pt_container__(self) -> "Container":
        return self.container


class LabeledWidget:
    def __init__(self, body: "AnyContainer", label, height: "Optional[int]"):
        self.body = body
        self.container = VSplit(
            [
                Window(
                    FormattedTextControl(label),
                    dont_extend_width=True,
                    height=height,
                ),
                self.body,
            ],
            padding=1,
        )

    def __pt_container__(self) -> "Container":
        return self.container


class Slider:
    """A slider input widget.

    ⮜ ───⬤━━━━━━━⬤──── ⮞ 9 - 18

    """

    def __init__(
        self,
        options: "List[T]",
        index: "Union[int, Tuple[int, int]]]" = 0,
        width: "int" = 20,
        arrows: "FilterOrBool" = True,
        readout: "FilterOrBool" = True,
        style: "str" = "",
    ) -> None:
        assert len(options) > 0
        self.index = list(index) if is_iterable(index) else [index]
        self.width = width or fragment_list_width(self.text)
        self._selected_handle = 0
        self.options = options
        self.arrows = to_filter(arrows)
        self.readout = to_filter(readout)
        self.container = Window(
            FormattedTextControl(
                self._get_text_fragments,
                # key_bindings=self._get_key_bindings(),
                focusable=True,
            ),
            style=f"class:slider {style}",
        )
        self.repeat_task: "Optional[asyncio.Task[None]]" = None
        self.dragging = False

    @property
    def selected_handle(self) -> "int":
        return self._selected_handle

    @selected_handle.setter
    def selected_handle(self, value: "int"):
        value = max(0, min(len(self.index)))
        self._selected_handle = value

    @property
    def value(self) -> "Union[T, Tuple[T,T]]]":
        if len(self.index) == 1:
            return self.options[self.index[0]]
        else:
            return (self.options[self.index[0]], self.options[self.index[1]])

    @property
    def value_str(self) -> "str":
        return " - ".join(map(lambda x: str(self.options[x]), self.index))

    def set_index(
        self, handle: "int", ab: "Optional[int]" = None, rel: "Optional[int]" = None
    ):
        assert ab is not None or rel is not None
        if rel is not None:
            ab = self.index[handle] + rel
        ab = min(len(self.options) - 1, max(0, ab))
        self.index[handle] = ab

    def _get_text_fragments(self):
        ft = []

        if self.arrows():
            ft.extend(
                [
                    (
                        "class:slider.arrow,left",
                        "⮜",
                        partial(self.mouse_handler_arrow, n=-1),
                    ),
                    ("", " "),
                ]
            )

        track_length = self.width - (4 if self.arrows() else 0) - len(self.index)
        first_seg = floor((track_length) * self.index[0] / (len(self.options) - 1))
        ft.extend(
            [
                (
                    "class:slider.track",
                    "─",
                    partial(
                        self.mouse_handler_track,
                        n=(floor(i / (track_length) * len(self.options))),
                    ),
                )
                for i in range(first_seg)
            ]
        )
        selected = ".selected" if self.selected_handle == 0 else ""
        ft.append(
            (
                f"class:slider.handle{selected}",
                "⬤",
            )
        )
        middle_seg = 0
        if len(self.index) > 1:
            middle_seg = floor(
                (track_length) * (self.index[-1] - self.index[0]) / len(self.options)
            )
            selected = ".selected" if self.selected_handle == 0 else ""
            ft.extend(
                [
                    ("class:slider.track,selected", "━" * middle_seg),
                    (
                        f"class:slider.handle{selected}",
                        "⬤",
                    ),
                ]
            )

        last_seg = track_length - first_seg - middle_seg
        ft.extend(
            [
                (
                    "class:slider.track",
                    "─",
                    partial(
                        self.mouse_handler_track,
                        n=ceil(i / (track_length) * (len(self.options) - 1)),
                    ),
                )
                for i in range(first_seg + middle_seg, track_length)
            ]
        )
        if self.arrows():
            ft.extend(
                [
                    ("", " " if self.arrows() else ""),
                    (
                        "class:slider.arrow,right",
                        "⮞",
                        partial(self.mouse_handler_arrow, n=1),
                    ),
                ]
            )
        if self.readout():
            ft.extend([("", " "), ("class:slider.value", self.value_str)])
        return ft

    def mouse_handler_track(
        self, mouse_event: "MouseEvent", repeated: "bool" = False, n: "int" = 0
    ) -> "None":
        """Generate a mouse event handler which calls a function on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            self.set_index(self.selected_handle, ab=n)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.set_index(self.selected_handle, rel=1)
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.set_index(self.selected_handle, rel=-1)

    def mouse_handler_arrow(
        self, mouse_event: "MouseEvent", repeated: "bool" = False, n: "int" = 0
    ) -> "None":
        """Generate a mouse event handler which calls a function on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            self.set_index(self.selected_handle, rel=n)
            # Trigger this mouse event to be repeated
            self.repeat_task = get_app().create_background_task(
                self.repeat(mouse_event, handler=self.mouse_handler_arrow, n=n)
            )
        else:
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                self.set_index(self.selected_handle, rel=-n)
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self.set_index(self.selected_handle, rel=-n)
            # Stop any repeated tasks
            if self.repeat_task is not None:
                self.repeat_task.cancel()
            self.dragging = False

    async def repeat(
        self, mouse_event: "MouseEvent", handler, timeout: "float" = 0.1, **kwargs
    ) -> "None":
        """Repeat a mouse event after a timeout."""
        await asyncio.sleep(timeout)
        handler(mouse_event, repeated=True, **kwargs)
        get_app().invalidate()

    def __pt_container__(self) -> "Container":
        return self.container
