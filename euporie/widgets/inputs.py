import asyncio
import logging
from enum import Enum
from functools import partial
from math import ceil, floor
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.filters import Always, Condition, FilterOrBool, has_focus, to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_len, fragment_list_width
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent, UIControl
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from prompt_toolkit.validation import Validator
from prompt_toolkit.widgets.base import Box, TextArea

from euporie.border import (
    BorderVisibility,
    EighthBlockLowerLeft,
    EighthBlockUpperRight,
    Thin,
)
from euporie.formatted_text.utils import (
    FormattedTextAlign,
    add_border,
    align,
    apply_style,
)
from euporie.margins import ScrollbarMargin
from euporie.widgets.decor import Border

if TYPE_CHECKING:
    from numbers import Number
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


class WidgetOrientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


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
        if self.selected:
            return f"{self.style} class:button.selected"
        else:
            return f"{self.style} class:button"

    def _get_text_fragments(self) -> "StyleAndTextTuples":
        ft = [
            *to_formatted_text(self.text),
        ]
        ft = align(FormattedTextAlign.CENTER, ft, self.width)
        ft = [(style, text, self.mouse_handler) for style, text, *_ in ft]
        ft = [("[SetMenuPosition]", ""), *ft]
        return ft

    def _get_key_bindings(self) -> "KeyBindings":
        "Key bindings for the Button."
        kb = KeyBindings()

        @kb.add(" ")
        @kb.add("enter")
        def _(event: "KeyPressEvent") -> None:
            self.on_mouse_down.fire()
            self.on_click.fire()

        return kb

    def __init__(
        self,
        text: "AnyFormattedText",
        on_click: "Optional[Callable[[Button], None]]" = None,
        on_mouse_down: "Optional[Callable[[Button], None]]" = None,
        width: "Optional[int]" = None,
        style: "str" = "",
        border: "Optional[GridStyle]" = WidgetGrid,
        show_borders: "BorderVisibility" = BorderVisibility(True, True, True, True),
        selected: "bool" = False,
        key_bindings: "Optional[KeyBindings]" = None,
    ) -> None:
        self.text = text
        self.on_mouse_down = Event(self, on_mouse_down)
        self.on_click = Event(self, on_click)
        self.width = width or fragment_list_width(to_formatted_text(self.text)) + 2
        self.style = style
        self.selected = selected
        if key_bindings is not None:
            self.key_bindings = merge_key_bindings(
                [self._get_key_bindings(), key_bindings]
            )
        else:
            self.key_bindings = self._get_key_bindings()
        self.container = Border(
            Window(
                FormattedTextControl(
                    self._get_text_fragments,
                    key_bindings=self.key_bindings,
                    focusable=True,
                    show_cursor=False,
                    style="class:button.face",
                ),
                style=self._get_style,
                dont_extend_width=True,
                dont_extend_height=True,
            ),
            border=border,
            show_borders=show_borders,
            style=lambda: f"{self._get_style()} class:button.border",
        )

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
            self.selected = True
            self.on_mouse_down.fire()
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.selected = False
            self.on_click.fire()

    def __pt_container__(self) -> "Container":
        return self.container


class ToggleMixin:
    def toggle(self):
        self.selected = not self.selected
        self.on_click.fire()

    def _get_key_bindings(self) -> "KeyBindings":
        "Key bindings for the Button."
        kb = KeyBindings()

        @kb.add(" ")
        @kb.add("enter")
        def _(event: "KeyPressEvent") -> None:
            self.toggle()

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.toggle()


class ToggleButton(ToggleMixin, Button):
    """"""


class Checkbox(ToggleMixin):
    """"""

    def _get_text_fragments(self) -> "StyleAndTextTuples":
        selected_style = "class:selected" if self.selected else ""
        ft = [
            ("[SetCursorPosition] class:checkbox.box", self.prefix[int(self.selected)]),
            # Add space between the tickbox and the text
            ("", " " if fragment_list_len(self.text) else ""),
            *self.text,
        ]
        ft = [(style, text, self.mouse_handler) for style, text, *_ in ft]
        return ft

    def __init__(
        self,
        text: "AnyFormattedText" = "",
        on_click: "Optional[Callable[[Button], None]]" = None,
        prefix: "Tuple[str, str]" = ("☐", "☑"),
        style: "str" = "",
        selected: "bool" = False,
    ) -> None:
        self.text = to_formatted_text(text)
        self.on_click = Event(self, on_click)
        self.prefix = prefix
        self.style = style
        self.selected = selected
        self.container = Window(
            FormattedTextControl(
                self._get_text_fragments,
                key_bindings=self._get_key_bindings(),
                focusable=True,
                show_cursor=False,
            ),
            style=f"class:checkbox {style}",
            dont_extend_width=True,
            dont_extend_height=True,
        )

    def __pt_container__(self) -> "Container":
        return self.container


class Text:
    """A text input."""

    def __init__(
        self,
        text: "str" = "",
        style: "str" = "",
        height: "int" = 1,
        width: "Optional[int]" = None,
        show_borders: "Optional[BorderVisibility]" = None,
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
            style=f"class:text-area.text {style}",
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
            show_borders=show_borders,
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
    def __init__(
        self,
        body: "AnyContainer",
        label: "AnyFormattedText",
        height: "Optional[int]" = None,
        width: "Optional[int]" = None,
        style: "str" = "",
        orientation: "WidgetOrientation" = WidgetOrientation.HORIZONTAL,
    ):
        self.body = body
        self.orientation = WidgetOrientation(orientation)
        if self.orientation == WidgetOrientation.HORIZONTAL:
            Split = VSplit
            padding_left = padding_right = 0
            padding_top = padding_bottom = None
        else:
            Split = HSplit
            padding_left = padding_right = None
            padding_top = padding_bottom = 0
        self.container = Split(
            [
                ConditionalContainer(
                    Box(
                        Window(
                            FormattedTextControl(label),
                            dont_extend_width=True,
                            height=height,
                            width=width,
                        ),
                        padding_top=padding_top,
                        padding_right=padding_right,
                        padding_bottom=padding_bottom,
                        padding_left=padding_left,
                    ),
                    filter=Condition(
                        lambda: bool(fragment_list_len(to_formatted_text(label)))
                    ),
                ),
                self.body,
            ],
            padding=1,
            style=style,
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
    def value_str(self) -> "str":
        return " - ".join(map(str, self.value))

    @property
    def max_value_str_len(self) -> "int":
        return (max(map(len, map(str, self.options))) + 1) * len(self._index)

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
        orientation: "WidgetOrientation" = WidgetOrientation.HORIZONTAL,
        handle_char: "str" = "●",
        track_char: "Optional[str]" = None,
        selected_track_char: "Optional[str]" = None,
        style: "str" = "",
    ):
        self.data = data

        self.orientation = orientation
        self.arrows = arrows
        self.show_arrows = to_filter(show_arrows)
        self.handle_char = handle_char
        self.track_char = track_char or (
            "─" if orientation == WidgetOrientation.HORIZONTAL else "│"
        )
        self.selected_track_char = selected_track_char or (
            "━" if orientation == WidgetOrientation.HORIZONTAL else "┃"
        )

        self.has_focus = has_focus(self)
        self.selected_handle = 0
        self.track_len = 0

        self.mouse_handlers = {}
        self.dragging = False
        self.repeat_task: "Optional[asyncio.Task[None]]" = None

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        return (
            max_available_width
            if self.orientation == WidgetOrientation.HORIZONTAL
            else 1
        )

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[GetLinePrefixCallable]",
    ) -> "Optional[int]":
        return (
            1
            if self.orientation == WidgetOrientation.HORIZONTAL
            else min(max_available_height, 10)
        )

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
            handle = self.selected_handle
            if len(self.data.index) == 2:
                if handle == 0 and index > self.data.index[1]:
                    self.selected_handle = 1
                elif handle == 1 and index < self.data.index[0]:
                    self.selected_handle = 0
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
            index = int((len(self.data.options) - 0.5) * pos / self.track_len)
            if self.orientation == WidgetOrientation.VERTICAL:
                index = len(self.data.options) - index
            self.data.set_index(
                self.selected_handle,
                ab=index,
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

    def get_key_bindings(self) -> "Optional[KeyBindingsBase]":
        """Key bindings for the Slider."""
        kb = KeyBindings()

        if self.orientation == WidgetOrientation.HORIZONTAL:

            @kb.add("left")
            def _(event: "KeyPressEvent") -> None:
                self.data.set_index(self.selected_handle, rel=-1)

            @kb.add("right")
            def _(event: "KeyPressEvent") -> None:
                self.data.set_index(self.selected_handle, rel=1)

        else:

            @kb.add("down")
            def _(event: "KeyPressEvent") -> None:
                self.data.set_index(self.selected_handle, rel=-1)

            @kb.add("up")
            def _(event: "KeyPressEvent") -> None:
                self.data.set_index(self.selected_handle, rel=1)

        return kb

    def render_lines(self, width: "int", height: "int") -> "List[StyleAndTextTyples]":

        ft = []
        mouse_handlers = []

        size = width if self.orientation == WidgetOrientation.HORIZONTAL else height
        track_len = size - len(self.data.index)

        if self.show_arrows():
            # The arrows take up 4 characters: remove them from the track length
            track_len -= 4
            ft += [("class:slider.arrow,left", self.arrows[0]), ("", " ")]
            mouse_handlers += [
                partial(self.mouse_handler_arrow, n=-1),
                self.mouse_handler_scroll,
            ]

        # First bit of track
        left_len = floor(track_len * self.data.index[0] / (len(self.data.options) - 1))
        ft.append(("class:slider.track", self.track_char * left_len))
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
            middle_len = ceil(
                track_len
                * (self.data.index[-1] - self.data.index[0])
                / (len(self.data.options) - 1)
            )
            ft.append(
                ("class:slider.track.selected", self.selected_track_char * middle_len)
            )
            mouse_handlers += [
                partial(
                    self.mouse_handler_track,
                    index=int((len(self.data.options) - 0.5) * i / track_len),
                )
                for i in range(left_len, left_len + middle_len)
            ]
            # Second handle
            ft.append(self._draw_handle(1))
            mouse_handlers.append(partial(self.mouse_handler_handle, handle=1))

        # Last bit of track
        right_len = track_len - left_len - middle_len
        ft.append(("class:slider.track", self.track_char * right_len))
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

        self.track_len = track_len

        if self.orientation == WidgetOrientation.VERTICAL:
            mouse_handlers = mouse_handlers[::-1]
            output = [[x] for x in explode_text_fragments(ft)][::-1]
        else:
            output = [ft]

        self.mouse_handlers = dict(enumerate(mouse_handlers))

        return output

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        if self.orientation == WidgetOrientation.HORIZONTAL:
            loc = mouse_event.position.x
        else:
            loc = mouse_event.position.y
        self._mouse_handler(mouse_event, loc=loc)


class Slider:
    """A slider input widget.

    - ───⬤━━━━⬤────── + [9-18]

    """

    def _validate_readout(self, text: "str") -> "Optional[T]":
        try:
            values = [self.data_type(value.strip()) for value in text.split("-")]
        except Exception:
            return None
        else:
            if all(value in self.data.options for value in values):
                order = {v: i for i, v in enumerate(self.data.options)}
                return sorted(values, key=lambda x: order[x])

    def _value_changed(self, slider_data: "SliderData") -> "None":
        """Sets the readout text when the slider value changes."""
        self.readout.text = self.data.value_str

    def _accept_handler(self, buffer: "Buffer") -> "bool":
        if values := self._validate_readout(buffer.text):
            for i, value in enumerate(values):
                self.data.set_index(
                    handle=i, ab=self.data.options.index(value), fire=False
                )
            # Trigger the event once all the values have been updated
            self.data.on_value_change.fire()
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
        orientation: "Union[WidgetOrientation, str]" = WidgetOrientation.HORIZONTAL,
        on_value_change: "Optional[Callable[[Slider], None]]" = None,
    ) -> None:
        self.show_readout = to_filter(show_readout)
        self.orientation = WidgetOrientation(orientation)
        self.data_type = type(options[0])

        self.data = SliderData(
            options=options,
            index=(index,) if isinstance(index, int) else tuple(index),
            on_value_change=on_value_change,
        )
        self.data.on_value_change += self._value_changed
        self.slider_control = SliderControl(
            self.data,
            arrows=arrows,
            show_arrows=to_filter(show_arrows),
            orientation=self.orientation,
        )

        self.readout = Text(
            text=self.data.value_str,
            height=1,
            width=min(self.data.max_value_str_len, 10),
            validation=lambda x: self._validate_readout(x) is not None,
            accept_handler=self._accept_handler,
        )
        Split = VSplit if self.orientation == WidgetOrientation.HORIZONTAL else HSplit
        self.container = Split(
            [
                Box(
                    Window(
                        self.slider_control,
                    ),
                ),
                ConditionalContainer(self.readout, filter=self.show_readout),
            ],
            padding=1,
            style=style,
        )

    def __pt_container__(self) -> "Container":
        return self.container


class ProgressControl(UIControl):

    hchars = ("", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█")
    vchars = ("", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")

    def __init__(
        self,
        start: "Number" = 0,
        stop: "Number" = 100,
        step: "Number" = 1,
        value: "Number" = 0,
        orientation: "WidgetOrientation" = WidgetOrientation.HORIZONTAL,
    ):
        self.start = start
        self.stop = stop
        self.step = step
        self.value = value
        self.orientation = orientation

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        return (
            max_available_width
            if self.orientation == WidgetOrientation.HORIZONTAL
            else 1
        )

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[GetLinePrefixCallable]",
    ) -> "Optional[int]":
        return (
            1
            if self.orientation == WidgetOrientation.HORIZONTAL
            else min(max_available_height, 10)
        )

    def render(self, width: int, height: int):
        length = width if self.orientation == WidgetOrientation.HORIZONTAL else height
        size = int(self.value / (self.stop - self.start) * length * 8) / 8
        remainder = int(size % 1 * 8)
        chars = (
            self.vchars
            if self.orientation == WidgetOrientation.VERTICAL
            else self.hchars
        )

        ft = [
            ("class:progress", chars[8] * int(size)),
            ("class:progress", chars[remainder]),
            ("class:progress", " " * int(length - size)),
        ]

        if self.orientation == WidgetOrientation.VERTICAL:
            return [[x] for x in explode_text_fragments(ft)][::-1]
        else:
            return [ft]

    def create_content(self, width: "int", height: "int") -> "UIContent":
        def get_content() -> UIContent:
            fragment_lines = self.render(width, height)

            return UIContent(
                get_line=lambda i: fragment_lines[i],
                line_count=len(fragment_lines),
                show_cursor=False,
            )

        key = (width, self.start, self.stop, self.step, self.value)
        return self._content_cache.get(key, get_content)


class Progress:
    def __init__(
        self,
        start: "Number" = 0,
        stop: "Number" = 100,
        step: "Number" = 1,
        value: "Number" = 0,
        orientation: "Union[WidgetOrientation, str]" = WidgetOrientation.HORIZONTAL,
        style: "str" = "",
    ) -> "None":
        self.style = style
        self.orientation = WidgetOrientation(orientation)
        self.control = ProgressControl(
            start=start,
            stop=stop,
            step=step,
            value=value,
            orientation=self.orientation,
        )
        self.container = Box(
            Border(
                Window(
                    self.control,
                    style=self.add_style("class:progress"),
                    dont_extend_width=self.orientation == WidgetOrientation.VERTICAL,
                ),
                border=WidgetGrid,
                style=self.add_style("class:progress,progress.border"),
            ),
            width=1 if self.orientation == WidgetOrientation.VERTICAL else None,
        )

    @property
    def value(self) -> "Number":
        return self.control.value

    @value.setter
    def value(self, value) -> "None":
        self.control.value = value

    def add_style(self, extra):
        def _style():
            if callable(self.style):
                return f"{self.style()} {extra}"
            else:
                return f"{self.style} {extra}"

        return _style

    def __pt_container__(self) -> "Container":
        return self.container


class Dropdown:
    """A drop-down selection widget."""

    def _text(self) -> "StyleAndTextTuples":
        formatted_options = self.formatted_options
        max_width = max(fragment_list_width(x) for x in formatted_options)
        ft = align(FormattedTextAlign.LEFT, formatted_options[self.index], max_width)
        ft += [("", " "), ("class:arrow", self.arrow)]
        return ft

    def _menu_fragments(self) -> "StyleAndTextTuples":
        ft = []
        formatted_options = self.formatted_options
        max_width = max(fragment_list_width(x) for x in formatted_options)
        for i, option in enumerate(formatted_options):
            # Pad each option
            option = align(FormattedTextAlign.LEFT, option, width=max_width + 2)
            item_style = "class:hovered" if i == self.hovered else ""
            handler = partial(self.mouse_handler, i)
            ft.extend(
                [
                    (item_style, " ", handler),
                    *[
                        (f"{item_style} {style}", text, handler)
                        for style, text, *_ in option
                    ],
                    (item_style, " ", handler),
                    ("", "\n"),
                ]
            )
        # Remoe the last newline
        ft.pop()
        return ft

    def _get_key_bindings(self) -> "KeyBindings":
        "Key bindings for the Button."
        kb = KeyBindings()

        menu_visible = Condition(lambda: self.menu_visible)

        @kb.add("enter", filter=menu_visible)
        @kb.add(" ", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = self.hovered
            self.menu_visible = False
            self.button.selected = False
            self.on_change.fire()

        @kb.add("home", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = 0

        @kb.add("up", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min(self.hovered - 1, len(self.options) - 1))

        @kb.add("down", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min(self.hovered + 1, len(self.options) - 1))

        @kb.add("end", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = len(self.options) - 1

        @kb.add("home", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = 0

        @kb.add("up", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = max(0, min(self.index - 1, len(self.options) - 1))

        @kb.add("down", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = max(0, min(self.index + 1, len(self.options) - 1))

        @kb.add("end", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = len(self.options) - 1

        return kb

    def __init__(
        self,
        options: "List[AnyFormattedText]",
        index: "int" = 0,
        on_change: "Optional[Callable[[Dropdown], None]]" = None,
        style: "str" = "",
        arrow: "str" = "⯆",
    ):
        self.menu_visible = False
        self.options = options
        self.index = index
        self.on_change = Event(self, on_change)
        self.hovered = index
        self.arrow = arrow
        self.button = Button(
            self._text,
            on_mouse_down=self.toggle_menu,
            style=f"class:dropdown {style}",
            key_bindings=self._get_key_bindings(),
        )
        self.container = self.button
        # self.container = FloatContainer(
        # content=self.button,
        # floats=[],
        # )
        self.float_ = Float(
            ConditionalContainer(
                Window(
                    FormattedTextControl(self._menu_fragments),
                    style=f"class:dropdown,dropdown.menu {style}",
                ),
                filter=Condition(lambda: self.menu_visible) & has_focus(self),
            ),
            xcursor=True,
            ycursor=True,
        )
        get_app().add_float(self.float_)

    def mouse_handler(self, i, mouse_event: "MouseEvent"):
        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            self.hovered = i
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.index = i
            self.menu_visible = False
            self.button.selected = False
            self.on_change.fire()

    @property
    def formatted_options(self):
        return [to_formatted_text(x) for x in self.options]

    def toggle_menu(self, button: "Button"):
        self.menu_visible = not self.menu_visible
        self.hovered = self.index

    def __pt_container__(self) -> "Container":
        return self.container


class Selection:
    def _get_text_fragments(self) -> "StyleAndTextTuples":
        ft = []
        formatted_options = self.formatted_options
        max_width = max(fragment_list_width(x) for x in formatted_options)
        for i, option in enumerate(formatted_options):
            option = align(FormattedTextAlign.LEFT, option, width=max_width)
            cursor = "[SetCursorPosition]" if self.mask[i] else ""
            style = "class:selected" if self.mask[i] else ""
            if self.hovered == i and self.multiple() and self.has_focus():
                style += " class:hovered"
            ft_option = [
                (f"class:prefix {cursor}", self.prefix[self.mask[i]]),
                # Add space between the tickbox and the text
                ("", " "),
                *option,
                ("", " "),
                ("", "\n"),
            ]
            handler = partial(self.mouse_handler, i)
            ft += [
                (f"{fragment_style} {style}", text, handler)
                for fragment_style, text, *_ in ft_option
            ]
        ft.pop()
        return ft

    def _get_key_bindings(self) -> "KeyBindings":
        """Key bindings for the radio-buttons."""
        kb = KeyBindings()

        @kb.add("home", filter=~self.multiple)
        def _(event: "KeyPressEvent") -> "None":
            self.toggle_item(0)

        @kb.add("up", filter=~self.multiple)
        def _(event: "KeyPressEvent") -> "None":
            self.toggle_item(max(0, min((self.index or 0) - 1, len(self.options) - 1)))

        @kb.add("down", filter=~self.multiple)
        def _(event: "KeyPressEvent") -> "None":
            self.toggle_item(max(0, min((self.index or 0) + 1, len(self.options) - 1)))

        @kb.add("end", filter=~self.multiple)
        def _(event: "KeyPressEvent") -> "None":
            self.toggle_item(len(self.options) - 1)

        @kb.add("enter", filter=self.multiple)
        @kb.add(" ", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.toggle_item(self.hovered)

        @kb.add("home", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = 0

        @kb.add("up", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min(self.hovered - 1, len(self.options) - 1))

        @kb.add("down", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min(self.hovered + 1, len(self.options) - 1))

        @kb.add("end", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = len(self.options) - 1

        return kb

    def __init__(
        self,
        options: "List[AnyFormattedText]",
        index: "int" = 0,
        indices: "Tuple[int]" = (),
        on_change: "Optional[Callable[[Dropdown], None]]" = None,
        style: "str" = "",
        prefix: "Tuple[str, str]" = ("", ""),  # ○ ◉ 🔘 ⊙ ◎ ▣ □ ◈ ◇
        multiple: "FilterOrBool" = False,
    ):
        self.menu_visible = False
        self.options = options
        self.hovered = index
        self.multiple = to_filter(multiple)
        self.mask = [False for _ in self.options]
        if not indices:
            indices = (index,)
        self.indices = indices

        self.on_change = Event(self, on_change)
        self.prefix = prefix
        self.container = Window(
            FormattedTextControl(
                self._get_text_fragments,
                key_bindings=self._get_key_bindings(),
                focusable=True,
                show_cursor=False,
            ),
            dont_extend_width=True,
            dont_extend_height=True,
            style=f"class:selection {style}",
        )
        self.has_focus = has_focus(self)

    def toggle_item(self, index) -> "List[bool]":
        if not self.multiple() and any(self.mask):
            self.mask = [False for _ in self.options]
        self.mask[index] = not self.mask[index]
        self.on_change.fire()

    @property
    def index(self) -> "Optional[int]":
        return next((x for x in self.indices), None)

    @index.setter
    def index(self, value: "int") -> "None":
        self.indices = (value,)

    @property
    def indices(self) -> "Tuple[int]":
        return tuple(i for i, m in enumerate(self.mask) if m)

    @indices.setter
    def indices(self, values: "Tuple[int]") -> "None":
        self.mask = [i in values for i in range(len(self.options))]

    @property
    def formatted_options(self):
        return [to_formatted_text(x) for x in self.options]

    def mouse_handler(self, i, mouse_event: "MouseEvent"):
        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            self.hovered = i
        elif mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.toggle_item(i)

    def __pt_container__(self) -> "Container":
        return self.container
