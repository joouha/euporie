"""A text base user interface for euporie."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from functools import partial
from typing import TYPE_CHECKING, cast

from prompt_toolkit.clipboard import InMemoryClipboard
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.filters import Condition, buffer_has_focus
from prompt_toolkit.formatted_text import HTML, fragment_list_to_text, to_formatted_text
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    HSplit,
    FloatContainer,
    VSplit,
    Window,
    WindowAlign,
    to_container,
)
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Dialog, Label, SearchToolbar
from prompt_toolkit.shortcuts.utils import print_container
from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    BeforeInput,
)
from pyperclip import determine_clipboard

from euporie import __app_name__, __copyright__, __logo__, __strapline__, __version__
from euporie.app.base import EuporieApp
from euporie.commands.registry import get
from euporie.config import CONFIG_PARAMS, config
from euporie.enums import TabMode
from euporie.tabs.console import Console
from euporie.tabs.notebook import EditNotebook
from euporie.utils import parse_path
from euporie.widgets.decor import FocusedStyle, Pattern
from euporie.widgets.formatted_text_area import FormattedTextArea
from euporie.widgets.inputs import Button, Text
from euporie.widgets.layout import TabBarControl, TabBarTab
from euporie.widgets.menu import MenuContainer, MenuItem
from euporie.widgets.palette import CommandPalette
from euporie.widgets.page import PrintingContainer

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from typing import (
        Any,
        Callable,
        Dict,
        Generator,
        List,
        Literal,
        Optional,
        Tuple,
        Type,
    )

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.clipboard import Clipboard
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.tabs.base import Tab
    from euporie.tabs.notebook import Notebook
    from euporie.widgets.cell import InteractiveCell

log = logging.getLogger(__name__)


class ConsoleApp(EuporieApp):
    """A text user interface euporie application."""

    def __init__(self, **kwargs: "Any") -> "None":
        """Create a new euporie text user interface application instance."""
        super().__init__(
            **{
                **{
                    "full_screen": False,
                    "mouse_support": True,
                },
                **kwargs,
            }
        )

        self.tabs = [Console(self)]

    def load_container(self) -> "FloatContainer":
        """Returns a container with all opened tabs."""
        self.dialogs.extend(
            [
                Float(
                    content=CompletionsMenu(
                        max_height=16,
                        scroll_offset=1,
                    ),
                    xcursor=True,
                    ycursor=True,
                ),
            ]
        )
        return HSplit(
            [
                FloatContainer(
                    self.tabs[0],
                    floats=self.floats,
                ),
                # Window(char="=", height=1),
            ]
        )
