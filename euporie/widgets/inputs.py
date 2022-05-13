import asyncio
import logging
from abc import ABCMeta, abstractmethod
from enum import Enum
from functools import partial
from math import ceil, floor
from typing import TYPE_CHECKING, cast

from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.completion.base import ConditionalCompleter
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.filters import Always, Condition, FilterOrBool, has_focus, to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_len, fragment_list_width
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    KeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.processors import AfterInput, ConditionalProcessor
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from prompt_toolkit.validation import Validator
from prompt_toolkit.widgets.base import Box, TextArea

from euporie.app.current import get_edit_app as get_app
from euporie.border import BorderVisibility, InnerEdgeGridStyle
from euporie.convert.base import convert, find_route
from euporie.formatted_text.utils import (
    FormattedTextAlign,
    add_border,
    align,
    apply_style,
)
from euporie.margins import ScrollbarMargin
from euporie.widgets.decor import Border
from euporie.widgets.display import Display
from euporie.widgets.layout import ConditionalSplit

if TYPE_CHECKING:
    from numbers import Number
    from typing import (
        Any,
        Callable,
        ClassVar,
        Dict,
        List,
        Optional,
        Tuple,
        Type,
        TypeVar,
        Union,
    )

    from prompt_toolkit.buffer import Buffer, BufferAcceptHandler
    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer, Container
    from prompt_toolkit.layout.controls import GetLinePrefixCallable

    from euporie.border import GridStyle

    T = TypeVar("T", str, int, float)


log = logging.getLogger(__name__)


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
        if callable(self.style):
            style = self.style()
        else:
            style = self.style
        if self.selected:
            return f"{style} class:button,selection"
        else:
            return f"{style} class:button"

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
        style: "Union[str, Callable[[], str]]" = "",
        border: "Optional[GridStyle]" = InnerEdgeGridStyle,
        show_borders: "Optional[BorderVisibility]" = None,
        selected: "bool" = False,
        key_bindings: "Optional[KeyBindings]" = None,
    ) -> None:
        self.text = text
        self.on_mouse_down = Event(self, on_mouse_down)
        self.on_click = Event(self, on_click)
        self._width = width
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
                    style="class:face",
                ),
                style=self._get_style,
                dont_extend_width=True,
                dont_extend_height=True,
            ),
            border=border,
            show_borders=show_borders,
            style=lambda: f"{self._get_style()} class:border",
        )

    @property
    def width(self) -> "int":
        if self._width is not None:
            return self._width
        else:
            return fragment_list_width(to_formatted_text(self.text)) + 2

    @width.setter
    def width(self, value: "Optional[int]") -> "None":
        self._width = value

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
            self.selected = True
            self.on_mouse_down.fire()
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.selected = False
            self.on_click.fire()

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class Swatch:
    def __init__(
        self,
        color: "Union[str, Callable[[], str]]" = "#FFFFFF",
        width: "int" = 2,
        height: "int" = 1,
        style: "str" = "class:swatch",
        show_borders: "Optional[BorderVisibility]" = None,
    ):
        self.color = color
        self.style = style

        self.container = Border(
            Window(char=" ", style=self.get_style, width=width, height=height),
            border=InnerEdgeGridStyle,
            style=f"{self.style} class:border,inset",
            show_borders=show_borders,
        )

    def get_style(self):
        if callable(self.color):
            color = self.color()
        else:
            color = self.color
        return f"{self.style} bg:{color} "

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class ToggleableWidget(metaclass=ABCMeta):
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

    def _get_key_bindings(self) -> "Optional[KeyBindingsBase]":
        """Key bindings for the Toggler."""
        kb = KeyBindings()

        @kb.add(" ")
        @kb.add("enter")
        def _(event: "KeyPressEvent") -> None:
            self.toggle()


class ToggleButton(Button, ToggleableWidget):
    """"""

    def __init__(
        self,
        text: "AnyFormattedText",
        on_click: "Optional[Callable[[ToggleableWidget], None]]" = None,
        on_mouse_down: "Optional[Callable[[Button], None]]" = None,
        width: "Optional[int]" = None,
        style: "str" = "",
        border: "Optional[GridStyle]" = InnerEdgeGridStyle,
        show_borders: "Optional[BorderVisibility]" = None,
        selected: "bool" = False,
        key_bindings: "Optional[KeyBindings]" = None,
    ) -> None:
        super().__init__(
            text=text,
            on_click=on_click,
            on_mouse_down=on_mouse_down,
            width=width,
            style=style,
            border=border,
            show_borders=show_borders,
            selected=selected,
            key_bindings=key_bindings,
        )


class Checkbox(ToggleableWidget):
    """"""

    def _get_text_fragments(self) -> "StyleAndTextTuples":
        selected_style = "class:selection" if self.selected else ""
        ft = [
            (
                f"[SetCursorPosition] class:checkbox,prefix{',selection' if self.selected else ''}",
                self.prefix[int(self.selected)],
            ),
            # Add space between the tickbox and the text
            ("", " " if fragment_list_len(self.text) else ""),
            *self.text,
        ]
        ft = [(style, text, self.mouse_handler) for style, text, *_ in ft]
        return ft

    def __init__(
        self,
        text: "AnyFormattedText" = "",
        on_click: "Optional[Callable[[ToggleableWidget], None]]" = None,
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

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class Text:
    """A text input."""

    def __init__(
        self,
        text: "str" = "",
        style: "str" = "",
        height: "int" = 1,
        min_height: "int" = 1,
        multiline: "bool" = False,
        width: "Optional[int]" = None,
        options: "Optional[Union[List[str], Callable[[], List[str]]]]" = None,
        show_borders: "Optional[BorderVisibility]" = None,
        on_text_changed: "Optional[Callable[[Buffer], None]]" = None,
        validation: "Optional[Callable[[str], bool]]" = None,
        accept_handler: "Optional[BufferAcceptHandler]" = None,
        placeholder: "Optional[str]" = None,
        input_processors: "Optional[List[Processor]]" = None,
    ):
        self.style = style
        self.options = options

        self.placeholder = placeholder

        self.text_area = TextArea(
            str(text),
            multiline=multiline,
            height=Dimension(min=min_height, max=height, preferred=height),
            width=width,
            focusable=True,
            focus_on_click=True,
            style=f"class:text,text-area {style}",
            validator=Validator.from_callable(validation) if validation else None,
            accept_handler=accept_handler,
            completer=ConditionalCompleter(
                WordCompleter(self.options),
                filter=Condition(lambda: bool(self.options)),
            ),
            input_processors=[
                ConditionalProcessor(
                    AfterInput(
                        lambda: self.placeholder, style="class:text,placeholder"
                    ),
                    filter=Condition(
                        lambda: self.placeholder is not None and self.buffer.text == ""
                    ),
                ),
            ]
            + (input_processors or []),
        )
        self.buffer = self.text_area.buffer

        # Patch text area control's to expand to fill available width
        self.text_area.control.preferred_width = self.preferred_width

        if multiline:
            self.text_area.window.right_margins += [ScrollbarMargin()]
        if on_text_changed:
            self.text_area.buffer.on_text_changed += on_text_changed
        if validation:
            self.text_area.buffer.validate_while_typing = Always()
        self.container = Border(
            self.text_area,
            border=InnerEdgeGridStyle,
            style=self.border_style,
            show_borders=show_borders,
        )

    def preferred_width(self, max_available_width: "int") -> "int":
        """Ensure text box expands to available width.

        Args:
            max_available_width: The maximum available width

        Returns:
            The desired width, which is the maximum available
        """
        return max_available_width

    def border_style(self):
        if self.text_area.buffer.validation_state == ValidationState.INVALID:
            return f"{self.style} class:text,border,invalid"
        else:
            return f"{self.style} class:text,border"

    @property
    def text(self) -> "str":
        return self.buffer.text

    @text.setter
    def text(self, value: "str") -> "None":
        self.buffer.text = value

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class Label:
    def __init__(
        self, value: "AnyFormattedText", style: "Union[str, Callable[[], str]]" = ""
    ):
        self.value = value
        self.control = FormattedTextControl(self.get_value, focusable=False)
        self.container = Window(
            self.control,
            style=style,
            dont_extend_width=True,
        )

    def get_value(self):
        value = self.value
        if callable(value):
            data = value()
        else:
            data = value
        return convert(
            data=data,
            from_="markdown",
            to="formatted_text",
        )

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class LabelledWidget:
    def __init__(
        self,
        body: "AnyContainer",
        label: "AnyFormattedText",
        height: "Optional[int]" = None,
        width: "Optional[int]" = None,
        style: "str" = "",
        vertical: "FilterOrBool" = False,
    ):
        self.body = body
        self.vertical = to_filter(vertical)
        padding_left = padding_right = lambda: None if self.vertical() else 0
        padding_top = padding_bottom = lambda: 0 if self.vertical() else None
        self.container = ConditionalSplit(
            self.vertical,
            [
                ConditionalContainer(
                    Box(
                        Label(label, style=style),
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

    def __pt_container__(self) -> "AnyContainer":
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
        vertical: "FilterOrBool" = False,
    ):
        self.start = start
        self.stop = stop
        self.step = step
        self.value = value
        self.vertical = to_filter(vertical)

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        return 1 if self.vertical() else max_available_width

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[GetLinePrefixCallable]",
    ) -> "Optional[int]":
        return min(max_available_height, 10) if self.vertical() else 1

    def render(self, width: int, height: int):
        vertical = self.vertical()
        length = height if vertical else width
        size = int(self.value / (self.stop - self.start) * length * 8) / 8
        remainder = int(size % 1 * 8)
        chars = self.vchars if vertical else self.hchars

        ft = [
            ("class:progress", chars[8] * int(size)),
            ("class:progress", chars[remainder]),
            ("class:progress", " " * int(length - size)),
        ]

        if vertical:
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
        vertical: "FilterOrBool" = False,
        style: "Union[str, Callable[[], str]]" = "",
    ) -> "None":
        self.style = style
        self.vertical = to_filter(vertical)
        self.control = ProgressControl(
            start=start,
            stop=stop,
            step=step,
            value=value,
            vertical=self.vertical,
        )
        self.container = Box(
            Border(
                Window(
                    self.control,
                    style=self.add_style("class:progress"),
                    dont_extend_width=self.vertical,
                ),
                border=InnerEdgeGridStyle,
                style=self.add_style("class:progress,border"),
            ),
            width=lambda: 1 if self.vertical() else None,
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

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class SelectableWidget(metaclass=ABCMeta):
    def __init__(
        self,
        options: "List[T]",
        index: "int" = 0,
        indices: "Optional[List[int]]" = None,
        multiple: "FilterOrBool" = False,
        on_change: "Optional[Callable[[SelectableWidget], None]]" = None,
        style: "Union[str, Callable[[], str]]" = "",
    ):
        self.options: "List[T]" = options
        self.mask: "List[bool]" = [False for _ in self.options]
        if indices is None:
            indices = [index]
        self.indices = indices
        self.multiple = to_filter(multiple)
        self.on_change = Event(self, on_change)
        self._style = style

        self.hovered: "Optional[int]" = index
        self.container = self.load_container()
        self.has_focus = has_focus(self)

    @abstractmethod
    def load_container(self) -> "AnyContainer":
        ...

    @property
    def style(self) -> "str":
        if callable(self._style):
            return self._style()
        else:
            return self._style

    @style.setter
    def style(self, value: "Union[str, Callable[[], str]]") -> "None":
        self._style = value

    def key_bindings(self) -> "KeyBindings":
        """Key bindings for the select."""
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
            if self.hovered is not None:
                self.toggle_item(self.hovered)

        @kb.add("home", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = 0

        @kb.add("up", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))

        @kb.add("down", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))

        @kb.add("end", filter=self.multiple)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = len(self.options) - 1

        return kb

    def toggle_item(self, index: "int") -> "None":
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
    def indices(self) -> "List[int, ...]":
        return [i for i, m in enumerate(self.mask) if m]

    @indices.setter
    def indices(self, values: "Tuple[int]") -> "None":
        self.mask = [i in values for i in range(len(self.options))]
        log.debug(values)

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

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class Select(SelectableWidget):
    def __init__(
        self,
        options: "List[T]",
        index: "int" = 0,
        indices: "Optional[List[int]]" = None,
        multiple: "FilterOrBool" = False,
        on_change: "Optional[Callable[[SelectableWidget], None]]" = None,
        style: "Union[str, Callable[[], str]]" = "",
        prefix: "Tuple[str, str]" = ("", ""),
        border: "Optional[GridStyle]" = InnerEdgeGridStyle,
        show_borders: "Optional[BorderVisibility]" = None,
    ) -> "None":
        self.prefix = prefix
        self.border = border
        self.show_borders = show_borders
        super().__init__(
            options=options,
            index=index,
            indices=indices,
            multiple=multiple,
            on_change=on_change,
            style=style,
        )

    def text_fragments(self) -> "StyleAndTextTuples":
        ft: "StyleAndTextTuples" = []
        formatted_options = self.formatted_options
        max_width = max(fragment_list_width(x) for x in formatted_options)
        for i, option in enumerate(formatted_options):
            option = align(FormattedTextAlign.LEFT, option, width=max_width)
            cursor = "[SetCursorPosition]" if self.mask[i] else ""
            style = "class:selection" if self.mask[i] else ""
            if self.hovered == i and self.multiple() and self.has_focus():
                style += " class:hovered"
            ft_option = [
                (f"class:prefix {cursor}", self.prefix[self.mask[i]]),
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

    def load_container(self) -> "AnyContainer":
        return Border(
            Window(
                FormattedTextControl(
                    self.text_fragments,
                    key_bindings=self.key_bindings(),
                    focusable=True,
                    show_cursor=False,
                ),
                dont_extend_width=True,
                dont_extend_height=True,
                style=f"class:select {self.style}",
            ),
            border=self.border,
            show_borders=self.show_borders,
            style="class:select,border",
        )


class Dropdown(SelectableWidget):
    def __init__(
        self,
        options: "List[T]",
        index: "int" = 0,
        indices: "Optional[List[int]]" = None,
        multiple: "FilterOrBool" = False,
        on_change: "Optional[Callable[[SelectableWidget], None]]" = None,
        style: "Union[str, Callable[[], str]]" = "",
        arrow: "str" = "⯆",
    ):
        self.menu_visible: "bool" = False
        self.arrow: "str" = arrow
        super().__init__(
            options=options,
            index=index,
            indices=indices,
            multiple=multiple,
            on_change=on_change,
            style=style,
        )

        self.menu = Float(
            ConditionalContainer(
                Window(
                    FormattedTextControl(
                        self.menu_fragments,
                    ),
                    style=f"class:dropdown,dropdown.menu {self.style}",
                ),
                filter=Condition(lambda: self.menu_visible) & self.has_focus,
            ),
            xcursor=True,
            ycursor=True,
        )
        get_app().add_float(self.menu)

    def load_container(self) -> "AnyContainer":
        self.button = Button(
            self.button_text,
            on_mouse_down=self.toggle_menu,
            style=f"class:dropdown {self.style}",
            key_bindings=self.key_bindings(),
        )
        return self.button

    def button_text(self) -> "StyleAndTextTuples":
        formatted_options = self.formatted_options
        max_width = max(fragment_list_width(x) for x in formatted_options)
        ft = align(FormattedTextAlign.LEFT, formatted_options[self.index], max_width)
        ft += [("", " " if self.arrow else ""), ("class:arrow", self.arrow)]
        return ft

    def toggle_menu(self, button: "Button") -> "None":
        self.menu_visible = not self.menu_visible
        self.hovered = self.index

    def menu_fragments(self) -> "StyleAndTextTuples":
        ft: "StyleAndTextTuples" = []
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
        # Remove the last newline
        ft.pop()
        return ft

    def mouse_handler(self, i, mouse_event: "MouseEvent"):
        super().mouse_handler(i, mouse_event)
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.menu_visible = False
            self.button.selected = False

    def key_bindings(self) -> "KeyBindings":

        menu_visible = Condition(lambda: self.menu_visible)
        kb = KeyBindings()

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
            self.hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))

        @kb.add("down", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))

        @kb.add("end", filter=menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.hovered = len(self.options) - 1

        @kb.add("home", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = 0

        @kb.add("up", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = max(0, min((self.index or 0) - 1, len(self.options) - 1))

        @kb.add("down", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = max(0, min((self.index or 0) + 1, len(self.options) - 1))

        @kb.add("end", filter=~menu_visible)
        def _(event: "KeyPressEvent") -> None:
            self.index = len(self.options) - 1

        return kb


class ToggleButtons(SelectableWidget):
    def __init__(
        self,
        options: "List[T]",
        index: "int" = 0,
        indices: "Optional[List[int]]" = None,
        multiple: "FilterOrBool" = False,
        on_change: "Optional[Callable[[SelectableWidget], None]]" = None,
        style: "Union[str, Callable[[], str]]" = "",
        border: "GridStyle" = InnerEdgeGridStyle,
    ):
        self.border = border
        super().__init__(
            options=options,
            index=index,
            indices=indices,
            multiple=multiple,
            on_change=on_change,
            style=style,
        )

    def load_container(self) -> "AnyContainer":
        show_borders_values = [BorderVisibility(True, False, True, True)]
        if len(self.options) > 1:
            show_borders_values += [
                *[
                    BorderVisibility(True, False, True, False)
                    for _ in self.options[1:-1]
                ],
                BorderVisibility(True, True, True, False),
            ]

        self.buttons = [
            ToggleButton(
                text=option,
                selected=selected,
                on_click=partial(lambda index, button: self.toggle_item(index), i),
                border=self.border,
                show_borders=show_borders,
                style=self.style,
            )
            for i, (option, selected, show_borders) in enumerate(
                zip(self.options, self.mask, show_borders_values)
            )
        ]
        self.on_change += self.update_buttons
        return VSplit(
            self.buttons,
            style="class:toggle-buttons",
        )

    def update_buttons(self, widget: "Optional[SelectableWidget]" = None):
        for i, selected in enumerate(self.mask):
            self.buttons[i].selected = selected

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class SliderControl(UIControl):
    def __init__(
        self,
        slider: "Slider",
        show_arrows: "FilterOrBool" = True,
        handle_char: "str" = "●",
        track_char: "Optional[str]" = None,
        selected_track_char: "Optional[str]" = None,
        style: "str" = "",
    ):
        self.slider = slider

        self.track_char = track_char
        self.selected_track_char = selected_track_char
        self.show_arrows = to_filter(show_arrows)
        self.handle_char = handle_char

        self.selected_handle = 0
        self.track_len = 0

        self.mouse_handlers: "Dict[int, Callable[..., NotImplementedOrNone]]" = {}
        self.dragging = False
        self.repeat_task: "Optional[asyncio.Task[None]]" = None

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        return 1 if self.slider.vertical() else max_available_width

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[GetLinePrefixCallable]",
    ) -> "Optional[int]":
        return min(max_available_height, 10) if self.slider.vertical() else 1

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

        key = (
            width,
            self.slider.vertical(),
            tuple(self.slider.options),
            tuple(self.slider.mask),
            self.selected_handle,
            self.slider.has_focus(),
        )
        return self._content_cache.get(key, get_content)

    def set_index(
        self,
        handle: "int" = 0,
        ab: "Optional[int]" = None,
        rel: "Optional[int]" = None,
        fire: "bool" = True,
    ) -> "None":
        assert ab is not None or rel is not None
        if rel is not None:
            ab = self.slider.indices[handle] + rel
        assert ab is not None
        ab = min(len(self.slider.options) - 1, max(0, ab))
        indices = dict(enumerate(self.slider.indices))
        # Do not allow both handles to have the same value
        if ab not in indices.values():
            indices.update({handle: ab})
            self.slider.mask = [
                i in sorted(indices.values()) for i in range(len(self.slider.options))
            ]
            if fire:
                self.slider.on_change.fire()

    @property
    def selected_handle(self) -> "int":
        return self._selected_handle

    @selected_handle.setter
    def selected_handle(self, value: "int"):
        value = max(0, min(value, sum(self.slider.mask)))
        self._selected_handle = value

    def _draw_handle(self, n: "int") -> "OneStyleAndTextTuple":
        selected_style = "class:selection" if self.selected_handle == n else ""
        focused_style = "class:focused" if self.slider.has_focus() else ""
        return (
            f"class:handle {selected_style} {focused_style}",
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
            if sum(self.slider.mask) == 2:
                if handle == 0 and index > self.slider.indices[1]:
                    self.selected_handle = 1
                elif handle == 1 and index < self.slider.indices[0]:
                    self.selected_handle = 0
            self.set_index(self.selected_handle, ab=index)
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
            self.set_index(self.selected_handle, rel=n)
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
    ) -> "NotImplementedOrNone":
        if handle is None:
            handle = self.selected_handle
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.set_index(handle, rel=1)
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.set_index(handle, rel=-1)
        else:
            return NotImplemented
        return None

    def mouse_handler_(
        self, mouse_event: "MouseEvent", loc: "int"
    ) -> "NotImplementedOrNone":
        # Handle dragging
        if self.dragging and mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            n_options = len(self.slider.options)
            pos = loc
            if self.show_arrows():
                pos -= 2
            pos = max(0, min(self.track_len, pos))
            index = int((n_options - 0.5) * pos / self.track_len)
            if self.slider.vertical():
                index = n_options - index
            self.set_index(
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
        self,
        mouse_event: "MouseEvent",
        handler: "Callable[..., NotImplementedOrNone]",
        timeout: "float" = 0.25,
        **kwargs,
    ) -> "None":
        """Repeat a mouse event after a timeout."""
        await asyncio.sleep(timeout)
        handler(mouse_event, repeated=True, **kwargs)
        get_app().invalidate()

    def get_key_bindings(self) -> "Optional[KeyBindingsBase]":
        """Key bindings for the Slider."""
        kb = KeyBindings()

        if self.slider.vertical():

            @kb.add("down")
            def _(event: "KeyPressEvent") -> None:
                self.set_index(self.selected_handle, rel=-1)

            @kb.add("up")
            def _(event: "KeyPressEvent") -> None:
                self.set_index(self.selected_handle, rel=1)

        else:

            @kb.add("left")
            def _(event: "KeyPressEvent") -> None:
                self.set_index(self.selected_handle, rel=-1)

            @kb.add("right")
            def _(event: "KeyPressEvent") -> None:
                self.set_index(self.selected_handle, rel=1)

        return kb

    def render_lines(self, width: "int", height: "int") -> "List[StyleAndTextTuples]":

        ft = []
        mouse_handlers: "List[Callable[..., NotImplementedOrNone]]" = []

        vertical = self.slider.vertical()
        size = height if vertical else width
        n_handles = sum(self.slider.mask)
        n_options = len(self.slider.options)
        indices = self.slider.indices
        track_len = size - n_handles

        track_char = self.track_char or ("│" if vertical else "─")
        selected_track_char = self.selected_track_char or ("┃" if vertical else "━")

        if self.show_arrows():
            # The arrows take up 4 characters: remove them from the track length
            track_len -= 4
            ft += [
                *to_formatted_text(self.slider.arrows[0], "class:arrow,left"),
                ("", " "),
            ]
            mouse_handlers += [
                partial(self.mouse_handler_arrow, n=-1),
                self.mouse_handler_scroll,
            ]

        # First bit of track
        left_len = floor(track_len * indices[0] / (n_options - 1))
        ft.append(("class:track", track_char * left_len))
        mouse_handlers += [
            partial(
                self.mouse_handler_track,
                index=int((n_options - 0.5) * i / track_len),
            )
            for i in range(0, left_len)
        ]

        # First handle
        ft.append((self._draw_handle(0)))
        mouse_handlers.append(partial(self.mouse_handler_handle, handle=0))

        # Middle bit of track
        middle_len = 0
        if n_handles > 1:
            middle_len = ceil(track_len * (indices[-1] - indices[0]) / (n_options - 1))
            ft.append(("class:track,selection", selected_track_char * middle_len))
            mouse_handlers += [
                partial(
                    self.mouse_handler_track,
                    index=int((n_options - 0.5) * i / track_len),
                )
                for i in range(left_len, left_len + middle_len)
            ]
            # Second handle
            ft.append(self._draw_handle(1))
            mouse_handlers.append(partial(self.mouse_handler_handle, handle=1))

        # Last bit of track
        right_len = track_len - left_len - middle_len
        ft.append(("class:track", track_char * right_len))
        mouse_handlers += [
            partial(
                self.mouse_handler_track,
                index=int(n_options * i / track_len),
            )
            for i in range(left_len + middle_len, track_len)
        ]

        if self.show_arrows():
            ft += [
                ("", " "),
                *to_formatted_text(self.slider.arrows[1], "class:arrow,right"),
            ]
            mouse_handlers += [
                self.mouse_handler_scroll,
                partial(self.mouse_handler_arrow, n=1),
            ]

        self.track_len = track_len

        if vertical:
            mouse_handlers = mouse_handlers[::-1]
            output = [[x] for x in explode_text_fragments(ft)][::-1]
        else:
            output = [ft]

        self.mouse_handlers = dict(enumerate(mouse_handlers))

        return output

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        if self.slider.vertical():
            loc = mouse_event.position.y
        else:
            loc = mouse_event.position.x
        return self.mouse_handler_(mouse_event, loc=loc)


class Slider(SelectableWidget):
    def __init__(
        self,
        options: "List[Any]",
        index: "int" = 0,
        indices: "Optional[List[int]]" = None,
        multiple: "FilterOrBool" = False,
        on_change: "Optional[Callable[[SelectableWidget], None]]" = None,
        style: "Union[str, Callable[[], str]]" = "",
        border: "GridStyle" = InnerEdgeGridStyle,
        show_borders: "Optional[BorderVisibility]" = None,
        vertical: "FilterOrBool" = False,
        show_arrows: "FilterOrBool" = True,
        arrows: "Tuple[AnyFormattedText, AnyFormattedText]" = ("-", "+"),
        show_readout: "FilterOrBool" = True,
    ):
        self.vertical = to_filter(vertical)
        self.arrows = arrows
        self.show_arrows = to_filter(show_arrows)
        self.show_readout = to_filter(show_readout)

        super().__init__(
            options=options,
            index=index,
            indices=indices,
            multiple=multiple,
            on_change=on_change,
            style=style,
        )

        self.on_change += self.value_changed

    def load_container(self) -> "AnyContainer":
        self.control = SliderControl(
            slider=self,
            show_arrows=self.show_arrows,
        )
        self.readout = Text(
            text=self.readout_text(self.indices),
            height=1,
            width=self.readout_len(),
            validation=lambda x: self.validate_readout(x) is not None,
            accept_handler=self.accept_handler,
        )
        return ConditionalSplit(
            self.vertical,
            [
                Box(
                    Window(
                        self.control,
                        style=lambda: f"class:slider {self.style}",
                    ),
                ),
                ConditionalContainer(
                    Box(self.readout, padding=0),
                    filter=self.show_readout,
                ),
            ],
            padding=1,
            style=self._style,
        )

    def value_changed(self, slider: "Optional[SelectableWidget]" = None) -> "None":
        """Sets the readout text when the slider value changes."""
        self.readout.text = self.readout_text(self.indices)

    def accept_handler(self, buffer: "Buffer") -> "bool":
        if values := self.validate_readout(buffer.text):
            for i, value in enumerate(values):
                self.control.set_index(
                    handle=i, ab=self.options.index(value), fire=False
                )
            # Trigger the event once all the values have been updated
            self.on_change.fire()
            return True
        return False

    def validate_readout(self, text: "str") -> "Optional[List[T]]":
        values = [value.strip() for value in text.split("-")]
        valid_values = []
        for value in values:
            for option in self.options:
                type_ = type(option)
                try:
                    typed_value = cast("T", type_(value))
                except Exception:
                    continue
                else:
                    if option == typed_value:
                        valid_values.append(typed_value)
                        break
            else:
                return None
        return valid_values

    def readout_text(self, indices) -> "str":
        return " - ".join(map(str, (self.options[i] for i in indices)))

    def readout_len(self) -> "int":
        return min(
            10,
            len(
                self.readout_text(
                    [
                        x[1]
                        for x in sorted(
                            (len(str(x)), i) for i, x in enumerate(self.options)
                        )[-sum(self.mask) :]
                    ]
                )
            ),
        )
