"""Clone Helix editor's list of known LSP servers."""

import tomllib
from upath import UPath

source = UPath("https://github.com/helix-editor/helix/raw/master/languages.toml")
with source.open("rb") as f:
    c = tomllib.load(f)

lsps = c.get("language-server", {})

for lsp in lsps.values():
    # Margs command and args
    lsp["command"] = [lsp["command"], *lsp.get("args", [])]
    del lsp["command"]
    if "args" in lsp:
        del lsp["args"]
    # Rename settings to config
    if "settings" in lsp:
        lsp["config"] = lsp["settings"]
        del lsp["settings"]

# Assign languages to LSPs
for lang in c.get("language", []):
    for name in lang.get("language-servers", []):
        if isinstance(name, str) and (lsp := lsps.get(name, {})):
            if "languages" not in lsp:
                lsp["languages"] = set()
            lsp["languages"].add(lang["name"])

print(lsps)
