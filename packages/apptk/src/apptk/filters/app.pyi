from typing import TYPE_CHECKING

from apptk.enums import EditingMode
from apptk.filters.base import Condition

from .base import Condition

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.filters.base import Filter
    from apptk.layout.containers import Window
    from apptk.layout.layout import FocusableElement

emacs_insert_mode: Filter
emacs_mode: Filter
vi_insert_mode: Filter
vi_mode: Filter
vi_navigation_mode: Filter
vi_replace_mode: Filter
has_focus: Callable[[FocusableElement], Filter]

__all__ = [
    "buffer_has_focus",
    "completion_is_selected",
    "control_is_searchable",
    "emacs_insert_mode",
    "emacs_mode",
    "emacs_selection_mode",
    "has_arg",
    "has_completions",
    "has_focus",
    "has_selection",
    "has_suggestion",
    "has_validation_error",
    "in_editing_mode",
    "in_paste_mode",
    "is_done",
    "is_multiline",
    "is_read_only",
    "is_searching",
    "renderer_height_is_known",
    "shift_selection_mode",
    "vi_digraph_mode",
    "vi_insert_mode",
    "vi_insert_multiple_mode",
    "vi_mode",
    "vi_navigation_mode",
    "vi_recording_macro",
    "vi_replace_mode",
    "vi_search_direction_reversed",
    "vi_selection_mode",
    "vi_waiting_for_text_object_mode",
]

def has_focus(value: FocusableElement) -> Condition: ...

buffer_has_focus: Condition
has_selection: Condition
has_suggestion: Condition
has_completions: Condition
completion_is_selected: Condition
is_read_only: Condition
is_multiline: Condition
has_validation_error: Condition
has_arg: Condition
is_done: Condition
renderer_height_is_known: Condition

def in_editing_mode(editing_mode: EditingMode) -> Condition: ...

in_paste_mode: Condition
vi_mode: Condition
vi_navigation_mode: Condition
vi_insert_mode: Condition
vi_insert_multiple_mode: Condition
vi_replace_mode: Condition
vi_replace_single_mode: Condition
vi_selection_mode: Condition
vi_waiting_for_text_object_mode: Condition
vi_digraph_mode: Condition
vi_recording_macro: Condition
emacs_mode: Condition
emacs_insert_mode: Condition
emacs_selection_mode: Condition
shift_selection_mode: Condition
is_searching: Condition
control_is_searchable: Condition
vi_search_direction_reversed: Condition
display_has_focus: Condition

def scrollable(window: Window) -> Filter: ...

has_toolbar: Condition
