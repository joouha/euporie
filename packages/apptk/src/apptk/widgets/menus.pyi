import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from apptk.border import ThinGrid
from apptk.filters import has_focus
from apptk.filters.utils import to_filter
from apptk.formatted_text.base import (
    StyleAndTextTuples,
)
from apptk.key_binding.key_bindings import KeyBindings, KeyBindingsBase
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.layout.containers import (
    AnyContainer,
    Container,
    Float,
    FloatContainer,
    Window,
)
from apptk.layout.controls import FormattedTextControl

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

    from apptk.border import GridStyle
    from apptk.commands import Command
    from apptk.filters import Filter, FilterOrBool
    from apptk.formatted_text.base import AnyFormattedText
    from apptk.layout.controls import UIControl

    from euporie.core.bars.status import StatusBarFields

E = KeyPressEvent
log = logging.getLogger(__name__)

__all__ = [
    "MenuContainer",
    "MenuItem",
]

class MenuContainer:
    body: AnyContainer | None
    menu_items: list[MenuItem] | None
    selected_menu: list[int]
    control: FormattedTextControl
    window: Window
    container: FloatContainer
    grid: type[GridStyle] = ThinGrid  # Class attribute default
    padding: int
    max_depth: int
    _show_icons: FilterOrBool
    collapse_prefix: bool
    collapse_suffix: bool
    _shadows: FilterOrBool
    last_focused: UIControl | None
    kb: KeyBindings
    menu_containers: list[AnyContainer]
    focused = has_focus(self.window)
    def __init__(
        self,
        body: AnyContainer | None = None,
        menu_items: list[MenuItem] | None = None,
        floats: list[Float] | None = None,
        key_bindings: KeyBindingsBase | None = None,
        grid: type[GridStyle] | None = None,
        padding: int = 1,
        max_depth: int = 4,
        collapse_prefix: bool = False,
        collapse_suffix: bool = True,
        icons: FilterOrBool = True,
        shadows: FilterOrBool = True,
    ) -> None: ...
    def _get_menu(self, level: int) -> MenuItem: ...
    def _get_menu_fragments(self) -> StyleAndTextTuples: ...
    def _submenu(self, level: int = 0) -> AnyContainer: ...
    @property
    def floats(self) -> list[Float] | None: ...
    def __pt_container__(self) -> Container: ...
    def _render_prefix(self, item: MenuItem) -> StyleAndTextTuples: ...
    def _render_suffix(self, item: MenuItem) -> StyleAndTextTuples: ...
    def _compute_prefix_width(self, menu: MenuItem) -> int: ...
    def _compute_suffix_width(self, menu: MenuItem) -> int: ...
    def _compute_menu_width(self, menu: MenuItem) -> int: ...
    def refocus(self) -> None: ...
    def _select_previous_item(self) -> bool: ...
    def _select_next_item(self) -> bool: ...
    def __pt_status__(self) -> StatusBarFields: ...

class MenuItem:
    handler: Callable[[], None] | None
    children: list[MenuItem] | None
    selected_item = 0
    _formatted_text: AnyFormattedText
    _icon: AnyFormattedText
    description: str
    separator: bool | None
    _disabled = to_filter(disabled) | to_filter(self.separator)
    hidden: FilterOrBool
    toggled: Filter | None
    _shortcut = ""
    def __init__(
        self,
        text: AnyFormattedText = "",
        handler: Callable[[], None] | None = None,
        children: list[MenuItem] | None = None,
        shortcut: Sequence[str] | None = None,
        disabled: FilterOrBool = False,
        description: str = "",
        separator: bool | None = None,
        hidden: FilterOrBool = False,
        toggled: Filter | None = None,
        icon: AnyFormattedText = "",
    ) -> None: ...
    @property
    def width(self) -> int: ...
    @property
    def text(self) -> str: ...
    @text.setter
    def text(self, value: Any) -> None: ...
    @property
    def shortcut(self) -> AnyFormattedText: ...
    @shortcut.setter
    def shortcut(self, value: Any) -> None: ...
    @property
    def disabled(self) -> bool: ...
    @disabled.setter
    def disabled(self, value: FilterOrBool) -> None: ...
    @property
    def icon(self) -> StyleAndTextTuples: ...
    @property
    def formatted_text(self) -> StyleAndTextTuples: ...
    @classmethod
    def from_cmd(cls, cmd: Command | str) -> MenuItem: ...
