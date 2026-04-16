from .app import *

def HasValidationError():
    return has_validation_error

def HasArg():
    return has_arg

def IsDone():
    return is_done

def RendererHeightIsKnown():
    return renderer_height_is_known

def ViNavigationMode():
    return vi_navigation_mode

def InPasteMode():
    return in_paste_mode

def EmacsMode():
    return emacs_mode

def EmacsInsertMode():
    return emacs_insert_mode

def ViMode():
    return vi_mode

def IsSearching():
    return is_searching

def HasSearch():
    return is_searching

def ControlIsSearchable():
    return control_is_searchable

def EmacsSelectionMode():
    return emacs_selection_mode

def ViDigraphMode():
    return vi_digraph_mode

def ViWaitingForTextObjectMode():
    return vi_waiting_for_text_object_mode

def ViSelectionMode():
    return vi_selection_mode

def ViReplaceMode():
    return vi_replace_mode

def ViInsertMultipleMode():
    return vi_insert_multiple_mode

def ViInsertMode():
    return vi_insert_mode

def HasSelection():
    return has_selection

def HasCompletions():
    return has_completions

def IsReadOnly():
    return is_read_only

def IsMultiline():
    return is_multiline

HasFocus = has_focus  # No lambda here! (Has_focus is callable that returns a callable.)
InEditingMode = in_editing_mode

__all__ = [
    "ControlIsSearchable",
    "EmacsInsertMode",
    "EmacsMode",
    "EmacsSelectionMode",
    "HasArg",
    "HasCompletions",
    "HasFocus",
    "HasSearch",
    "HasSelection",
    "HasValidationError",
    "InEditingMode",
    "InPasteMode",
    "IsDone",
    "IsMultiline",
    "IsReadOnly",
    "IsSearching",
    "RendererHeightIsKnown",
    "ViDigraphMode",
    "ViInsertMode",
    "ViInsertMultipleMode",
    "ViMode",
    "ViNavigationMode",
    "ViReplaceMode",
    "ViSelectionMode",
    "ViWaitingForTextObjectMode",
]
