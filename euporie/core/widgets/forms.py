"""Contain input widgets."""

from __future__ import annotations

import asyncio
import logging
from abc import ABCMeta, abstractmethod
from collections import deque
from functools import partial
from math import ceil, floor
from typing import TYPE_CHECKING, Dict, cast
from weakref import finalize

from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.completion.base import ConditionalCompleter
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.filters import (
    Always,
    Condition,
    Filter,
    FilterOrBool,
    has_focus,
    to_filter,
)
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_len, fragment_list_width
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    KeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout.containers import ConditionalContainer, Float, VSplit, Window
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
    UIContent,
    UIControl,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.processors import AfterInput, ConditionalProcessor
from prompt_toolkit.layout.screen import WritePosition
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from prompt_toolkit.validation import Validator
from prompt_toolkit.widgets.base import Box, TextArea

from euporie.core.border import InsetGrid
from euporie.core.current import get_app
from euporie.core.data_structures import DiBool
from euporie.core.ft.utils import FormattedTextAlign, align
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.widgets.decor import Border, Shadow
from euporie.core.widgets.layout import ConditionalSplit

if TYPE_CHECKING:
    from typing import Any, Callable, Sequence

    from prompt_toolkit.buffer import Buffer, BufferAcceptHandler
    from prompt_toolkit.completion.base import Completer
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
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.controls import (
        GetLinePrefixCallable,
        SearchBufferControl,
    )
    from prompt_toolkit.layout.processors import Processor
    from prompt_toolkit.lexers import Lexer

    from euporie.core.border import GridStyle

    OptionalSearchBuffer = (
        SearchBufferControl | Callable[[], SearchBufferControl] | None
    )

log = logging.getLogger(__name__)


class Swatch:
    """An widget which displays a given color."""

    def __init__(
        self,
        color: str | Callable[[], str] = "#FFFFFF",
        width: int = 2,
        height: int = 1,
        style: str = "class:swatch",
        border: GridStyle = InsetGrid,
        show_borders: DiBool | None = None,
    ) -> None:
        """Create a new instance of the color swatch.

        Args:
            color: A function or string which gives color to display
            width: The width of the color swatch (excluding the border)
            height: The height of the color swatch (excluding the border)
            style: Additional style to apply to the color swatch
            border: The grid style to use for the widget's border
            show_borders: Determines which borders should be displayed

        """
        self.color = color
        self.style = style

        self.container = Border(
            Window(char=" ", style=self.get_style, width=width, height=height),
            border=border,
            style=f"{self.style} class:border,inset",
            show_borders=show_borders,
        )

    def get_style(self) -> str:
        """Compute the style for the swatch.."""
        if callable(self.color):
            color = self.color()
        else:
            color = self.color
        return f"{self.style} bg:{color} "

    def __pt_container__(self) -> AnyContainer:
        """Return the swatch container."""
        return self.container


class Button:
    """A clickable button widget."""

    def __init__(
        self,
        text: AnyFormattedText,
        on_click: Callable[[Button], None] | None = None,
        on_mouse_down: Callable[[Button], None] | None = None,
        disabled: FilterOrBool = False,
        width: int | None = None,
        style: str | Callable[[], str] = "class:input",
        border: GridStyle | None = InsetGrid,
        show_borders: DiBool | None = None,
        selected: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        mouse_handler: Callable[[MouseEvent], NotImplementedOrNone] | None = None,
    ) -> None:
        """Create a new button widget instance.

        Args:
            text: The caption for the button.
            on_click: A callback to run when the mouse is released over the button
            on_mouse_down: A callback to run when the mouse is pressed on the button
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
            width: The width of the button. If :py:const:`None`, the button width is
                determined by the text
            style: A style string or callable style to apply to the button
            border: The grid style to use as the button's border
            show_borders: Determines which borders should be shown
            selected: The selection state of the button
            key_bindings: Additional key_binding to apply to the button
            mouse_handler: A mouse handler for the button. If unset, the default will be
                used, which results in the button behaving like a regular click-button

        """
        self.text = text
        self.on_mouse_down = Event(self, on_mouse_down)
        self.on_click = Event(self, on_click)
        self.disabled = to_filter(disabled)
        self._width = width
        self.style = style
        self.selected = selected
        if key_bindings is not None:
            self.key_bindings: KeyBindingsBase = merge_key_bindings(
                [self.get_key_bindings(), key_bindings]
            )
        else:
            self.key_bindings = self.get_key_bindings()
        self.mouse_handler = mouse_handler or self.default_mouse_handler
        self.window = Window(
            FormattedTextControl(
                self.get_text_fragments,
                key_bindings=self.key_bindings,
                focusable=True,
                show_cursor=False,
                style="class:face",
            ),
            style=self.get_style,
            dont_extend_width=True,
            dont_extend_height=True,
        )
        self.container = Box(
            Border(
                self.window,
                border=border,
                show_borders=show_borders,
                style=lambda: f"{self.get_style()} class:border",
            ),
            padding=0,
        )
        self.has_focus = has_focus(self)

    def get_style(self) -> str:
        """Return the style for the button given its current state."""
        if callable(self.style):
            style = self.style()
        else:
            style = self.style
        style = f"{style} class:button"
        if self.selected:
            style = f"{style} class:selection"
        if self.disabled():
            style = f"{style} class:disabled"
        return style

    def get_text_fragments(self) -> StyleAndTextTuples:
        """Return the list of formatted text fragments which define the button."""
        ft = [
            *to_formatted_text(self.text),
        ]
        ft = align(ft, FormattedTextAlign.CENTER, self.width)
        ft = [(style, text, self.mouse_handler) for style, text, *_ in ft]
        ft = [("[SetMenuPosition]", ""), *ft]
        return ft

    def get_key_bindings(self) -> KeyBindingsBase:
        """Key bindings for the Button."""
        kb = KeyBindings()

        @kb.add(" ", filter=~self.disabled)
        @kb.add("enter", filter=~self.disabled)
        def _(event: KeyPressEvent) -> None:
            self.on_mouse_down.fire()
            self.on_click.fire()

        return kb

    def default_mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events."""
        if self.disabled():
            return NotImplemented
        if mouse_event.button == MouseButton.LEFT:
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                self.selected = True
                if (render_info := self.window.render_info) is not None:
                    y_min, x_min = min(render_info._rowcol_to_yx.values())
                    y_max, x_max = max(render_info._rowcol_to_yx.values())
                    get_app().mouse_limits = WritePosition(
                        xpos=x_min,
                        ypos=y_min,
                        width=x_max - x_min,
                        height=y_max - y_min,
                    )
                self.on_mouse_down.fire()

                if not self.has_focus():
                    app = get_app()
                    app.layout.focus(self)
                    # Invalidate the app - we don't do it by returning None so the
                    # event can bubble
                    app.invalidate()
                    # We want this event to bubble if unfocused
                    return NotImplemented
                else:
                    return None

            elif mouse_event.event_type == MouseEventType.MOUSE_UP:
                get_app().mouse_limits = None
                if self.selected:
                    self.selected = False
                    self.on_click.fire()
                return None

            elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
                # Unselect the button if the mouse is moved outside of the button
                if (info := self.window.render_info) is not None:
                    if (
                        info._x_offset + mouse_event.position.x,
                        info._y_offset + mouse_event.position.y,
                    ) != get_app().mouse_position:
                        self.selected = False
                return None

        get_app().mouse_limits = None
        self.selected = False
        return NotImplemented

    @property
    def width(self) -> int:
        """The width of the button."""
        if self._width is not None:
            return self._width
        else:
            return fragment_list_width(to_formatted_text(self.text)) + 2

    @width.setter
    def width(self, value: int | None) -> None:
        """Set the width of the button."""
        self._width = value

    def __pt_container__(self) -> AnyContainer:
        """Return the button's container."""
        return self.container


class ToggleableWidget(metaclass=ABCMeta):
    """Base class for toggleable widgets."""

    container: AnyContainer
    on_click: Event
    selected: bool
    disabled: Filter
    key_bindings: KeyBindingsBase | None

    def toggle(self) -> None:
        """Toggle the selected state and trigger the "clicked" callback."""
        self.selected = not self.selected
        self.on_click.fire()

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Focus on mouse down and toggle state on mouse up."""
        if self.disabled():
            return NotImplemented
        elif mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            layout = get_app().layout
            if not layout.has_focus(self):
                app = get_app()
                app.layout.focus(self)
                app.invalidate()
                return NotImplemented
            else:
                return None
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.toggle()
            return None
        else:
            return NotImplemented

    def _get_key_bindings(self) -> KeyBindingsBase:
        """Key bindings for the Toggler."""
        kb = KeyBindings()

        @kb.add(" ", filter=~self.disabled)
        @kb.add("enter", filter=~self.disabled)
        def _(event: KeyPressEvent) -> None:
            self.toggle()

        if self.key_bindings is None:
            return kb
        else:
            return merge_key_bindings([kb, self.key_bindings])

    def __pt_container__(self) -> AnyContainer:
        """Return the toggler's container."""
        return self.container


class ToggleButton(ToggleableWidget):
    """A toggleable button widget."""

    def __init__(
        self,
        text: AnyFormattedText,
        on_click: Callable[[ToggleButton], None] | None = None,
        width: int | None = None,
        style: str | Callable[[], str] = "class:input",
        border: GridStyle | None = InsetGrid,
        show_borders: DiBool | None = None,
        selected: bool = False,
        disabled: FilterOrBool = False,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None:
        """Create a new toggle-button instance.

        Args:
            text: The text to display on the button (can be a string or callable)
            on_click: A callback to run when the button is clicked
            width: The width of the button
            style: A style for the button
            border: The grid style to use as the button's border
            show_borders: Which borders to display
            selected: The initial selection state of the button
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
            key_bindings: Additional key_binding to apply to the button
        """
        self.on_click = Event(self, on_click)
        self.style = style
        self.disabled = to_filter(disabled)
        self.key_bindings = key_bindings

        self.button = Button(
            text=text,
            width=width,
            style=style,
            border=border,
            show_borders=show_borders,
            selected=selected,
            key_bindings=self._get_key_bindings(),
            mouse_handler=self.mouse_handler,
            on_click=lambda button: self.on_click.fire(),
            disabled=self.disabled,
        )
        self.container = self.button

    # See mypy issue #4125
    @property  # type: ignore
    def selected(self) -> bool:  # type: ignore
        """Return the selection state of the toggle button."""
        return self.button.selected

    @selected.setter
    def selected(self, value: bool) -> None:
        """Set the selection state of the toggle button."""
        self.button.selected = value


class Checkbox(ToggleableWidget):
    """A toggleable checkbox widget."""

    def _get_text_fragments(self) -> StyleAndTextTuples:
        """Return the text fragments to display."""
        selected_style = "class:selection" if self.selected else ""
        ft = [
            (
                f"[SetCursorPosition] class:checkbox,prefix {selected_style}",
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
        text: AnyFormattedText = "",
        on_click: Callable[[ToggleableWidget], None] | None = None,
        prefix: tuple[str, str] = ("☐", "☑"),
        style: str = "class:input",
        selected: bool = False,
        disabled: FilterOrBool = False,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None:
        """Create a new checkbox widget instance.

        Args:
            text: The text to display next to the checkbox
            on_click: A callback to run when the checkbox is toggled
            prefix: A tuple of prefix strings to display, representing a checkbox in
                unchecked and checked state respectively
            style: Additional style string to apply to the widget
            selected: The initial selection state of the widget
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
            key_bindings: Additional key_binding to apply to the button

        """
        self.text = to_formatted_text(text)
        self.on_click = Event(self, on_click)
        self.prefix = prefix
        self.style = style
        self.selected = selected
        self.disabled = to_filter(disabled)
        self.key_bindings = key_bindings
        self.container = Window(
            FormattedTextControl(
                self._get_text_fragments,
                key_bindings=self._get_key_bindings(),
                focusable=True,
                show_cursor=False,
            ),
            style=lambda: f"class:checkbox {style}"
            f"{' class:disabled' if self.disabled() else ''}",
            dont_extend_width=True,
            dont_extend_height=True,
        )


class ExpandingBufferControl(BufferControl):
    """A sub-class of :class:`BufferControl` which expands to the available width."""

    def __init__(
        self,
        buffer: Buffer | None = None,
        input_processors: list[Processor] | None = None,
        include_default_input_processors: bool = True,
        lexer: Lexer | None = None,
        preview_search: FilterOrBool = False,
        focusable: FilterOrBool = True,
        search_buffer_control: OptionalSearchBuffer = None,
        menu_position: Callable[[], int | None] | None = None,
        focus_on_click: FilterOrBool = False,
        key_bindings: KeyBindingsBase | None = None,
        expand: FilterOrBool = True,
    ) -> None:
        """Add an ``expand`` parameter to the buffer control."""
        super().__init__(
            buffer=buffer,
            input_processors=input_processors,
            include_default_input_processors=include_default_input_processors,
            lexer=lexer,
            preview_search=preview_search,
            focusable=focusable,
            search_buffer_control=search_buffer_control,
            menu_position=menu_position,
            focus_on_click=focus_on_click,
            key_bindings=key_bindings,
        )
        self.expand = to_filter(expand)

    def preferred_width(self, max_available_width: int) -> int | None:
        """Enure text box expands to available width.

        Args:
            max_available_width: The maximum available width

        Returns:
            The desired width, which is the maximum available
        """
        if self.expand():
            return max_available_width
        else:
            return None


class Text:
    """A text input widget."""

    def __init__(
        self,
        text: str = "",
        style: str = "class:input",
        height: int = 1,
        min_height: int = 1,
        multiline: FilterOrBool = False,
        expand: FilterOrBool = True,
        width: int | None = None,
        completer: Completer | None = None,
        options: list[str] | Callable[[], list[str]] | None = None,
        show_borders: DiBool | None = None,
        on_text_changed: Callable[[Buffer], None] | None = None,
        validation: Callable[[str], bool] | None = None,
        accept_handler: BufferAcceptHandler | None = None,
        placeholder: str | None = None,
        lexer: Lexer | None = None,
        input_processors: Sequence[Processor] | None = None,
        disabled: FilterOrBool = False,
        password: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        prompt: AnyFormattedText | None = None,
    ) -> None:
        """Create a new text widget instance.

        Args:
            text: The default value of the text widget
            style: Additional style string to apply to the widget
            height: The height of the widget, excluding borders
            min_height: The minimum height of the widget, excluding borders
            multiline: Whether the text box accepts multiple lines of text
            expand: Determines if the text input should expand to the available width
            width: The width of the text input. If :py:const:`None`, the widget will
                expand to the available width
            completer: A completer to use, an alternative to ``options``
            options: A list of permitted values
            show_borders: Which borders to display. By default, all borders are shown
            on_text_changed: A callback to run when the text is changed
            validation: A callable used to validate the input
            accept_handler: A callable which run when the input is accepted (when the
                :kbd:`Enter` key is pressed on a non-multiline input)
            placeholder: Text to display when nothing has been entered
            lexer: :class:`~prompt_toolkit.lexers.Lexer` instance for syntax
                highlighting
            input_processors: Additional input processors to apply to the text-area
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
            password: A filter to determine if the text input is a password field
            prompt: Text to display before the input
            wrap_lines: Whether to wrap lines wider than the text area
        """
        self.style = style
        self.options = options or []
        self.disabled = to_filter(disabled)

        self.placeholder = placeholder

        self.text_area = TextArea(
            str(text),
            multiline=multiline,
            height=Dimension(min=min_height, max=height, preferred=height),
            width=width,
            focusable=True,
            focus_on_click=True,
            read_only=self.disabled,
            style=f"{style} class:text,text-area",
            validator=Validator.from_callable(validation) if validation else None,
            accept_handler=accept_handler,
            completer=completer
            or ConditionalCompleter(
                WordCompleter(self.options),
                filter=Condition(lambda: bool(self.options)),
            ),
            lexer=lexer,
            input_processors=[
                ConditionalProcessor(
                    AfterInput(
                        lambda: self.placeholder, style="class:text,placeholder"
                    ),
                    filter=Condition(
                        lambda: self.placeholder is not None and self.buffer.text == ""
                    ),
                ),
                *(input_processors or []),
            ],
            password=password,
            wrap_lines=wrap_lines,
        )
        self.buffer = self.text_area.buffer

        # Patch text area control's to expand to fill available width
        # Do this without monkey-pathing by sub-classing :class:`BufferControl` and
        # re-assigning the text-area's control
        self.text_area.control = ExpandingBufferControl(
            buffer=self.text_area.control.buffer,
            input_processors=self.text_area.control.input_processors,
            include_default_input_processors=(
                self.text_area.control.include_default_input_processors
            ),
            lexer=self.text_area.control.lexer,
            preview_search=self.text_area.control.preview_search,
            focusable=self.text_area.control.focusable,
            search_buffer_control=self.text_area.control._search_buffer_control,
            menu_position=self.text_area.control.menu_position,
            focus_on_click=self.text_area.control.focus_on_click,
            key_bindings=self.text_area.control.key_bindings,
            expand=expand,
        )
        self.text_area.window.content = self.text_area.control

        if on_text_changed:
            self.text_area.buffer.on_text_changed += on_text_changed
        if validation:
            self.text_area.buffer.validate_while_typing = Always()
        self.container = Border(
            VSplit(
                [
                    self.text_area,
                    ConditionalContainer(
                        MarginContainer(
                            ScrollbarMargin(), target=self.text_area.window
                        ),
                        filter=to_filter(multiline),
                    ),
                ]
            ),
            border=InsetGrid,
            style=self.border_style,
            show_borders=show_borders,
        )

    def border_style(self) -> str:
        """Calculate the style to apply to the widget's border."""
        if self.text_area.buffer.validation_state == ValidationState.INVALID:
            return f"{self.style} class:text,border,invalid"
        else:
            return f"{self.style} class:text,border"

    @property
    def text(self) -> str:
        """Return the input's text value."""
        return self.buffer.text

    @text.setter
    def text(self, value: str) -> None:
        """Set the input's text value."""
        self.buffer.text = value

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container


class Label:
    """A label widget which displays rich text."""

    def __init__(
        self,
        value: AnyFormattedText,
        style: str | Callable[[], str] = "class:input",
        html: FilterOrBool = False,
    ) -> None:
        """Create a new label widget instance.

        Args:
            value: The value to display
            style: Additional style to apply to the widget
            html: Whether to render the label as HTML
        """
        self.value = value
        self.control = FormattedTextControl(self.get_value, focusable=False)
        self.html = to_filter(html)
        self.container = Window(
            self.control,
            style=style,
            dont_extend_width=True,
            dont_extend_height=True,
        )

    def get_value(self) -> AnyFormattedText:
        """Return the current value of the label, converting to formatted text."""
        value = self.value
        if callable(value):
            data = value()
        else:
            data = value
        if self.html():
            from euporie.core.ft.html import HTML

            return HTML(data, collapse_root_margin=True, fill=False)
        return data

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container


class LabelledWidget:
    """A widget which applies a label to another widget."""

    def __init__(
        self,
        body: AnyContainer,
        label: AnyFormattedText,
        style: str = "class:input",
        vertical: FilterOrBool = False,
        html: FilterOrBool = False,
    ) -> None:
        """Create a new labelled widget instance.

        Args:
            body: The widget to label
            label: The label text to apply
            style: Additional style string to apply to the label
            vertical: Determines if the labelled widget should be oriented vertically
            html: Whether to render the label as HTML
        """
        self.body = body
        self.vertical = to_filter(vertical)
        self._html = to_filter(html)
        self.label = Label(label, style=style, html=self.html)
        padding_left = padding_right = lambda: None if self.vertical() else 0
        padding_top = padding_bottom = lambda: 0 if self.vertical() else None
        self.container = ConditionalSplit(
            self.vertical,
            [
                ConditionalContainer(
                    Box(
                        self.label,
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

    @property
    def html(self) -> Filter:
        """Get the HTML filter value."""
        return self._html

    @html.setter
    def html(self, value: FilterOrBool) -> None:
        """Set the HTML filter value."""
        self._html = to_filter(value)
        self.label.html = self._html

    def __pt_container__(self) -> AnyContainer:
        """Return the labelled widget container."""
        return self.container


class ProgressControl(UIControl):
    """A control which draws a progress-bar."""

    hchars = ("", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█")
    vchars = ("", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")

    def __init__(
        self,
        start: float | int = 0,
        stop: float | int = 100,
        step: float | int = 1,
        value: float | int = 0,
        vertical: FilterOrBool = False,
    ) -> None:
        """Create a new progress-bar control instance.

        Args:
            start: The lowest value of the progress-bar
            stop: The highest value of the progress-bar
            step: The size of each progress interval
            value: The initial value to display
            vertical: Determines if the progress-bar should be drawn in a vertical
                orientation
        """
        self.start = start
        self.stop = stop
        self.step = step
        self.value = value
        self.vertical = to_filter(vertical)

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)

    def preferred_width(self, max_available_width: int) -> int | None:
        """Determine the width of the progress-bar depending on its orientation."""
        return 1 if self.vertical() else max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Determine the height of the progress-bar depending on its orientation."""
        return min(max_available_height, 10) if self.vertical() else 1

    def render(self, width: int, height: int) -> list[StyleAndTextTuples]:
        """Render the progressbar at a given size as lines of formatted text."""
        vertical = self.vertical()
        length = height if vertical else width
        size = int(self.value / (self.stop - self.start) * length * 8) / 8
        remainder = int(size % 1 * 8)
        chars = self.vchars if vertical else self.hchars

        ft: StyleAndTextTuples = [
            ("class:progress", chars[8] * int(size)),
            ("class:progress", chars[remainder]),
            ("class:progress", " " * int(length - size)),
        ]

        if vertical:
            return [[x] for x in explode_text_fragments(ft)][::-1]
        else:
            return [ft]

    def create_content(self, width: int, height: int) -> UIContent:
        """Get or render content for a given output size."""

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
    """A progress-bar widget."""

    def __init__(
        self,
        start: float | int = 0,
        stop: float | int = 100,
        step: float | int = 1,
        value: float | int = 0,
        vertical: FilterOrBool = False,
        style: str | Callable[[], str] = "class:input",
    ) -> None:
        """Create a new progress-bar widget instance.

        Args:
            start: The lowest permitted value
            stop: The highest permitted value
            step: The interval between permitted values
            value: The initial value
            vertical: Determines if the progress-bar should be drawn in a vertical
                orientation
            style: Additional style string or callable to apply to the widget
        """
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
                    # dont_extend_height=~self.vertical,
                    height=lambda: None if self.vertical() else 1,
                    width=lambda: 1 if self.vertical() else None,
                ),
                border=InsetGrid,
                style=self.add_style("class:progress,border"),
            ),
            # width=lambda: 1 if self.vertical() else None,
        )

    @property
    def value(self) -> float | int:
        """Return the current value of the proegress-bar."""
        return self.control.value

    @value.setter
    def value(self, value: float | int) -> None:
        """Set the current value of the proegress-bar."""
        self.control.value = value

    def add_style(self, extra: str) -> Callable[[], str]:
        """Add an additional style to the widget's base style."""

        def _style() -> str:
            if callable(self.style):
                return f"{self.style()} {extra}"
            else:
                return f"{self.style} {extra}"

        return _style

    def __pt_container__(self) -> AnyContainer:
        """Return the progress-bar's container."""
        return self.container


class SizedMask(Dict[int, bool]):
    """Mask with restricted number of True items."""

    def __init__(self, size: int | None = None) -> None:
        """Initialize a new sized default dict."""
        self.size = size
        self._keys: deque[int] = deque()

    def clear(self) -> None:
        """Clear the dict's items."""
        self._keys.clear()
        super().clear()

    def __setitem__(self, key: int, value: bool) -> None:
        """Remove the oldest key when the size is exceeded."""
        if value:
            super().__setitem__(key, value)
        else:
            if key in self:
                del self[key]
            if key in self._keys:
                self._keys.remove(key)

        if self.size:
            if len(self._keys) >= self.size:
                key_to_remove = self._keys.popleft()
                if key_to_remove in self:
                    del self[key_to_remove]
            if value:
                self._keys.append(key)

    def __missing__(self, key: int) -> bool:
        """Return ``False`` for unknown items."""
        return False


class SelectableWidget(metaclass=ABCMeta):
    """Base class for widgets where one or more items can be selected."""

    def __init__(
        self,
        options: list[Any],
        labels: Sequence[AnyFormattedText] | None = None,
        index: int | None = None,
        indices: list[int] | None = None,
        n_values: int | None = None,
        multiple: FilterOrBool = False,
        max_count: int | None = None,
        on_change: Callable[[SelectableWidget], None] | None = None,
        style: str | Callable[[], str] = "class:input",
        disabled: FilterOrBool = False,
    ) -> None:
        """Create a new selectable widget instance.

        Args:
            options: List of permitted values
            labels: Optional list of labels for each permitted value
            index: The index of the initially selected single value
            indices: List of indices of the initially selected values
            n_values: The number of values which are selectable
            multiple: Determines whether multiple values can be selected
            max_count: The maximum number of selectable items
            on_change: Callback which is run when the selection changes
            style: Additional style to apply to the widget
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
        """
        self.options = options
        self.labels: list[AnyFormattedText] = list(
            labels or (str(option) for option in options)
        )
        self._selected = SizedMask(size=max_count)
        self.multiple = to_filter(multiple)

        if index is None and indices is None:
            if self.multiple():
                indices = []
            else:
                indices = [0]
        if indices is None:
            indices = [index or 0]
        self.indices = indices
        self.n_values = n_values
        self.on_change = Event(self, on_change)
        self._style = style
        self.disabled = to_filter(disabled)

        self.hovered: int | None = index
        self.container = self.load_container()
        self.has_focus = has_focus(self)

    @abstractmethod
    def load_container(self) -> AnyContainer:
        """Abstract method for loading the widget's container."""
        ...

    @property
    def style(self) -> str:
        """Return the widget's style."""
        if callable(self._style):
            style = self._style()
        else:
            style = self._style
        if self.disabled():
            style = f"{style} class:disabled"
        return style

    @style.setter
    def style(self, value: str | Callable[[], str]) -> None:
        """Set the widget's style."""
        self._style = value

    def key_bindings(self) -> KeyBindingsBase:
        """Key bindings for the selectable widget."""
        kb = KeyBindings()

        @kb.add("home", filter=~self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.toggle_item(0)

        @kb.add("up", filter=~self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.toggle_item(max(0, min((self.index or 0) - 1, len(self.options) - 1)))
            get_app().invalidate()

        @kb.add("down", filter=~self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.toggle_item(max(0, min((self.index or 0) + 1, len(self.options) - 1)))

        @kb.add("end", filter=~self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.toggle_item(len(self.options) - 1)

        @kb.add("enter", filter=self.multiple)
        @kb.add(" ", filter=self.multiple)
        def _(event: KeyPressEvent) -> None:
            if self.hovered is not None:
                self.toggle_item(self.hovered)

        @kb.add("home", filter=self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = 0

        @kb.add("up", filter=self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))

        @kb.add("down", filter=self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))

        @kb.add("end", filter=self.multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = len(self.options) - 1

        return ConditionalKeyBindings(kb, filter=~self.disabled)

    def toggle_item(self, index: int) -> None:
        """Toggle the selection status of the option at a given index."""
        if not self.multiple() and any(self._selected.values()):
            self._selected.clear()
        self._selected[index] = not self._selected[index]
        self.hovered = index
        self.on_change.fire()

    @property
    def mask(self) -> list[bool]:
        """Get mask of selected options."""
        return [self._selected[i] for i in range(len(self.options))]

    @property
    def index(self) -> int | None:
        """Return the first selected index."""
        return next((x for x in self.indices), None)

    @index.setter
    def index(self, value: int) -> None:
        """Set the selected indices to a single value."""
        self.indices = [value]

    @property
    def indices(self) -> list[int]:
        """Return a list of the selected indices."""
        output = [i for i, m in enumerate(self.mask) if m]
        if self.n_values is not None:
            if len(output) < self.n_values:
                output = (output * self.n_values)[: self.n_values]
        return output

    @indices.setter
    def indices(self, values: tuple[int]) -> None:
        """Set the selected indices."""
        self._selected.clear()
        for i in range(len(self.options)):
            self._selected[i] = i in values

    @property
    def value(self) -> Any:
        """Return the selected value."""
        if self.options:
            return self.options[self.index or 0]
        else:
            return None

    @property
    def values(self) -> list[Any]:
        """Return a list of the selected values."""
        if self.options:
            return [self.options[i] for i in self.indices]
        else:
            return [None for i in self.indices]

    def mouse_handler(self, i: int, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events."""
        if self.disabled():
            return NotImplemented
        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            self.hovered = i
            return None
        elif mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            if not self.has_focus():
                app = get_app()
                get_app().layout.focus(self)
                app.invalidate()
                # We want this event to bubble if unfocused
                return NotImplemented
            else:
                return None
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.toggle_item(i)
            return None
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            if self.multiple():
                hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))
                if self.hovered == hovered:
                    return NotImplemented
                else:
                    self.hovered = hovered
                    return None
            else:
                self.toggle_item(
                    item := max(0, min((self.index or 0) - 1, len(self.options) - 1))
                )
                return NotImplemented if item == 0 else None
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            if self.multiple():
                hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))
                if self.hovered == hovered:
                    return NotImplemented
                else:
                    self.hovered = hovered
                    return None
            else:
                self.toggle_item(
                    item := max(0, min((self.index or 0) + 1, len(self.options) - 1))
                )
                return NotImplemented if item == len(self.options) - 1 else None
            return NotImplemented
        else:
            return NotImplemented

    def __pt_container__(self) -> AnyContainer:
        """Return the widget's container."""
        return self.container


class Select(SelectableWidget):
    """A select widget, which allows one or more items to be selected from a list."""

    def __init__(
        self,
        options: list[Any],
        labels: Sequence[AnyFormattedText] | None = None,
        index: int | None = None,
        indices: list[int] | None = None,
        n_values: int | None = None,
        multiple: FilterOrBool = False,
        max_count: int | None = None,
        on_change: Callable[[SelectableWidget], None] | None = None,
        style: str | Callable[[], str] = "class:input,select",
        rows: int | None = 3,
        prefix: tuple[str, str] = ("", ""),
        border: GridStyle | None = InsetGrid,
        show_borders: DiBool | None = None,
        disabled: FilterOrBool = False,
        dont_extend_width: FilterOrBool = True,
        dont_extend_height: FilterOrBool = True,
    ) -> None:
        """Create a new select widget instance.

        Args:
            options: List of permitted values
            labels: Optional list of labels for each permitted value
            index: The index of the initially selected single value
            indices: List of indices of the initially selected values
            n_values: The number of values which are selectable
            multiple: Determines whether multiple values can be selected
            max_count: The maximum number of selectable items
            on_change: Callback which is run when the selection changes
            style: Additional style to apply to the widget
            rows: The number of rows of options to display
            prefix: A prefix to add to each row
            border: The grid style to use for the widget's border
            show_borders: Which borders to display
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
            dont_extend_width: When ``True``, don't take up more width then the
                preferred width reported by the control.
            dont_extend_height: When ``True``, don't take up more width then the
                preferred height reported by the control.

        """
        self.rows = rows
        self.prefix = prefix
        self.border = border
        self.show_borders = show_borders
        self.dont_extend_width = dont_extend_width
        self.dont_extend_height = dont_extend_height
        super().__init__(
            options=options,
            labels=labels,
            index=index,
            indices=indices,
            multiple=multiple,
            max_count=max_count,
            on_change=on_change,
            style=style,
            disabled=disabled,
        )

    def text_fragments(self) -> StyleAndTextTuples:
        """Create a list of formatted text fragments to display."""
        ft: StyleAndTextTuples = []
        if self.labels:
            max_width = max(
                fragment_list_width(to_formatted_text(x)) for x in self.labels
            )
        else:
            max_width = 1
        for i, label in enumerate(self.labels):
            label = to_formatted_text(label)
            label = align(label, FormattedTextAlign.LEFT, width=max_width)
            if self.multiple():
                cursor = "[SetCursorPosition]" if i == self.hovered else ""
            else:
                cursor = "[SetCursorPosition]" if self.mask[i] else ""
            style = "class:selection" if self.mask[i] else ""
            if self.hovered == i and self.multiple() and self.has_focus():
                style += " class:hovered"
            ft_option = [
                (f"class:prefix {cursor}", self.prefix[self.mask[i]]),
                ("", " "),
                *label,
                ("", " "),
                ("", "\n"),
            ]
            handler = cast(
                "Callable[[MouseEvent], None]", partial(self.mouse_handler, i)
            )
            ft += [
                (f"{fragment_style} {style}", text, handler)
                for fragment_style, text, *_ in ft_option
            ]
        if ft:
            ft.pop()
        return ft

    def load_container(self) -> AnyContainer:
        """Load the widget's container."""
        return Box(
            Border(
                VSplit(
                    [
                        window := Window(
                            FormattedTextControl(
                                self.text_fragments,
                                focusable=True,
                                show_cursor=False,
                                key_bindings=self.key_bindings(),
                            ),
                            height=lambda: self.rows,
                            dont_extend_width=self.dont_extend_width,
                            dont_extend_height=self.dont_extend_height,
                            style=f"class:face"
                            f"{' class:disabled' if self.disabled() else ''}",
                        ),
                        MarginContainer(ScrollbarMargin(), target=window),
                    ]
                ),
                border=self.border,
                show_borders=self.show_borders,
                style="class:inset,border",
            ),
            padding=0,
            style=self.style,
        )


class Dropdown(SelectableWidget):
    """A dropdown widget, allowing selection of an item from a menu of options."""

    def __init__(
        self,
        options: list[Any],
        labels: Sequence[AnyFormattedText] | None = None,
        index: int | None = None,
        indices: list[int] | None = None,
        n_values: int | None = None,
        multiple: FilterOrBool = False,
        max_count: int | None = None,
        on_change: Callable[[SelectableWidget], None] | None = None,
        style: str | Callable[[], str] = "class:input",
        arrow: str = "⯆",
        disabled: FilterOrBool = False,
    ) -> None:
        """Create a new drop-down widget instance.

        Args:
            options: List of permitted values
            labels: Optional list of labels for each permitted value
            index: The index of the initially selected single value
            indices: List of indices of the initially selected values
            n_values: The number of values which are selectable
            multiple: Determines whether multiple values can be selected
            max_count: The maximum number of selectable items
            on_change: Callback which is run when the selection changes
            style: Additional style to apply to the widget
            arrow: The character to use for the dropdown arrow
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
        """
        self.menu_visible: bool = False
        self.arrow: str = arrow
        super().__init__(
            options=options,
            labels=labels,
            index=index,
            indices=indices,
            multiple=multiple,
            max_count=max_count,
            on_change=on_change,
            style=style,
            disabled=disabled,
        )

        self.menu = Float(
            ConditionalContainer(
                Shadow(
                    Window(
                        FormattedTextControl(
                            self.menu_fragments,
                        ),
                        style=f"class:dropdown,dropdown.menu {self.style}",
                    )
                ),
                filter=Condition(lambda: self.menu_visible) & self.has_focus,
            ),
            xcursor=True,
            ycursor=True,
        )
        menu_name = f"dropdown-menu-{hash(self)}"
        app = get_app()
        app.menus[menu_name] = self.menu

        def _cleanup_menu() -> None:
            del app.menus[menu_name]

        finalize(self, _cleanup_menu)

    def load_container(self) -> AnyContainer:
        """Load the widget's container."""
        self.button = ToggleButton(
            self.button_text,
            on_click=self.toggle_menu,
            style=f"class:dropdown {self.style}",
            key_bindings=self.key_bindings(),
            disabled=self.disabled,
        )
        return self.button

    def button_text(self) -> StyleAndTextTuples:
        """Return the text to display on the button."""
        labels = [to_formatted_text(x) for x in self.labels] or [
            to_formatted_text([("", "")])
        ]
        max_width = max(fragment_list_width(x) for x in labels)
        ft = align(
            to_formatted_text(labels[self.index or 0]),
            FormattedTextAlign.LEFT,
            max_width,
        )
        ft += [("", " " if self.arrow else ""), ("class:arrow", self.arrow)]
        return ft

    def toggle_menu(self, button: ToggleButton) -> None:
        """Show or hide the menu."""
        self.menu_visible = not self.menu_visible
        self.hovered = self.index
        get_app().invalidate()

    def menu_fragments(self) -> StyleAndTextTuples:
        """Return formatted text fragment to display in the menu."""
        ft: StyleAndTextTuples = []
        labels = [to_formatted_text(x) for x in self.labels]
        max_width = max(fragment_list_width(x) for x in labels)
        for i, label in enumerate(labels):
            # Pad each option
            formatted_label = align(label, FormattedTextAlign.LEFT, width=max_width + 2)
            item_style = "class:hovered" if i == self.hovered else ""
            handler = partial(self.mouse_handler, i)
            ft.extend(
                [
                    (item_style, " ", handler),
                    *[
                        (f"{item_style} {style}", text, handler)
                        for style, text, *_ in formatted_label
                    ],
                    (item_style, " ", handler),
                    ("", "\n"),
                ]
            )
        # Remove the last newline
        ft.pop()
        return ft

    def mouse_handler(self, i: int, mouse_event: MouseEvent) -> None:
        """Handle mouse events."""
        if self.disabled():
            return None
        super().mouse_handler(i, mouse_event)
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.menu_visible = False
            self.button.selected = False

    def key_bindings(self) -> KeyBindingsBase:
        """Return key-bindings for the drop-down widget."""
        menu_visible = Condition(lambda: self.menu_visible)
        kb = KeyBindings()

        @kb.add("enter", filter=menu_visible)
        @kb.add(" ", filter=menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.index = self.hovered
            self.menu_visible = False
            self.button.selected = False
            self.on_change.fire()

        @kb.add("escape", filter=menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.menu_visible = False
            self.button.selected = False

        @kb.add("home", filter=menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.hovered = 0

        @kb.add("up", filter=menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))

        @kb.add("down", filter=menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))

        @kb.add("end", filter=menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.hovered = len(self.options) - 1

        @kb.add("home", filter=~menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.index = 0

        @kb.add("up", filter=~menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.index = max(0, min((self.index or 0) - 1, len(self.options) - 1))

        @kb.add("down", filter=~menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.index = max(0, min((self.index or 0) + 1, len(self.options) - 1))

        @kb.add("end", filter=~menu_visible)
        def _(event: KeyPressEvent) -> None:
            self.index = len(self.options) - 1

        return ConditionalKeyBindings(kb, filter=~self.disabled)


class ToggleButtons(SelectableWidget):
    """A widget where an option is selected using mutually exclusive toggle-buttons."""

    def __init__(
        self,
        options: list[Any],
        labels: Sequence[AnyFormattedText] | None = None,
        index: int | None = None,
        indices: list[int] | None = None,
        n_values: int | None = None,
        multiple: FilterOrBool = False,
        max_count: int | None = None,
        on_change: Callable[[SelectableWidget], None] | None = None,
        style: str | Callable[[], str] = "class:input",
        border: GridStyle | None = InsetGrid,
        disabled: FilterOrBool = False,
        vertical: FilterOrBool = False,
    ) -> None:
        """Create a new select widget instance.

        Args:
            options: List of permitted values
            labels: Optional list of labels for each permitted value
            index: The index of the initially selected single value
            indices: List of indices of the initially selected values
            n_values: The number of values which are selectable
            multiple: Determines whether multiple values can be selected
            max_count: The maximum number of selectable items
            on_change: Callback which is run when the selection changes
            style: Additional style to apply to the widget
            border: The grid style to use for the widget's border
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled
            vertical: Determines if the toggle buttons should be arranged vertically
        """
        self.border = border
        self.disabled = to_filter(disabled)
        self.vertical = to_filter(vertical)
        super().__init__(
            options=options,
            labels=labels,
            index=index,
            indices=indices,
            multiple=multiple,
            max_count=max_count,
            on_change=on_change,
            style=style,
            disabled=self.disabled,
        )

    def load_container(self) -> AnyContainer:
        """Load the widget's container."""
        if self.vertical():
            show_borders_values = [
                DiBool(False, True, False, True) for _ in self.options
            ]
            show_borders_values[0] = show_borders_values[0]._replace(top=True)
            show_borders_values[-1] = show_borders_values[-1]._replace(bottom=True)
        else:
            show_borders_values = [
                DiBool(True, False, True, False) for _ in self.options
            ]
            show_borders_values[0] = show_borders_values[0]._replace(left=True)
            show_borders_values[-1] = show_borders_values[-1]._replace(right=True)
        self.buttons = [
            ToggleButton(
                text=label,
                selected=selected,
                on_click=partial(lambda index, button: self.toggle_item(index), i),
                border=self.border,
                show_borders=show_borders,
                style=self.get_button_style(i),
                disabled=self.disabled,
            )
            for i, (label, selected, show_borders) in enumerate(
                zip(
                    self.labels,
                    self.mask,
                    show_borders_values,
                )
            )
        ]
        self.on_change += self.update_buttons
        return ConditionalSplit(
            self.vertical,
            self.buttons,
            style="class:toggle-buttons",
            key_bindings=self.key_bindings(),
        )

    def get_button_style(self, index: int) -> Callable[[], str]:
        """Return the current button style."""

        def _get_style() -> str:
            style = self.style() if callable(self.style) else self.style
            if self.hovered == index:
                return f"{style} class:hovered"
            else:
                return style

        return _get_style

    @property
    def index(self) -> int | None:
        """Return the first selected index."""
        return next((x for x in self.indices), None)

    @index.setter
    def index(self, value: int) -> None:
        """Set the selected indices to a single value."""
        self.indices = [value]
        self.update_buttons(self)

    def update_buttons(self, widget: SelectableWidget | None = None) -> None:
        """Set the toggle buttons' selection state when the selected index changes."""
        for i, selected in enumerate(self.mask):
            self.buttons[i].selected = selected

    def key_bindings(self) -> KeyBindingsBase:
        """Return key-bindings for the drop-down widget."""
        multiple = self.multiple
        kb = KeyBindings()

        @kb.add("left", filter=~multiple)
        def _(event: KeyPressEvent) -> None:
            self.index = max(0, min((self.index or 0) - 1, len(self.options) - 1))

        @kb.add("right", filter=~multiple)
        def _(event: KeyPressEvent) -> None:
            self.index = max(0, min((self.index or 0) + 1, len(self.options) - 1))

        @kb.add("home", filter=~multiple)
        def _(event: KeyPressEvent) -> None:
            self.index = 0

        @kb.add("end", filter=~multiple)
        def _(event: KeyPressEvent) -> None:
            self.index = len(self.options) - 1

        @kb.add("left", filter=multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))
            get_app().layout.focus(self.buttons[self.hovered])

        @kb.add("right", filter=multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))
            get_app().layout.focus(self.buttons[self.hovered])

        @kb.add("home", filter=multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = 0
            get_app().layout.focus(self.buttons[self.hovered])

        @kb.add("end", filter=multiple)
        def _(event: KeyPressEvent) -> None:
            self.hovered = len(self.options) - 1
            get_app().layout.focus(self.buttons[self.hovered])

        return kb


class SliderControl(UIControl):
    """A control to display a slider."""

    def __init__(
        self,
        slider: Slider,
        show_arrows: FilterOrBool = True,
        handle_char: str = "●",
        track_char: str | None = None,
        selected_track_char: str | None = None,
        style: str = "class:input",
    ) -> None:
        """Create a new slider control instance.

        Args:
            slider: The slider widget the control belongs to (provides slider data)
            show_arrows: Whether to show increment / decrement buttons at each end of
                the slider
            handle_char: The character to use as the slider handle
            track_char: The character to use for the slider track
            selected_track_char: The character to use for the selected section of the
                slider track
            style: A style string to apply to the slider
        """
        self.slider = slider

        self.track_char = track_char
        self.selected_track_char = selected_track_char
        self.show_arrows = to_filter(show_arrows)
        self.handle_char = handle_char

        self.selected_handle = 0
        self.track_len = 0

        self.mouse_handlers: dict[int, Callable[..., NotImplementedOrNone]] = {}
        self.dragging = False
        self.repeatable = True
        self.repeat_task: asyncio.Task[None] | None = None

        self._content_cache: SimpleCache = SimpleCache(maxsize=50)
        self.window: Window | None = None

    def preferred_width(self, max_available_width: int) -> int | None:
        """Return the preferred width of the slider control given its orientation."""
        return 1 if self.slider.vertical() else max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Return the preferred height of the slider control given its orientation."""
        return min(max_available_height, 10) if self.slider.vertical() else 1

    def is_focusable(self) -> bool:
        """Tell whether this user control is focusable."""
        return True

    def create_content(self, width: int, height: int) -> UIContent:
        """Create an cache the rendered control fragments."""

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
        handle: int = 0,
        ab: int | None = None,
        rel: int | None = None,
        fire: bool = True,
    ) -> NotImplementedOrNone:
        """Set the selected index of the slider."""
        assert ab is not None or rel is not None
        if rel is not None:
            ab = self.slider.indices[handle] + rel
        assert ab is not None
        # Restrict set value to permitted range
        ab = min(len(self.slider.options) - 1, max(0, ab))

        # Do not allow both handles to have the same value
        indices = dict(enumerate(self.slider.indices))
        if ab not in indices.values():
            # Set the handle's value
            indices.update({handle: ab})
            # Update the slider
            self.slider.indices = [index for handle, index in sorted(indices.items())]
            if fire:
                self.slider.on_change.fire()
            return None
        else:
            return NotImplemented

    @property
    def selected_handle(self) -> int:
        """Return the currently selected slider handle."""
        return self._selected_handle

    @selected_handle.setter
    def selected_handle(self, value: int) -> None:
        """Set the currently selected slider handle."""
        value = max(0, min(value, sum(self.slider.mask)))
        self._selected_handle = value

    def _draw_handle(self, n: int) -> OneStyleAndTextTuple:
        """Draw the given slider handle given it's current focus and selection state."""
        selected_style = "class:selection" if self.selected_handle == n else ""
        focused_style = "class:focused" if self.slider.has_focus() else ""
        return (
            f"class:handle {selected_style} {focused_style}",
            self.handle_char,
        )

    def mouse_handler_handle(
        self, mouse_event: MouseEvent, handle: int = 0
    ) -> NotImplementedOrNone:
        """Handle mouse events on the slider's handles."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            self.selected_handle = handle
            self.dragging = True

            # Set global mouse capture
            if (
                self.window is not None
                and (render_info := self.window.render_info) is not None
            ):
                y_min, x_min = min(render_info._rowcol_to_yx.values())
                y_max, x_max = max(render_info._rowcol_to_yx.values())
                get_app().mouse_limits = WritePosition(
                    xpos=x_min,
                    ypos=y_min,
                    width=x_max - x_min,
                    height=y_max - y_min,
                )
        return self.mouse_handler_scroll(mouse_event)

    def mouse_handler_track(
        self, mouse_event: MouseEvent, index: int = 0
    ) -> NotImplementedOrNone:
        """Handle mouse events on the slider track."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
            handle = self.selected_handle
            if sum(self.slider.mask) == 2:
                if handle == 0 and index > self.slider.indices[1]:
                    self.selected_handle = 1
                elif handle == 1 and index < self.slider.indices[0]:
                    self.selected_handle = 0
            self.set_index(self.selected_handle, ab=index)
            return None
        else:
            if self.repeat_task is not None:
                self.repeat_task.cancel()
            return self.mouse_handler_scroll(mouse_event)

    def mouse_handler_arrow(
        self, mouse_event: MouseEvent, n: int = 0
    ) -> NotImplementedOrNone:
        """Handle mouse events on the slider's arrows."""
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.focus(self)
            self.set_index(self.selected_handle, rel=n)
            # Trigger this mouse event to be repeated
            if self.repeatable:
                self.repeat_task = get_app().create_background_task(
                    self.repeat(mouse_event, handler=self.mouse_handler_arrow, n=n)
                )
            else:
                self.repeatable = True
            return None
        else:
            # Stop any repeated tasks
            self.repeatable = False
            if self.repeat_task is not None:
                self.repeat_task.cancel()
            return self.mouse_handler_scroll(mouse_event)

    def mouse_handler_scroll(
        self, mouse_event: MouseEvent, handle: int | None = None
    ) -> NotImplementedOrNone:
        """Handle mouse scroll events."""
        if self.slider.has_focus():
            if handle is None:
                handle = self.selected_handle
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                return self.set_index(handle, rel=1)
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                return self.set_index(handle, rel=-1)
        return NotImplemented

    def mouse_handler_(self, mouse_event: MouseEvent, loc: int) -> NotImplementedOrNone:
        """Handle mouse events."""
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
            get_app().mouse_limits = None
            # Call the underlying mouse handler
            if handler := self.mouse_handlers.get(loc):
                return handler(mouse_event)
            else:
                return NotImplemented

    async def repeat(
        self,
        mouse_event: MouseEvent,
        handler: Callable[..., NotImplementedOrNone],
        timeout: float = 0.25,
        **kwargs: Any,
    ) -> None:
        """Repeat a mouse event after a timeout."""
        await asyncio.sleep(timeout)
        handler(mouse_event, **kwargs)
        get_app().invalidate()

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Key bindings for the Slider."""
        kb = KeyBindings()

        if self.slider.vertical():

            @kb.add("down")
            def _(event: KeyPressEvent) -> None:
                self.set_index(self.selected_handle, rel=-1)

            @kb.add("up")
            def _(event: KeyPressEvent) -> None:
                self.set_index(self.selected_handle, rel=1)

        else:

            @kb.add("left")
            def _(event: KeyPressEvent) -> None:
                self.set_index(self.selected_handle, rel=-1)

            @kb.add("right")
            def _(event: KeyPressEvent) -> None:
                self.set_index(self.selected_handle, rel=1)

        @kb.add("home")
        def _(event: KeyPressEvent) -> None:
            self.set_index(self.selected_handle, ab=0)

        @kb.add("end")
        def _(event: KeyPressEvent) -> None:
            self.set_index(self.selected_handle, ab=len(self.slider.options))

        return kb

    def render_lines(self, width: int, height: int) -> list[StyleAndTextTuples]:
        """Generate formatted text fragments to display the slider."""
        ft = []
        mouse_handlers: list[Callable[..., NotImplementedOrNone]] = []

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
        ft.append(self._draw_handle(0))
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

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events given the slider's orientation."""
        if self.slider.disabled():
            return None
        if self.slider.vertical():
            loc = mouse_event.position.y
        else:
            loc = mouse_event.position.x
        return self.mouse_handler_(mouse_event, loc=loc)


class Slider(SelectableWidget):
    """A slider widget with an optional editable readout."""

    control: SliderControl
    readout: Text

    def __init__(
        self,
        options: list[Any],
        labels: Sequence[AnyFormattedText] | None = None,
        index: int | None = None,
        indices: list[int] | None = None,
        n_values: int | None = None,
        multiple: FilterOrBool = False,
        max_count: int | None = None,
        on_change: Callable[[SelectableWidget], None] | None = None,
        style: str | Callable[[], str] = "class:input",
        border: GridStyle = InsetGrid,
        show_borders: DiBool | None = None,
        vertical: FilterOrBool = False,
        show_arrows: FilterOrBool = True,
        arrows: tuple[AnyFormattedText, AnyFormattedText] = ("-", "+"),
        show_readout: FilterOrBool = True,
        disabled: FilterOrBool = False,
    ) -> None:
        """Create a new slider widget instance.

        Args:
            options: A list of available options for the slider
            labels: An optional list of option names
            index: The index of the initially selected option if not a multiple
                selection slider
            indices: The indices of the start and end of the initially selected ranger
                of options if a range can be selected
            n_values: The number of values which are selectable
            multiple: If true, allow a range of options to be selected
            max_count: The maximum number of selectable items
            on_change: An optional function to call when the selection changes
            style: An optional style to apply to the widget
            border: The grid style to use for the borders (unused)
            show_borders: Whether the borders should be displayed (unused)
            vertical: If true, the slider will be displayed vertically
            show_arrows: If increment & decrement buttons should be shown at either end
                of the slider
            arrows: Strings to use for the increment and decrement buttons
            show_readout: If true, a read-out text box will be shown displaying the
                slider's current value
            disabled: A filter which when evaluated to :py:const:`True` causes the
                widget to be disabled

        """
        self.vertical = to_filter(vertical)
        self.arrows = arrows
        self.show_arrows = to_filter(show_arrows)
        self.show_readout = to_filter(show_readout)
        self.disabled = to_filter(disabled)

        if n_values is None and indices:
            n_values = len(indices)

        super().__init__(
            options=options,
            labels=labels,
            index=index,
            indices=indices,
            n_values=n_values,
            multiple=multiple,
            max_count=max_count,
            on_change=on_change,
            style=style,
            disabled=self.disabled,
        )
        self.on_change += self.value_changed

    def load_container(self) -> AnyContainer:
        """Build the slider's container."""
        self.control = SliderControl(slider=self, show_arrows=self.show_arrows)
        window = Window(self.control, style=lambda: f"class:slider {self.style}")
        self.control.window = window
        self.readout = Text(
            text=self.readout_text(self.indices),
            height=1,
            width=self.readout_len(),
            validation=lambda x: self.validate_readout(x) is not None,
            accept_handler=self.accept_handler,
            disabled=self.disabled,
            style=self.style,
        )
        return ConditionalSplit(
            self.vertical,
            [
                Box(window),
                ConditionalContainer(
                    Box(self.readout, padding=0),
                    filter=self.show_readout,
                ),
            ],
            padding=1,
            style=self._style,
        )

    def value_changed(self, slider: SelectableWidget | None = None) -> None:
        """Set the readout text when the slider value changes."""
        self.readout.text = self.readout_text(self.indices)

    def accept_handler(self, buffer: Buffer) -> bool:
        """Set the index to the value(s) entered in the readout buffer."""
        if values := self.validate_readout(buffer.text):
            for i, value in enumerate(values):
                self.control.set_index(
                    handle=i, ab=self.options.index(value), fire=False
                )
            # Trigger the event once all the values have been updated
            self.on_change.fire()
            return True
        return False

    def validate_readout(self, text: str) -> list[Any] | None:
        """Confirm the value entered in the readout is value."""
        values = [value.strip() for value in text.split("-")]
        valid_values = []
        for value in values:
            for option in self.options:
                type_ = type(option)
                try:
                    typed_value = type_(value)
                except ValueError:
                    continue
                else:
                    if option == typed_value:
                        valid_values.append(typed_value)
                        break
            else:
                return None
        return valid_values

    def readout_text(self, indices: list[int]) -> str:
        """Return the readout text area value."""
        return " - ".join(map(str, (self.options[i] for i in indices)))

    def readout_len(self) -> int:
        """Return the length of the readout text area."""
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
