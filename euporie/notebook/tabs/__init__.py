"""Tab for use in euporie notebook editor."""

from euporie.notebook.tabs.display import DisplayTab
from euporie.notebook.tabs.edit import EditorTab
from euporie.notebook.tabs.json import JsonTab
from euporie.notebook.tabs.log import LogView
from euporie.notebook.tabs.notebook import Notebook
from euporie.web.tabs.web import WebTab

__all__ = ["DisplayTab", "EditorTab", "JsonTab", "LogView", "Notebook", "WebTab"]
