"""Tabs for use in euporie notebook editor."""

from euporie.core.tabs import _TAB_REGISTRY, TabRegistryEntry

_TAB_REGISTRY.extend(
    [
        TabRegistryEntry(
            path="euporie.web.tabs.web:WebTab",
            name="Web Viewer",
            mime_types={"text/html", "text/markdown"},
            weight=2,
        ),
    ]
)
