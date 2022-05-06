import asyncio
import logging
from functools import partial
from math import ceil, floor
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.filters import Always, Condition, has_focus, to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_len, fragment_list_width
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent, UIControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from prompt_toolkit.validation import Validator
from prompt_toolkit.widgets.base import Box, TextArea

from euporie.border import EighthBlockLowerLeft, EighthBlockUpperRight, Thin
from euporie.formatted_text.utils import (
    FormattedTextAlign,
    add_border,
    align,
    apply_style,
)
from euporie.margins import ScrollbarMargin
from euporie.widgets.decor import Border

if TYPE_CHECKING:
    from typing import Callable, List, Optional, Tuple, TypeVar, Union

    from prompt_toolkit.buffer import Buffer, BufferAcceptHandler
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

    def __pt_container__(self) -> "Container":
        return self.window


class Text:
    """A text input."""

    def __init__(
        self,
        text: "str" = "",
        style: "str" = "",
        height: "int" = 1,
        width: "Optional[int]" = None,
        on_text_changed: "Optional[Callable[[Buffer], None]]" = None,
        validation: "Optional[Callable[[str], bool]]" = None,
        accept_handler: "Optional[BufferAcceptHandler]" = None,
    ):
        self.style = style
        self.text_area = TextArea(
            str(text),
            multiline=height > 1,
            height=height,
            width=width,
            focusable=True,
            focus_on_click=True,
            style=style,
            validator=Validator.from_callable(validation) if validation else None,
            accept_handler=accept_handler,
        )
        self.buffer = self.text_area.buffer
        if height > 1:
            self.text_area.window.right_margins += [ScrollbarMargin()]
        if on_text_changed:
            self.text_area.buffer.on_text_changed += on_text_changed
        if validation:
            self.text_area.buffer.validate_while_typing = Always()
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
        return self.buffer.text

    @text.setter
    def text(self, value: "str") -> "None":
        self.buffer.text = value

    def __pt_container__(self) -> "Container":
        return self.container


class LabeledWidget:
    def __init__(self, body: "AnyContainer", label, height: "Optional[int]"):
        self.body = body
        self.container = VSplit(
            [
                ConditionalContainer(
                    Box(
                        Window(
                            FormattedTextControl(label),
                            dont_extend_width=True,
                            height=height,
                        ),
                        padding_left=0,
                        padding_right=0,
                    ),
                    filter=Condition(
                        lambda: bool(fragment_list_len(to_formatted_text(label)))
                    ),
                ),
                self.body,
            ],
            padding=1,
        )

    def __pt_container__(self) -> "Container":
        return self.container


class SliderData:
    def __init__(
        self,
        options: "Iterable[T]",
        index: "Iterable[int]" = (0,),
        on_value_change: "Optional[Callable[[Slider], None]]" = None,
    ):
        self.options = options
        self._index = list(index)
        self.on_value_change = Event(self, on_value_change)

    @property
    def value(self) -> "Tuple[T, ...]]":
        return tuple(self.options[index] for index in self._index)

    @property
    def index(self) -> "Tuple[int, ...]":
        return tuple(self._index)

    def set_index(
        self,
        handle: "int" = 0,
        ab: "Optional[int]" = None,
        rel: "Optional[int]" = None,
        fire=True,
    ):
        assert ab is not None or rel is not None
        if rel is not None:
            ab = self.index[handle] + rel
        ab = min(len(self.options) - 1, max(0, ab))
        self._index[handle] = ab
        if fire:
            self.on_value_change.fire()


class SliderControl(UIControl):
    def __init__(
        self,
        data: "SliderData",
        arrows: "Tuple[str, str]" = ("-", "+"),  # ⊖ ⊕  ⊟ ⊞  ⮜ ⮞
        show_arrows: "FilterOrBool" = True,
        handle_char: "str" = "⬤",
        style: "str" = "",
    ):
        self.data = data

        self.arrows = arrows
        self.show_arrows = to_filter(show_arrows)
        self.handle_char = handle_char
        self.has_focus = has_focus(self)

        self.selected_handle = 0
        self.track_len = 0

        self.mouse_handlers = {}
        self.dragging = False
        self.repeat_task: "Optional[asyncio.Task[None]]" = None

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def is_focusable(self) -> bool:
        """Tell whether this user control is focusable."""
        return True

    def create_content(self, width: int, height: int) -> "UIContent":
        def get_content() -> UIContent:
            fragment_lines = self.render_lines(width, height)

            return UIContent(
                get_line=lambda i: fragment_lines[i],
                line_count=len(fragment_lines),
                show_cursor=False,
            )

        key = (width, self.data.index, self.selected_handle, self.has_focus())
        return self._content_cache.get(key, get_content)

    @property
    def selected_handle(self) -> "int":
        return self._selected_handle

    @selected_handle.setter
    def selected_handle(self, value: "int"):
        value = max(0, min(value, len(self.data.index)))
        self._selected_handle = value

    def _draw_handle(self, n: "int") -> "StyleAndTextTyples":
        selected_style = (
            "class:slider.handle.selected" if self.selected_handle == n else ""
        )
        focused_style = "class:focused" if self.has_focus() else ""
        return (
            f"class:slider.handle {selected_style} {focused_style}",
            self.handle_char,
        )

    def mouse_handler_handle(
        self, mouse_event: "MouseEvent", handle: "int" = 0
    ) -> "None":
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            self.selected_handle = handle
            self.dragging = True
        self.mouse_handler_scroll(mouse_event)

    def mouse_handler_track(
        self, mouse_event: "MouseEvent", repeated: "bool" = False, index: "int" = 0
    ) -> "None":
        """Generate a mouse event handler which calls a function on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
            self.data.set_index(self.selected_handle, ab=index)
        else:
            self.mouse_handler_scroll(mouse_event)
            if self.repeat_task is not None:
                self.repeat_task.cancel()

    def mouse_handler_arrow(
        self, mouse_event: "MouseEvent", repeated: "bool" = False, n: "int" = 0
    ) -> "None":
        """Generate a mouse event handler which calls a function on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
            self.data.set_index(self.selected_handle, rel=n)
            # Trigger this mouse event to be repeated
            self.repeat_task = get_app().create_background_task(
                self.repeat(mouse_event, handler=self.mouse_handler_arrow, n=n)
            )
        else:
            # Stop any repeated tasks
            if self.repeat_task is not None:
                self.repeat_task.cancel()
            self.mouse_handler_scroll(mouse_event)

    def mouse_handler_scroll(
        self, mouse_event: "MouseEvent", handle: "Optional[int]" = None
    ):
        if handle is None:
            handle = self.selected_handle
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.data.set_index(handle, rel=1)
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.data.set_index(handle, rel=-1)

    def _mouse_handler(
        self, mouse_event: "MouseEvent", loc: "int"
    ) -> "NotImplementedOrNone":
        # Handle dragging
        if self.dragging and mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            pos = loc
            if self.show_arrows():
                pos -= 2
            pos = max(0, min(self.track_len, pos))
            self.data.set_index(
                self.selected_handle,
                ab=int((len(self.data.options) - 0.5) * pos / self.track_len),
            )
            return None
        else:
            self.dragging = False
            # Call the underlying mouse handler
            if handler := self.mouse_handlers.get(loc):
                return handler(mouse_event)
            else:
                return NotImplemented

    async def repeat(
        self, mouse_event: "MouseEvent", handler, timeout: "float" = 0.25, **kwargs
    ) -> "None":
        """Repeat a mouse event after a timeout."""
        await asyncio.sleep(timeout)
        handler(mouse_event, repeated=True, **kwargs)
        get_app().invalidate()


class HorizontalSliderControl(SliderControl):
    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        return max_available_width

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[GetLinePrefixCallable]",
    ) -> "Optional[int]":
        return 1

    def get_key_bindings(self) -> "Optional[KeyBindingsBase]":
        """Key bindings for the Slider."""
        kb = KeyBindings()

        @kb.add("left")
        def _(event: "KeyPressEvent") -> None:
            self.data.set_index(self.selected_handle, rel=-1)

        @kb.add("right")
        def _(event: "KeyPressEvent") -> None:
            self.data.set_index(self.selected_handle, rel=1)

        return kb

    def render_lines(self, width: "int", height: "int") -> "List[StyleAndTextTyples]":

        ft = []
        mouse_handlers = []

        track_len = width - len(self.data.index)

        if self.show_arrows():
            # The arrows take up 4 characters: remove them from the track length
            track_len -= 4
            ft += [("class:slider.arrow,left", self.arrows[0]), ("", " ")]
            mouse_handlers += [
                partial(self.mouse_handler_arrow, n=-1),
                self.mouse_handler_scroll,
            ]

        # First bit of track
        left_len = floor(
            (track_len) * self.data.index[0] / (len(self.data.options) - 1)
        )
        ft.append(("class:slider.track", "─" * left_len))
        mouse_handlers += [
            partial(
                self.mouse_handler_track,
                index=int((len(self.data.options) - 0.5) * i / track_len),
            )
            for i in range(0, left_len)
        ]

        # First handle
        ft.append((self._draw_handle(0)))
        mouse_handlers.append(partial(self.mouse_handler_handle, handle=0))

        # Middle bit of track
        middle_len = 0
        if len(self.data.index) > 1:
            middle_len = floor(
                (track_len) * (self.index[-1] - self.index[0]) / len(self.data.options)
            )
        if len(self.data.index) > 1:
            ft.append(("class:slider.track,selected", "━" * middle_len))
            mouse_handlers += [
                partial(
                    self.mouse_handler_track,
                    index=int((len(self.data.options) - 0.5) * i / track_len),
                )
                for i in range(left_len, middle_len + 1)
            ]
            # Second handle
            ft.append(self._draw_handle(1))
            mouse_handlers.append(partial(self.mouse_handler_handle, handle=1))

        # Last bit of track
        right_len = track_len - left_len - middle_len
        ft.append(("class:slider.track", "─" * right_len))
        mouse_handlers += [
            partial(
                self.mouse_handler_track,
                index=int(len(self.data.options) * i / track_len),
            )
            for i in range(left_len + middle_len, track_len)
        ]

        if self.show_arrows():
            ft += [("", " "), ("class:slider.arrow,right", self.arrows[1])]
            mouse_handlers += [
                self.mouse_handler_scroll,
                partial(self.mouse_handler_arrow, n=1),
            ]

        self.mouse_handlers = dict(enumerate(mouse_handlers))
        self.track_len = track_len

        return [ft]

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        self._mouse_handler(mouse_event, loc=mouse_event.position.x)


class Slider:
    """A slider input widget.

    ⮜ ───⬤━━━━━━━⬤──── ⮞ 9 - 18

    """

    def _validate_readout(self, text: "str") -> "Optional[T]":
        try:
            value = self.data_type(text)
        except ValueError:
            return None
        else:
            if value in self.data.options:
                return value

    def _value_changed(self, slider_data: "SliderData") -> "None":
        """Sets the readout text when the slider value changes."""
        self.readout.text = str(self.data.value[0])

    def _accept_handler(self, buffer: "Buffer") -> "bool":
        value = self._validate_readout(buffer.text)
        if value in self.data.options:
            self.data.set_index(ab=self.data.options.index(value))
            return True
        return False

    def __init__(
        self,
        options: "Iterable[T]",
        index: "Union[int, Tuple[int, int]]]" = 0,
        show_arrows: "FilterOrBool" = True,
        arrows: "Optional[Tuple[str, str]]" = None,
        show_readout: "FilterOrBool" = True,
        style: "str" = "",
        orientation="horizontal",
        on_value_change: "Optional[Callable[[Slider], None]]" = None,
    ) -> None:
        self.show_readout = to_filter(show_readout)
        self.orientation = orientation
        self.data_type = type(options[0])
        self.data = SliderData(
            options=options,
            index=(index,) if isinstance(index, int) else tuple(index),
            on_value_change=on_value_change,
        )
        self.data.on_value_change += self._value_changed
        self.slider_control = HorizontalSliderControl(
            self.data,
            arrows=arrows,
            show_arrows=to_filter(show_arrows),
        )
        self.readout = Text(
            text=self.data.value[0],
            height=1,
            width=min(max(map(len, map(str, self.data.options))) + 1, 10),
            style=style,
            validation=lambda x: self._validate_readout(x) is not None,
            accept_handler=self._accept_handler,
        )
        self.container = VSplit(
            [
                Box(
                    Window(self.slider_control, style=style),
                ),
                ConditionalContainer(self.readout, filter=self.show_readout),
            ],
            padding=1,
        )

    def __pt_container__(self) -> "Container":
        return self.container
