"""Tab for use in euporie notebook editor."""

from euporie.core.convert.mime import MIME_FORMATS
from euporie.core.tabs import _TAB_REGISTRY, TabRegistryEntry

_TAB_REGISTRY.extend(
    [
        TabRegistryEntry(
            path="euporie.notebook.tabs.display:DisplayTab",
            name="File Viewer",
            mime_types=set(MIME_FORMATS.keys()),
        ),
        TabRegistryEntry(
            path="euporie.notebook.tabs.edit:EditorTab",
            name="Text Editor",
            mime_types={"text/*"},
            weight=1,
        ),
        TabRegistryEntry(
            path="euporie.notebook.tabs.json:JsonTab",
            name="JSON Viewer",
            mime_types={"*json"},
            file_extensions={".json": None},
        ),
        TabRegistryEntry(
            path="euporie.notebook.tabs.notebook:Notebook",
            name="Notebook Editor",
            mime_types={"application/x-ipynb+json"},
            file_extensions={".ipynb": None},
            weight=3,
        ),
        TabRegistryEntry(
            path="euporie.web.tabs.web:WebTab",
            name="Web Viewer",
            mime_types={"text/html", "text/markdown"},
            weight=2,
        ),
    ]
)

try:
    from jupytext.formats import NOTEBOOK_EXTENSIONS
except ModuleNotFoundError:
    pass
else:
    for entry in _TAB_REGISTRY:
        if entry.path == "euporie.notebook.tabs.notebook:Notebook":
            entry.file_extensions.update(dict.fromkeys(NOTEBOOK_EXTENSIONS))
            break
