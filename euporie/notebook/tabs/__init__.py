"""Tab for use in euporie notebook editor."""

from euporie.core.convert.mime import MIME_FORMATS
from euporie.core.tabs import _TAB_REGISTRY, TabRegistryEntry

_TAB_REGISTRY.extend(
    [
        TabRegistryEntry(
            path="euporie.notebook.tabs.display:DisplayTab",
            mime_types=set(MIME_FORMATS.keys()),
        ),
        TabRegistryEntry(
            path="euporie.notebook.tabs.edit:EditorTab",
            mime_types={"text/*"},
            weight=1,
        ),
        TabRegistryEntry(
            path="euporie.notebook.tabs.json:JsonTab",
            mime_types={"*json"},
            file_extensions={".json": None},
        ),
        TabRegistryEntry(
            path="euporie.notebook.tabs.notebook:Notebook",
            mime_types={"application/x-ipynb+json"},
            file_extensions={".ipynb": None},
            weight=3,
        ),
        TabRegistryEntry(
            path="euporie.web.tabs.web:WebTab",
            mime_types={"text/html", "text/markdown"},
        ),
    ]
)

try:
    from jupytext.formats import NOTEBOOK_EXTENSIONS
except ModuleNotFoundError:
    pass
else:
    _TAB_REGISTRY["euporie.notebook.tabs.notebook:Notebook"]["file_extensions"].update(
        dict.fromkeys(NOTEBOOK_EXTENSIONS)
    )
