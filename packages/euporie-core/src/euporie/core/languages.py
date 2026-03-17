"""Language support reference data.

Auto-generated from Helix editor's languages.toml by
scripts/clone_helix_lsp_config.py — do not edit manually.
"""

from __future__ import annotations

from typing import Any

KNOWN_LANGUAGES: dict[str, dict[str, Any]] = {
    "rust": {
        "language_servers": ["rust-analyzer"],
        "comment_token": ["//", "///", "//!"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["rs"],
        "formatters": [],
    },
    "sway": {
        "language_servers": ["forc"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["sw"],
        "formatters": [],
    },
    "toml": {
        "language_servers": ["taplo", "tombi"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["toml"],
        "formatters": [],
    },
    "awk": {
        "language_servers": ["awk-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["awk", "gawk", "nawk", "mawk"],
        "formatters": [],
    },
    "protobuf": {
        "language_servers": ["buf", "pbkit", "protols"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["proto"],
        "formatters": [],
    },
    "textproto": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["txtpb", "textpb", "textproto"],
        "formatters": ["txtpbfmt"],
    },
    "eiffel": {
        "language_servers": ["eiffel-language-server"],
        "comment_token": ["--"],
        "indent": None,
        "file_types": ["e"],
        "formatters": [],
    },
    "elixir": {
        "language_servers": ["elixir-ls", "expert"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ex", "exs"],
        "formatters": [],
    },
    "fennel": {
        "language_servers": ["fennel-ls"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["fnl", "fnlm"],
        "formatters": ["fnlfmt"],
    },
    "fish": {
        "language_servers": ["fish-lsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["fish"],
        "formatters": ["fish_indent"],
    },
    "flatbuffers": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": " ",
        },
        "file_types": ["fbs"],
        "formatters": [],
    },
    "mint": {
        "language_servers": ["mint"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["mint"],
        "formatters": [],
    },
    "mojo": {
        "language_servers": ["mojo-lsp-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["mojo", "🔥"],
        "formatters": ["pixi"],
    },
    "janet": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cgen", "janet", "jdn"],
        "formatters": ["janet-format"],
    },
    "json": {
        "language_servers": ["vscode-json-language-server"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "json",
            "arb",
            "ipynb",
            "geojson",
            "gltf",
            "webmanifest",
            "js.map",
            "ts.map",
            "css.map",
            "jsonl",
            "avsc",
            "ldtk",
            "ldtkl",
            "sublime-build",
            "sublime-color-scheme",
            "sublime-commands",
            "sublime-completions",
            "sublime-keymap",
            "sublime-macro",
            "sublime-menu",
            "sublime-mousemap",
            "sublime-project",
            "sublime-settings",
            "sublime-theme",
            "sublime-workspace",
            "code-workspace",
        ],
        "formatters": [],
    },
    "jsonc": {
        "language_servers": ["vscode-json-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["jsonc"],
        "formatters": [],
    },
    "json-ld": {
        "language_servers": ["vscode-json-language-server"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["jsonld"],
        "formatters": [],
    },
    "json5": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["json5"],
        "formatters": [],
    },
    "c": {
        "language_servers": ["clangd"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["c"],
        "formatters": [],
    },
    "cpp": {
        "language_servers": ["clangd"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "cc",
            "hh",
            "c++",
            "cpp",
            "hpp",
            "h",
            "ipp",
            "tpp",
            "cxx",
            "hxx",
            "ixx",
            "txx",
            "ino",
            "C",
            "H",
            "cu",
            "cuh",
            "cppm",
            "h++",
            "ii",
            "inl",
        ],
        "formatters": [],
    },
    "crystal": {
        "language_servers": ["crystalline", "ameba-ls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cr"],
        "formatters": ["crystal"],
    },
    "c-sharp": {
        "language_servers": ["roslyn-language-server", "omnisharp", "csharp-ls"],
        "comment_token": ["//", "///"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["cs", "csx", "cake"],
        "formatters": [],
    },
    "c3": {
        "language_servers": ["c3-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["c3", "c3i", "c3t"],
        "formatters": [],
    },
    "cel": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cel"],
        "formatters": [],
    },
    "spicedb": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["zed"],
        "formatters": [],
    },
    "go": {
        "language_servers": ["gopls", "golangci-lint-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["go"],
        "formatters": [],
    },
    "gomod": {
        "language_servers": ["gopls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": [],
        "formatters": [],
    },
    "gotmpl": {
        "language_servers": ["gopls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": " ",
        },
        "file_types": ["gotmpl"],
        "formatters": [],
    },
    "gowork": {
        "language_servers": ["gopls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": [],
        "formatters": [],
    },
    "go-format-string": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "javascript": {
        "language_servers": ["typescript-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["js", "mjs", "cjs", "rules", "es6", "pac", "gs"],
        "formatters": [],
    },
    "jsx": {
        "language_servers": ["typescript-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["jsx"],
        "formatters": [],
    },
    "typescript": {
        "language_servers": ["typescript-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ts", "mts", "cts"],
        "formatters": [],
    },
    "typespec": {
        "language_servers": ["typespec"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["tsp"],
        "formatters": [],
    },
    "tsx": {
        "language_servers": ["typescript-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["tsx"],
        "formatters": [],
    },
    "css": {
        "language_servers": ["vscode-css-language-server"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["css"],
        "formatters": [],
    },
    "scss": {
        "language_servers": ["vscode-css-language-server"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["scss"],
        "formatters": [],
    },
    "less": {
        "language_servers": ["vscode-css-language-server"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["less"],
        "formatters": [],
    },
    "html": {
        "language_servers": ["vscode-html-language-server", "superhtml"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "html",
            "htm",
            "shtml",
            "xhtml",
            "xht",
            "jsp",
            "asp",
            "aspx",
            "jshtm",
            "volt",
            "rhtml",
            "cshtml",
        ],
        "formatters": [],
    },
    "htmldjango": {
        "language_servers": ["djlsp", "vscode-html-language-server", "superhtml"],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "python": {
        "language_servers": ["ty", "ruff", "jedi", "pylsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["py", "pyi", "py3", "pyw", "ptl", "rpy", "cpy", "ipy", "pyt"],
        "formatters": [],
    },
    "nickel": {
        "language_servers": ["nls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ncl"],
        "formatters": [],
    },
    "nix": {
        "language_servers": ["nil", "nixd"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["nix"],
        "formatters": ["nixfmt"],
    },
    "ruby": {
        "language_servers": ["ruby-lsp", "solargraph"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "rb",
            "rake",
            "irb",
            "gemspec",
            "rabl",
            "jbuilder",
            "jb",
            "podspec",
            "rjs",
            "rbi",
            "rbs",
        ],
        "formatters": [],
    },
    "rshtml": {
        "language_servers": [
            "rshtml-analyzer",
            "vscode-html-language-server",
            "superhtml",
        ],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "bash": {
        "language_servers": ["bash-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "sh",
            "bash",
            "ash",
            "dash",
            "ksh",
            "mksh",
            "zsh",
            "zshenv",
            "zlogin",
            "zlogout",
            "zprofile",
            "zshrc",
            "eclass",
            "ebuild",
            "bazelrc",
            "Renviron",
            "zsh-theme",
            "cshrc",
            "tcshrc",
            "bashrc_Apple_Terminal",
            "zshrc_Apple_Terminal",
        ],
        "formatters": [],
    },
    "php": {
        "language_servers": ["intelephense"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["php", "inc", "php4", "php5", "phtml", "ctp"],
        "formatters": [],
    },
    "php-only": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "blade": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["blade"],
        "formatters": [],
    },
    "twig": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["twig"],
        "formatters": [],
    },
    "latex": {
        "language_servers": ["texlab"],
        "comment_token": ["%"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["tex", "sty", "cls", "Rd", "bbx", "cbx"],
        "formatters": [],
    },
    "bibtex": {
        "language_servers": ["texlab"],
        "comment_token": ["%"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["bib"],
        "formatters": ["bibtex-tidy"],
    },
    "lean": {
        "language_servers": ["lean"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["lean"],
        "formatters": [],
    },
    "lpf": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["lpf"],
        "formatters": [],
    },
    "julia": {
        "language_servers": ["julia"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["jl"],
        "formatters": [],
    },
    "java": {
        "language_servers": ["jdtls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["java", "jav", "pde"],
        "formatters": [],
    },
    "smali": {
        "language_servers": ["smalisp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["smali"],
        "formatters": [],
    },
    "ledger": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["ldg", "ledger", "journal"],
        "formatters": [],
    },
    "beancount": {
        "language_servers": ["beancount-language-server"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["beancount", "bean"],
        "formatters": [],
    },
    "ocaml": {
        "language_servers": ["ocamllsp"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ml"],
        "formatters": [],
    },
    "ocaml-interface": {
        "language_servers": ["ocamllsp"],
        "comment_token": ["(**)"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["mli"],
        "formatters": [],
    },
    "dune": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 1,
            "unit": " ",
        },
        "file_types": [],
        "formatters": ["dune"],
    },
    "lua": {
        "language_servers": ["lua-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["lua", "rockspec"],
        "formatters": [],
    },
    "luap": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "lua-format-string": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "teal": {
        "language_servers": ["teal-language-server"],
        "comment_token": ["--"],
        "indent": None,
        "file_types": ["tl"],
        "formatters": [],
    },
    "svelte": {
        "language_servers": ["svelteserver"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["svelte"],
        "formatters": [],
    },
    "vue": {
        "language_servers": ["vuels"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["vue"],
        "formatters": [],
    },
    "yaml": {
        "language_servers": ["yaml-language-server", "ansible-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["yml", "yaml", "sublime-syntax", "bu"],
        "formatters": ["yamlfmt"],
    },
    "nestedtext": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["nt"],
        "formatters": [],
    },
    "haskell": {
        "language_servers": ["haskell-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["hs", "hs-boot", "hsc"],
        "formatters": [],
    },
    "haskell-persistent": {
        "language_servers": [],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["persistentmodels"],
        "formatters": [],
    },
    "haskell-literate": {
        "language_servers": ["haskell-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["lhs"],
        "formatters": [],
    },
    "purescript": {
        "language_servers": ["purescript-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["purs"],
        "formatters": ["purs-tidy"],
    },
    "zig": {
        "language_servers": ["zls"],
        "comment_token": ["//", "///", "//!"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["zig", "zon"],
        "formatters": ["zig"],
    },
    "picat": {
        "language_servers": [],
        "comment_token": ["%"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["pi", "picat"],
        "formatters": [],
    },
    "prolog": {
        "language_servers": ["swipl"],
        "comment_token": ["%"],
        "indent": None,
        "file_types": ["pl", "prolog"],
        "formatters": [],
    },
    "tsq": {
        "language_servers": ["ts_query_ls"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "cmake": {
        "language_servers": ["neocmakelsp", "cmake-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cmake"],
        "formatters": [],
    },
    "make": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["make", "mk", "mak"],
        "formatters": [],
    },
    "glsl": {
        "language_servers": ["glsl_analyzer", "glsld"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["glsl", "vert", "tesc", "tese", "geom", "frag", "comp"],
        "formatters": [],
    },
    "penrose": {
        "language_servers": [],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["substance", "style", "domain"],
        "formatters": [],
    },
    "perl": {
        "language_servers": ["perlnavigator"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "pl",
            "pm",
            "t",
            "psgi",
            "raku",
            "rakumod",
            "rakutest",
            "rakudoc",
            "nqp",
            "p6",
            "pl6",
            "pm6",
        ],
        "formatters": [],
    },
    "embedded-perl": {
        "language_servers": [],
        "comment_token": ["%#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ep"],
        "formatters": [],
    },
    "pod": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["pod"],
        "formatters": [],
    },
    "racket": {
        "language_servers": ["racket"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["rkt", "rktd", "rktl", "scrbl", "zuo"],
        "formatters": [],
    },
    "common-lisp": {
        "language_servers": ["cl-lsp"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["lisp", "asd", "cl", "l", "lsp", "ny", "podsl", "ros", "sexp"],
        "formatters": [],
    },
    "comment": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "wesl": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["wesl"],
        "formatters": [],
    },
    "wgsl": {
        "language_servers": ["wgsl-analyzer"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["wgsl"],
        "formatters": [],
    },
    "llvm": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ll"],
        "formatters": [],
    },
    "llvm-mir": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "llvm-mir-yaml": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["mir"],
        "formatters": [],
    },
    "tablegen": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["td"],
        "formatters": [],
    },
    "mail": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["eml"],
        "formatters": [],
    },
    "markdown": {
        "language_servers": ["marksman", "markdown-oxide", "rumdl"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "md",
            "livemd",
            "markdown",
            "mdx",
            "mkd",
            "mkdn",
            "mdwn",
            "mdown",
            "markdn",
            "mdtxt",
            "mdtext",
            "workbook",
        ],
        "formatters": [],
    },
    "markdown-rustdoc": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "markdown.inline": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "djot": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["dj", "djot"],
        "formatters": [],
    },
    "dart": {
        "language_servers": ["dart"],
        "comment_token": ["//", "///"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["dart"],
        "formatters": [],
    },
    "scala": {
        "language_servers": ["metals"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["scala", "sbt", "sc"],
        "formatters": [],
    },
    "dockerfile": {
        "language_servers": ["docker-langserver", "docker-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "  ",
        },
        "file_types": ["Dockerfile", "dockerfile", "Containerfile", "containerfile"],
        "formatters": ["dockerfmt"],
    },
    "docker-compose": {
        "language_servers": [
            "docker-compose-langserver",
            "yaml-language-server",
            "docker-language-server",
        ],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "git-commit": {
        "language_servers": ["commit-lsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "git-notes": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "github-action": {
        "language_servers": [
            "actions-language-server",
            "yaml-language-server",
            "zizmor",
        ],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "diff": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["diff", "patch", "rej"],
        "formatters": [],
    },
    "git-rebase": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "\t",
        },
        "file_types": [],
        "formatters": [],
    },
    "regex": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["regex"],
        "formatters": [],
    },
    "git-config": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["gitconfig"],
        "formatters": [],
    },
    "git-attributes": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "git-ignore": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "graphql": {
        "language_servers": ["graphql-language-service"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gql", "graphql", "graphqls"],
        "formatters": [],
    },
    "elm": {
        "language_servers": ["elm-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["elm"],
        "formatters": [],
    },
    "iex": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["iex"],
        "formatters": [],
    },
    "rescript": {
        "language_servers": ["rescript-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["res"],
        "formatters": [],
    },
    "erlang": {
        "language_servers": ["erlang-ls", "elp"],
        "comment_token": ["%%"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["erl", "hrl", "app"],
        "formatters": [],
    },
    "kotlin": {
        "language_servers": ["kotlin-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["kt", "kts"],
        "formatters": [],
    },
    "hcl": {
        "language_servers": ["terraform-ls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["hcl", "tf", "nomad"],
        "formatters": [],
    },
    "tfvars": {
        "language_servers": ["terraform-ls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["tfvars"],
        "formatters": [],
    },
    "org": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["org"],
        "formatters": [],
    },
    "solidity": {
        "language_servers": ["solc"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["sol"],
        "formatters": [],
    },
    "gleam": {
        "language_servers": ["gleam"],
        "comment_token": ["//", "///", "////"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gleam"],
        "formatters": [],
    },
    "quarto": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["qmd"],
        "formatters": [],
    },
    "ron": {
        "language_servers": ["ron-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["ron"],
        "formatters": [],
    },
    "robot": {
        "language_servers": ["robotcode", "robotframework_ls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": " ",
        },
        "file_types": ["robot", "resource"],
        "formatters": [],
    },
    "r": {
        "language_servers": ["r"],
        "comment_token": ["#", "#'"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["r", "R"],
        "formatters": [],
    },
    "rmarkdown": {
        "language_servers": ["r"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["rmd", "Rmd"],
        "formatters": [],
    },
    "swift": {
        "language_servers": ["sourcekit-lsp"],
        "comment_token": ["//"],
        "indent": None,
        "file_types": ["swift", "swiftinterface"],
        "formatters": ["swift-format"],
    },
    "erb": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["erb"],
        "formatters": [],
    },
    "ejs": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ejs"],
        "formatters": [],
    },
    "eex": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["eex"],
        "formatters": [],
    },
    "heex": {
        "language_servers": ["elixir-ls", "expert"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["heex"],
        "formatters": [],
    },
    "sql": {
        "language_servers": [],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["sql", "dsql"],
        "formatters": [],
    },
    "gdscript": {
        "language_servers": [],
        "comment_token": ["#", "##"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["gd"],
        "formatters": ["gdformat"],
    },
    "godot-resource": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["tscn", "tres", "godot", "gdextension"],
        "formatters": [],
    },
    "nu": {
        "language_servers": ["nu-lsp", "nu-lint"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["nu", "nuon"],
        "formatters": ["nufmt"],
    },
    "vala": {
        "language_servers": ["vala-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["vala", "vapi"],
        "formatters": [],
    },
    "hare": {
        "language_servers": ["hare-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 8,
            "unit": "\t",
        },
        "file_types": ["ha"],
        "formatters": [],
    },
    "devicetree": {
        "language_servers": ["dts-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["dts", "dtsi"],
        "formatters": [],
    },
    "cairo": {
        "language_servers": ["cairo-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["cairo"],
        "formatters": [],
    },
    "cpon": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cpon", "cp"],
        "formatters": [],
    },
    "odin": {
        "language_servers": ["ols"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["odin"],
        "formatters": ["odinfmt"],
    },
    "meson": {
        "language_servers": ["mesonlsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "sshclientconfig": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "scheme": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ss", "scm", "sld"],
        "formatters": [],
    },
    "v": {
        "language_servers": ["vlang-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["v", "vv", "vsh"],
        "formatters": [],
    },
    "verilog": {
        "language_servers": ["verible-verilog-ls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["v", "vh"],
        "formatters": [],
    },
    "systemverilog": {
        "language_servers": ["svlangserver", "verible-verilog-ls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["sv", "svh"],
        "formatters": [],
    },
    "edoc": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["edoc", "edoc.in"],
        "formatters": [],
    },
    "jsdoc": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["jsdoc"],
        "formatters": [],
    },
    "openscad": {
        "language_servers": ["openscad-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "\t",
        },
        "file_types": ["scad"],
        "formatters": [],
    },
    "prisma": {
        "language_servers": ["prisma-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["prisma"],
        "formatters": [],
    },
    "clojure": {
        "language_servers": ["clojure-lsp"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["clj", "cljs", "cljc", "clje", "cljr", "cljx", "edn", "boot"],
        "formatters": [],
    },
    "starlark": {
        "language_servers": ["starpls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["bzl", "bazel", "star"],
        "formatters": [],
    },
    "elvish": {
        "language_servers": ["elvish"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["elv"],
        "formatters": [],
    },
    "idris": {
        "language_servers": ["idris2-lsp"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["idr"],
        "formatters": [],
    },
    "fortran": {
        "language_servers": ["fortls"],
        "comment_token": ["!"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["f", "for", "f90", "f95", "f03", "F", "F90", "F95", "F03"],
        "formatters": [],
    },
    "ungrammar": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ungram", "ungrammar"],
        "formatters": [],
    },
    "dot": {
        "language_servers": ["dot-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["dot"],
        "formatters": [],
    },
    "cue": {
        "language_servers": ["cuelsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["cue"],
        "formatters": ["cue"],
    },
    "slang": {
        "language_servers": ["slangd"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "  ",
        },
        "file_types": ["slang"],
        "formatters": [],
    },
    "slint": {
        "language_servers": ["slint-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["slint"],
        "formatters": [],
    },
    "task": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["task"],
        "formatters": [],
    },
    "xit": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["xit"],
        "formatters": [],
    },
    "esdl": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gel", "esdl"],
        "formatters": [],
    },
    "pascal": {
        "language_servers": ["pasls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["pas", "pp", "inc", "lpr", "lfm"],
        "formatters": [],
    },
    "sml": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["sml"],
        "formatters": [],
    },
    "jsonnet": {
        "language_servers": ["jsonnet-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["libsonnet", "jsonnet"],
        "formatters": [],
    },
    "ada": {
        "language_servers": ["ada-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 3,
            "unit": "   ",
        },
        "file_types": ["adb", "ads"],
        "formatters": [],
    },
    "astro": {
        "language_servers": ["astro-ls"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["astro"],
        "formatters": [],
    },
    "bass": {
        "language_servers": ["bass"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["bass"],
        "formatters": [],
    },
    "wat": {
        "language_servers": ["wasm-language-tools"],
        "comment_token": [";;"],
        "indent": None,
        "file_types": ["wat"],
        "formatters": [],
    },
    "wast": {
        "language_servers": [],
        "comment_token": [";;"],
        "indent": None,
        "file_types": ["wast"],
        "formatters": [],
    },
    "d": {
        "language_servers": ["serve-d"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["d", "dd"],
        "formatters": ["dfmt"],
    },
    "vhs": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["tape"],
        "formatters": [],
    },
    "kdl": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": None,
        "file_types": ["kdl"],
        "formatters": ["kdlfmt"],
    },
    "xml": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [
            "ascx",
            "atom",
            "axaml",
            "axml",
            "bpmn",
            "checkstyle",
            "cpt",
            "csl",
            "csproj.user",
            "dita",
            "ditamap",
            "dtml",
            "fods",
            "fodt",
            "fxml",
            "gir",
            "glif",
            "gml",
            "gpx",
            "iml",
            "isml",
            "itermcolors",
            "jmx",
            "kml",
            "launch",
            "menu",
            "mobileconfig",
            "mpd",
            "musicxml",
            "mxml",
            "ncx",
            "nuspec",
            "opml",
            "osc",
            "osm",
            "plist",
            "policy",
            "pt",
            "publishsettings",
            "pubxml",
            "pubxml.user",
            "rbxlx",
            "rbxmx",
            "resx",
            "rng",
            "rss",
            "shproj",
            "smil",
            "storyboard",
            "sublime-snippet",
            "svg",
            "terminal",
            "tld",
            "tmx",
            "ui",
            "vbproj.user",
            "vcxproj",
            "vcxproj.filters",
            "wixproj",
            "wsdl",
            "wxi",
            "wxs",
            "xaml",
            "xbl",
            "xib",
            "xlf",
            "xliff",
            "xml",
            "xmp",
            "xoml",
            "xpdl",
            "xrc",
            "xsd",
            "xsl",
            "xul",
        ],
        "formatters": [],
    },
    "dtd": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["dtd", "ent"],
        "formatters": [],
    },
    "wit": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["wit"],
        "formatters": [],
    },
    "env": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": [],
        "formatters": [],
    },
    "systemd": {
        "language_servers": ["systemd-lsp"],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [
            "service",
            "automount",
            "device",
            "mount",
            "nspawn",
            "path",
            "scope",
            "slice",
            "socket",
            "swap",
            "target",
            "timer",
        ],
        "formatters": [],
    },
    "ini": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": [
            "ini",
            "desktop",
            "container",
            "volume",
            "kube",
            "network",
            "properties",
            "cfg",
            "directory",
        ],
        "formatters": [],
    },
    "inko": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["inko"],
        "formatters": ["inko"],
    },
    "bicep": {
        "language_servers": ["bicep-langserver"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": " ",
        },
        "file_types": ["bicep", "bicepparam"],
        "formatters": [],
    },
    "qml": {
        "language_servers": ["qmlls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["qml"],
        "formatters": [],
    },
    "mermaid": {
        "language_servers": [],
        "comment_token": ["%%"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["mermaid", "mmd"],
        "formatters": [],
    },
    "matlab": {
        "language_servers": [],
        "comment_token": ["%"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["m"],
        "formatters": [],
    },
    "ponylang": {
        "language_servers": ["pony-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["pony"],
        "formatters": [],
    },
    "dhall": {
        "language_servers": ["dhall-lsp-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["dhall"],
        "formatters": ["dhall"],
    },
    "sage": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["sage"],
        "formatters": [],
    },
    "msbuild": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["proj", "vbproj", "csproj", "fsproj", "targets", "props"],
        "formatters": [],
    },
    "pem": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["pem", "cert", "crt"],
        "formatters": [],
    },
    "passwd": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "hosts": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "uxntal": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["tal"],
        "formatters": [],
    },
    "yuck": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["yuck"],
        "formatters": [],
    },
    "prql": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["prql"],
        "formatters": [],
    },
    "po": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["po", "pot"],
        "formatters": [],
    },
    "nasm": {
        "language_servers": ["asm-lsp"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 8,
            "unit": "        ",
        },
        "file_types": ["asm", "S", "nasm"],
        "formatters": [],
    },
    "gas": {
        "language_servers": ["asm-lsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 8,
            "unit": "        ",
        },
        "file_types": ["s"],
        "formatters": [],
    },
    "rst": {
        "language_servers": [],
        "comment_token": [".."],
        "indent": None,
        "file_types": ["rst"],
        "formatters": [],
    },
    "capnp": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["capnp"],
        "formatters": [],
    },
    "smithy": {
        "language_servers": ["cs"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["smithy"],
        "formatters": [],
    },
    "hdl": {
        "language_servers": ["hdls"],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["hdl"],
        "formatters": [],
    },
    "vhdl": {
        "language_servers": ["vhdl_ls"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["vhd", "vhdl"],
        "formatters": [],
    },
    "rego": {
        "language_servers": ["regols"],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["rego"],
        "formatters": [],
    },
    "nim": {
        "language_servers": ["nimlangserver"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["nim", "nims", "nimble"],
        "formatters": [],
    },
    "cabal": {
        "language_servers": ["haskell-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cabal"],
        "formatters": [],
    },
    "hurl": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["hurl"],
        "formatters": ["hurlfmt"],
    },
    "markdoc": {
        "language_servers": ["markdoc-ls"],
        "comment_token": [],
        "indent": None,
        "file_types": ["mdoc"],
        "formatters": [],
    },
    "opencl": {
        "language_servers": ["clangd"],
        "comment_token": ["//"],
        "indent": None,
        "file_types": ["cl"],
        "formatters": [],
    },
    "just": {
        "language_servers": ["just-lsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["just"],
        "formatters": [],
    },
    "gn": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gn", "gni"],
        "formatters": ["gn"],
    },
    "blueprint": {
        "language_servers": ["blueprint-compiler"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["blp"],
        "formatters": [],
    },
    "forth": {
        "language_servers": ["forth-lsp"],
        "comment_token": ["\\"],
        "indent": {
            "tab_width": 3,
            "unit": "   ",
        },
        "file_types": ["fs", "forth", "fth", "4th"],
        "formatters": [],
    },
    "fsharp": {
        "language_servers": ["fsharp-ls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["fs", "fsx", "fsi", "fsscript"],
        "formatters": [],
    },
    "t32": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["cmm", "t32"],
        "formatters": [],
    },
    "webc": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["webc"],
        "formatters": [],
    },
    "typst": {
        "language_servers": ["tinymist"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["typst", "typ"],
        "formatters": [],
    },
    "nunjucks": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["njk"],
        "formatters": [],
    },
    "jinja": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["jinja", "jinja2", "j2"],
        "formatters": [],
    },
    "jjconfig": {
        "language_servers": ["taplo", "tombi"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "jjdescription": {
        "language_servers": [],
        "comment_token": ["JJ:"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "jjrevset": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["jjrevset"],
        "formatters": [],
    },
    "jjtemplate": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["jjtemplate"],
        "formatters": [],
    },
    "miseconfig": {
        "language_servers": ["taplo", "tombi"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "jq": {
        "language_servers": ["jq-lsp"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["jq"],
        "formatters": [],
    },
    "wren": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["wren"],
        "formatters": [],
    },
    "unison": {
        "language_servers": [],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["u"],
        "formatters": [],
    },
    "todotxt": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["todotxt"],
        "formatters": ["sort"],
    },
    "strace": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["strace"],
        "formatters": [],
    },
    "gemini": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["gmi"],
        "formatters": [],
    },
    "agda": {
        "language_servers": [],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["agda"],
        "formatters": [],
    },
    "templ": {
        "language_servers": ["templ"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["templ"],
        "formatters": [],
    },
    "dbml": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["dbml"],
        "formatters": [],
    },
    "bitbake": {
        "language_servers": ["bitbake-language-server"],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["bb", "bbappend", "bbclass"],
        "formatters": [],
    },
    "log": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["log"],
        "formatters": [],
    },
    "hoon": {
        "language_servers": [],
        "comment_token": ["::"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["hoon"],
        "formatters": [],
    },
    "hocon": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "koka": {
        "language_servers": ["koka"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 8,
            "unit": "  ",
        },
        "file_types": ["kk"],
        "formatters": [],
    },
    "tact": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["tact"],
        "formatters": [],
    },
    "pkl": {
        "language_servers": ["pkl-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["pkl", "pcf"],
        "formatters": [],
    },
    "groovy": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gradle", "groovy", "jenkinsfile"],
        "formatters": [],
    },
    "fidl": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["fidl"],
        "formatters": [],
    },
    "powershell": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["ps1", "psm1", "psd1", "pscc", "psrc"],
        "formatters": [],
    },
    "ld": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ld"],
        "formatters": [],
    },
    "hy": {
        "language_servers": ["hyuga"],
        "comment_token": [";"],
        "indent": {
            "tab_width": 1,
            "unit": " ",
        },
        "file_types": ["hy"],
        "formatters": [],
    },
    "hyprlang": {
        "language_servers": ["hyprls"],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "tcl": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["tcl"],
        "formatters": [],
    },
    "supercollider": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["scd", "sc", "quark"],
        "formatters": [],
    },
    "rpmspec": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["spec"],
        "formatters": [],
    },
    "pkgbuild": {
        "language_servers": ["termux-language-server", "bash-language-server"],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "helm": {
        "language_servers": ["helm_ls"],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "glimmer": {
        "language_servers": ["ember-language-server"],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": ["prettier"],
    },
    "ohm": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ohm"],
        "formatters": [],
    },
    "earthfile": {
        "language_servers": ["earthlyls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "adl": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["adl"],
        "formatters": [],
    },
    "ldif": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["ldif"],
        "formatters": [],
    },
    "xtc": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": None,
        "file_types": ["xtc", "xpc", "xoa"],
        "formatters": [],
    },
    "move": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["move"],
        "formatters": [],
    },
    "pest": {
        "language_servers": ["pest-language-server"],
        "comment_token": ["//", "///", "//!"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["pest"],
        "formatters": [],
    },
    "elisp": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": None,
        "file_types": ["el"],
        "formatters": [],
    },
    "gjs": {
        "language_servers": [
            "typescript-language-server",
            "vscode-eslint-language-server",
            "ember-language-server",
        ],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gjs"],
        "formatters": [],
    },
    "gts": {
        "language_servers": [
            "typescript-language-server",
            "vscode-eslint-language-server",
            "ember-language-server",
        ],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["gts"],
        "formatters": [],
    },
    "gherkin": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["feature"],
        "formatters": [],
    },
    "thrift": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["thrift"],
        "formatters": [],
    },
    "circom": {
        "language_servers": ["circom-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["circom"],
        "formatters": [],
    },
    "snakemake": {
        "language_servers": ["pylsp"],
        "comment_token": ["#", "##"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["smk"],
        "formatters": ["snakefmt"],
    },
    "cylc": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["cylc"],
        "formatters": [],
    },
    "quint": {
        "language_servers": ["quint-language-server"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["qnt"],
        "formatters": [],
    },
    "spade": {
        "language_servers": ["spade-language-server"],
        "comment_token": ["//", "///"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["spade"],
        "formatters": [],
    },
    "amber": {
        "language_servers": ["amber-lsp"],
        "comment_token": ["//", "///"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["ab"],
        "formatters": [],
    },
    "koto": {
        "language_servers": ["koto-ls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["koto"],
        "formatters": ["koto"],
    },
    "gpr": {
        "language_servers": ["ada-gpr-language-server"],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 3,
            "unit": "   ",
        },
        "file_types": ["gpr"],
        "formatters": [],
    },
    "vento": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["vto"],
        "formatters": [],
    },
    "nginx": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "codeql": {
        "language_servers": ["codeql"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ql", "qll"],
        "formatters": [],
    },
    "gren": {
        "language_servers": [],
        "comment_token": ["--"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["gren"],
        "formatters": [],
    },
    "ghostty": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ghostty"],
        "formatters": [],
    },
    "tera": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["tera"],
        "formatters": [],
    },
    "fga": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["fga"],
        "formatters": [],
    },
    "csv": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["csv"],
        "formatters": [],
    },
    "yara": {
        "language_servers": ["yls"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["yara", "yar"],
        "formatters": [],
    },
    "ink": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["ink"],
        "formatters": [],
    },
    "sourcepawn": {
        "language_servers": ["sourcepawn-studio"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "  ",
        },
        "file_types": ["sp", "inc"],
        "formatters": [],
    },
    "vim": {
        "language_servers": [],
        "comment_token": ['"'],
        "indent": {
            "tab_width": 4,
            "unit": "\t",
        },
        "file_types": ["vim"],
        "formatters": [],
    },
    "tlaplus": {
        "language_servers": [],
        "comment_token": ["\\*"],
        "indent": {
            "tab_width": 4,
            "unit": " ",
        },
        "file_types": ["tla"],
        "formatters": ["tlafmt"],
    },
    "werk": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["werk"],
        "formatters": [],
    },
    "debian": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["dsc", "changes"],
        "formatters": [],
    },
    "pug": {
        "language_servers": [],
        "comment_token": ["//", "//-"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["pug"],
        "formatters": [],
    },
    "dunstrc": {
        "language_servers": [],
        "comment_token": ["#", ";"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "rust-format-args": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "rust-format-args-macro": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "clarity": {
        "language_servers": ["clarinet"],
        "comment_token": [";;"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["clar"],
        "formatters": [],
    },
    "alloy": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["alloy"],
        "formatters": [],
    },
    "luau": {
        "language_servers": ["luau"],
        "comment_token": ["--", "---"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["luau"],
        "formatters": [],
    },
    "caddyfile": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["Caddyfile", "caddyfile"],
        "formatters": ["caddy"],
    },
    "properties": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": ["properties", "prefs"],
        "formatters": [],
    },
    "robots.txt": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "pip-requirements": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "kconfig": {
        "language_servers": [],
        "comment_token": [],
        "indent": None,
        "file_types": ["Kconfig"],
        "formatters": [],
    },
    "doxyfile": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "cross-config": {
        "language_servers": ["taplo", "tombi"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "git-cliff-config": {
        "language_servers": ["taplo", "tombi"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "cython": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["pxd", "pxi", "pyx"],
        "formatters": [],
    },
    "shellcheckrc": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "strictdoc": {
        "language_servers": [],
        "comment_token": [".."],
        "indent": None,
        "file_types": ["sdoc", "sgra"],
        "formatters": [],
    },
    "docker-bake": {
        "language_servers": ["docker-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "gitlab-ci": {
        "language_servers": ["yaml-language-server", "gitlab-ci-ls"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": [],
    },
    "wikitext": {
        "language_servers": ["wikitext-lsp"],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["wikimedia", "mediawiki", "wikitext"],
        "formatters": [],
    },
    "slisp": {
        "language_servers": [],
        "comment_token": [";"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["sl"],
        "formatters": [],
    },
    "nearley": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["ne"],
        "formatters": [],
    },
    "kcl": {
        "language_servers": ["kcl-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["kcl"],
        "formatters": ["zoo"],
    },
    "bovex": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["bovex", "bibvex"],
        "formatters": [],
    },
    "haxe": {
        "language_servers": ["haxe-language-server"],
        "comment_token": ["//", "///"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["hx"],
        "formatters": [],
    },
    "basic": {
        "language_servers": [],
        "comment_token": ["REM"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["bas"],
        "formatters": [],
    },
    "freebasic": {
        "language_servers": [],
        "comment_token": ["'", "REM"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["bas", "bi"],
        "formatters": [],
    },
    "scfg": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": None,
        "file_types": [],
        "formatters": [],
    },
    "ripple": {
        "language_servers": ["ripple-lsp"],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["ripple"],
        "formatters": [],
    },
    "woodpecker-ci": {
        "language_servers": ["yaml-language-server"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": [],
        "formatters": ["yamlfmt"],
    },
    "chuck": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": [],
        "formatters": [],
    },
    "qmv": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 8,
            "unit": "        ",
        },
        "file_types": [],
        "formatters": [],
    },
    "klog": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["klg"],
        "formatters": [],
    },
    "styx": {
        "language_servers": ["styx"],
        "comment_token": ["//", "///"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["styx"],
        "formatters": [],
    },
    "tilt": {
        "language_servers": ["tilt"],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["tiltfile"],
        "formatters": ["buildifier"],
    },
    "gnuplot": {
        "language_servers": [],
        "comment_token": ["#"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["gnuplot", "plot", "plt"],
        "formatters": [],
    },
    "drools": {
        "language_servers": ["drools-lsp"],
        "comment_token": ["//"],
        "indent": None,
        "file_types": ["drl"],
        "formatters": ["drools-fmt"],
    },
    "proverif": {
        "language_servers": [],
        "comment_token": [],
        "indent": {
            "tab_width": 8,
            "unit": "        ",
        },
        "file_types": ["pv"],
        "formatters": [],
    },
    "ptx": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 4,
            "unit": "    ",
        },
        "file_types": ["ptx"],
        "formatters": [],
    },
    "tql": {
        "language_servers": [],
        "comment_token": ["//"],
        "indent": {
            "tab_width": 2,
            "unit": "  ",
        },
        "file_types": ["tql"],
        "formatters": [],
    },
}

KNOWN_LSP_SERVERS: dict[str, dict[str, Any]] = {
    "ada-gpr-language-server": {
        "command": ["ada_language_server", "--language-gpr"],
    },
    "ada-language-server": {
        "command": ["ada_language_server"],
    },
    "als": {
        "command": ["als"],
    },
    "amber-lsp": {
        "command": ["amber-lsp"],
    },
    "ameba-ls": {
        "command": ["ameba-ls"],
    },
    "angular": {
        "command": [
            "ngserver",
            "--stdio",
            "--tsProbeLocations",
            ".",
            "--ngProbeLocations",
            ".",
        ],
    },
    "asm-lsp": {
        "command": ["asm-lsp"],
    },
    "awk-language-server": {
        "command": ["awk-language-server"],
    },
    "bash-language-server": {
        "command": ["bash-language-server", "start"],
    },
    "bass": {
        "command": ["bass", "--lsp"],
    },
    "beancount-language-server": {
        "command": ["beancount-language-server"],
    },
    "bicep-langserver": {
        "command": ["bicep-langserver"],
    },
    "bitbake-language-server": {
        "command": ["bitbake-language-server"],
    },
    "buf": {
        "command": ["buf", "lsp", "serve", "--timeout", "0"],
    },
    "c3-lsp": {
        "command": ["c3-lsp"],
    },
    "cairo-language-server": {
        "command": ["cairo-language-server"],
    },
    "circom-lsp": {
        "command": ["circom-lsp"],
    },
    "cl-lsp": {
        "command": ["cl-lsp"],
    },
    "clangd": {
        "command": ["clangd"],
    },
    "clojure-lsp": {
        "command": ["clojure-lsp"],
    },
    "cmake-language-server": {
        "command": ["cmake-language-server"],
    },
    "codeql": {
        "command": ["codeql", "execute", "language-server", "--check-errors=ON_CHANGE"],
    },
    "commit-lsp": {
        "command": ["commit-lsp", "run"],
    },
    "crystalline": {
        "command": ["crystalline", "--stdio"],
    },
    "cs": {
        "command": ["cs", "launch", "--contrib", "smithy-language-server", "--", "0"],
    },
    "csharp-ls": {
        "command": ["csharp-ls"],
    },
    "cuelsp": {
        "command": ["cuelsp"],
    },
    "dart": {
        "command": ["dart", "language-server", "--client-id=euporie"],
    },
    "dhall-lsp-server": {
        "command": ["dhall-lsp-server"],
    },
    "djlsp": {
        "command": ["djlsp"],
    },
    "docker-langserver": {
        "command": ["docker-langserver", "--stdio"],
    },
    "docker-compose-langserver": {
        "command": ["docker-compose-langserver", "--stdio"],
    },
    "dot-language-server": {
        "command": ["dot-language-server", "--stdio"],
    },
    "dts-lsp": {
        "command": ["dts-lsp"],
    },
    "earthlyls": {
        "command": ["earthlyls"],
    },
    "eiffel-language-server": {
        "command": ["eiffel-language-server"],
    },
    "elixir-ls": {
        "command": ["elixir-ls"],
        "settings": {
            "elixirLS": {
                "dialyzerEnabled": False,
            },
        },
    },
    "elm-language-server": {
        "command": ["elm-language-server"],
    },
    "elp": {
        "command": ["elp", "server"],
    },
    "elvish": {
        "command": ["elvish", "-lsp"],
    },
    "erlang-ls": {
        "command": ["erlang_ls"],
    },
    "expert": {
        "command": ["expert"],
    },
    "fennel-ls": {
        "command": ["fennel-ls"],
    },
    "fish-lsp": {
        "command": ["fish-lsp", "start"],
    },
    "forc": {
        "command": ["forc", "lsp"],
    },
    "forth-lsp": {
        "command": ["forth-lsp"],
    },
    "fortls": {
        "command": ["fortls", "--lowercase_intrinsics"],
    },
    "fsharp-ls": {
        "command": ["fsautocomplete"],
        "settings": {
            "AutomaticWorkspaceInit": True,
        },
    },
    "gitlab-ci-ls": {
        "command": ["gitlab-ci-ls"],
    },
    "gleam": {
        "command": ["gleam", "lsp"],
    },
    "glsl_analyzer": {
        "command": ["glsl_analyzer"],
    },
    "glsld": {
        "command": ["glsld", "--stdio"],
    },
    "graphql-language-service": {
        "command": ["graphql-lsp", "server", "-m", "stream"],
    },
    "hare-lsp": {
        "command": ["hare-lsp", "-S"],
    },
    "harper-ls": {
        "command": ["harper-ls", "--stdio"],
    },
    "haskell-language-server": {
        "command": ["haskell-language-server-wrapper", "--lsp"],
    },
    "hdls": {
        "command": ["hdls"],
    },
    "hyprls": {
        "command": ["hyprls"],
    },
    "hyuga": {
        "command": ["hyuga"],
    },
    "idris2-lsp": {
        "command": ["idris2-lsp"],
    },
    "intelephense": {
        "command": ["intelephense", "--stdio"],
    },
    "jdtls": {
        "command": ["jdtls"],
    },
    "jedi": {
        "command": ["jedi-language-server"],
    },
    "jq-lsp": {
        "command": ["jq-lsp"],
    },
    "jsonnet-language-server": {
        "command": ["jsonnet-language-server", "-t", "--lint"],
    },
    "julia": {
        "command": [
            "julia",
            "--startup-file=no",
            "--history-file=no",
            "--quiet",
            "-e",
            "using LanguageServer; runserver()",
        ],
        "timeout": 60,
    },
    "just-lsp": {
        "command": ["just-lsp"],
    },
    "koka": {
        "command": ["koka", "--language-server", "--lsstdio"],
    },
    "koto-ls": {
        "command": ["koto-ls"],
    },
    "kotlin-lsp": {
        "command": ["kotlin-lsp", "--stdio"],
    },
    "kotlin-language-server": {
        "command": ["kotlin-language-server"],
    },
    "lean": {
        "command": ["lake", "serve"],
    },
    "ltex-ls": {
        "command": ["ltex-ls"],
    },
    "ltex-ls-plus": {
        "command": ["ltex-ls-plus"],
    },
    "markdoc-ls": {
        "command": ["markdoc-ls", "--stdio"],
    },
    "markdown-oxide": {
        "command": ["markdown-oxide"],
    },
    "marksman": {
        "command": ["marksman", "server"],
    },
    "metals": {
        "command": ["metals"],
        "settings": {
            "isHttpEnabled": True,
            "metals": {
                "inlayHints": {
                    "typeParameters": {
                        "enable": True,
                    },
                    "hintsInPatternMatch": {
                        "enable": True,
                    },
                },
            },
        },
    },
    "mesonlsp": {
        "command": ["mesonlsp", "--lsp"],
    },
    "mint": {
        "command": ["mint", "tool", "ls"],
    },
    "mojo-lsp-server": {
        "command": ["pixi", "run", "mojo-lsp-server"],
    },
    "neocmakelsp": {
        "command": ["neocmakelsp", "stdio"],
    },
    "nil": {
        "command": ["nil"],
    },
    "nimlangserver": {
        "command": ["nimlangserver"],
    },
    "nimlsp": {
        "command": ["nimlsp"],
    },
    "nixd": {
        "command": ["nixd"],
    },
    "nls": {
        "command": ["nls"],
    },
    "nu-lint": {
        "command": ["nu-lint", "--lsp"],
    },
    "nu-lsp": {
        "command": ["nu", "--lsp"],
    },
    "ocamllsp": {
        "command": ["ocamllsp"],
    },
    "ols": {
        "command": ["ols"],
    },
    "oxlint-language-server": {
        "command": ["oxlint", "--lsp"],
    },
    "omnisharp": {
        "command": ["OmniSharp", "--languageserver"],
    },
    "openscad-lsp": {
        "command": ["openscad-lsp", "--stdio"],
    },
    "pasls": {
        "command": ["pasls"],
    },
    "pbkit": {
        "command": ["pb", "lsp"],
    },
    "perlnavigator": {
        "command": ["perlnavigator", "--stdio"],
    },
    "pest-language-server": {
        "command": ["pest-language-server"],
    },
    "pkl-lsp": {
        "command": ["pkl-lsp"],
    },
    "pony-lsp": {
        "command": ["pony-lsp", "--stdio"],
        "settings": {
            "defines": [],
            "ponypath": [],
        },
    },
    "prisma-language-server": {
        "command": ["prisma-language-server", "--stdio"],
        "settings": {
            "prisma": {
                "enableDiagnostics": True,
            },
        },
    },
    "purescript-language-server": {
        "command": ["purescript-language-server", "--stdio"],
    },
    "pylsp": {
        "command": ["pylsp"],
    },
    "pyrefly": {
        "command": ["pyrefly", "lsp"],
    },
    "pyright": {
        "command": ["pyright-langserver", "--stdio"],
        "settings": {},
    },
    "protols": {
        "command": ["protols"],
    },
    "basedpyright": {
        "command": ["basedpyright-langserver", "--stdio"],
        "settings": {},
    },
    "pylyzer": {
        "command": ["pylyzer", "--server"],
    },
    "pytest-language-server": {
        "command": ["pytest-language-server"],
    },
    "qmlls": {
        "command": ["qmlls"],
    },
    "quint-language-server": {
        "command": ["quint-language-server", "--stdio"],
    },
    "r": {
        "command": ["R", "--no-echo", "-e", "languageserver::run()"],
    },
    "racket": {
        "command": ["racket", "-l", "racket-langserver"],
    },
    "regols": {
        "command": ["regols"],
    },
    "rescript-language-server": {
        "command": ["rescript-language-server", "--stdio"],
    },
    "ripple-lsp": {
        "command": ["ripple-language-server", "--stdio"],
    },
    "robotcode": {
        "command": ["robotcode", "language-server", "--stdio"],
    },
    "robotframework_ls": {
        "command": ["robotframework_ls"],
    },
    "ron-lsp": {
        "command": ["ron-lsp"],
    },
    "roslyn-language-server": {
        "command": ["roslyn-language-server", "--stdio", "--autoLoadProjects"],
    },
    "ruff": {
        "command": ["ruff", "server"],
    },
    "ruby-lsp": {
        "command": ["ruby-lsp"],
    },
    "rshtml-analyzer": {
        "command": ["rshtml-analyzer", "--stdio"],
    },
    "rumdl": {
        "command": ["rumdl", "server"],
    },
    "serve-d": {
        "command": ["serve-d"],
    },
    "slangd": {
        "command": ["slangd"],
    },
    "slint-lsp": {
        "command": ["slint-lsp"],
    },
    "smalisp": {
        "command": ["smalisp"],
    },
    "systemd-lsp": {
        "command": ["systemd-lsp"],
    },
    "solargraph": {
        "command": ["solargraph", "stdio"],
    },
    "solc": {
        "command": ["solc", "--lsp"],
    },
    "sourcekit-lsp": {
        "command": ["sourcekit-lsp"],
    },
    "spade-language-server": {
        "command": ["spade-language-server"],
    },
    "starpls": {
        "command": ["starpls"],
    },
    "styx": {
        "command": ["styx", "lsp"],
    },
    "svlangserver": {
        "command": ["svlangserver"],
        "settings": {
            "systemverilog": {
                "includeIndexing": ["*.{v,vh,sv,svh}", "**/*.{v,vh,sv,svh}"],
            },
        },
    },
    "swipl": {
        "command": [
            "swipl",
            "-g",
            "use_module(library(lsp_server))",
            "-g",
            "lsp_server:main",
            "-t",
            "halt",
            "--",
            "stdio",
        ],
    },
    "superhtml": {
        "command": ["superhtml", "lsp"],
    },
    "tailwindcss-ls": {
        "command": ["tailwindcss-language-server", "--stdio"],
    },
    "taplo": {
        "command": ["taplo", "lsp", "stdio"],
    },
    "templ": {
        "command": ["templ", "lsp"],
    },
    "terraform-ls": {
        "command": ["terraform-ls", "serve"],
    },
    "texlab": {
        "command": ["texlab"],
    },
    "tilt": {
        "command": ["tilt", "lsp", "start"],
    },
    "tombi": {
        "command": ["tombi", "lsp"],
    },
    "ty": {
        "command": ["ty", "server"],
    },
    "typespec": {
        "command": ["tsp-server", "--stdio"],
    },
    "vala-language-server": {
        "command": ["vala-language-server"],
    },
    "vale-ls": {
        "command": ["vale-ls"],
    },
    "verible-verilog-ls": {
        "command": ["verible-verilog-ls"],
    },
    "vhdl_ls": {
        "command": ["vhdl_ls"],
    },
    "vlang-language-server": {
        "command": ["v-analyzer"],
    },
    "vscode-css-language-server": {
        "command": ["vscode-css-language-server", "--stdio"],
        "settings": {
            "provideFormatter": True,
            "css": {
                "validate": {
                    "enable": True,
                },
            },
        },
    },
    "vscode-html-language-server": {
        "command": ["vscode-html-language-server", "--stdio"],
        "settings": {
            "provideFormatter": True,
        },
    },
    "vscode-json-language-server": {
        "command": ["vscode-json-language-server", "--stdio"],
        "settings": {
            "provideFormatter": True,
            "json": {
                "validate": {
                    "enable": True,
                },
            },
        },
    },
    "vuels": {
        "command": ["vue-language-server", "--stdio"],
        "settings": {
            "typescript": {
                "tsdk": "node_modules/typescript/lib/",
            },
        },
    },
    "wgsl-analyzer": {
        "command": ["wgsl-analyzer"],
    },
    "wikitext-lsp": {
        "command": ["wikitext-lsp", "--stdio"],
    },
    "yaml-language-server": {
        "command": ["yaml-language-server", "--stdio"],
    },
    "yls": {
        "command": ["yls", "-vv"],
    },
    "zls": {
        "command": ["zls"],
    },
    "blueprint-compiler": {
        "command": ["blueprint-compiler", "lsp"],
    },
    "tinymist": {
        "command": ["tinymist"],
    },
    "ts_query_ls": {
        "command": ["ts_query_ls"],
    },
    "termux-language-server": {
        "command": ["termux-language-server"],
    },
    "helm_ls": {
        "command": ["helm_ls", "serve"],
    },
    "ember-language-server": {
        "command": ["ember-language-server", "--stdio"],
    },
    "teal-language-server": {
        "command": ["teal-language-server"],
    },
    "wasm-language-tools": {
        "command": ["wat_server"],
    },
    "sourcepawn-studio": {
        "command": ["sourcepawn-studio"],
    },
    "luau": {
        "command": ["luau-lsp", "lsp"],
    },
    "zizmor": {
        "command": ["zizmor", "--lsp"],
    },
    "actions-language-server": {
        "command": ["actions-languageserver", "--stdio"],
        "settings": {
            "actions-language-server": {
                "sessionToken": "",
            },
        },
    },
    "ansible-language-server": {
        "command": ["ansible-language-server", "--stdio"],
    },
    "astro-ls": {
        "command": ["astro-ls", "--stdio"],
        "settings": {
            "typescript": {
                "tsdk": "node_modules/typescript/lib",
            },
        },
    },
    "lua-language-server": {
        "command": ["lua-language-server"],
        "settings": {
            "Lua": {
                "hint": {
                    "enable": True,
                    "arrayIndex": "Enable",
                    "setType": True,
                    "paramName": "All",
                    "paramType": True,
                    "await": True,
                },
            },
        },
    },
    "gopls": {
        "command": ["gopls"],
        "settings": {
            "hints": {
                "assignVariableTypes": True,
                "compositeLiteralFields": True,
                "constantValues": True,
                "functionTypeParameters": True,
                "parameterNames": True,
                "rangeVariableTypes": True,
            },
        },
    },
    "golangci-lint-lsp": {
        "command": ["golangci-lint-langserver"],
        "settings": {
            "command": [
                "golangci-lint",
                "run",
                "--output.json.path=stdout",
                "--show-stats=false",
                "--issues-exit-code=1",
            ],
        },
    },
    "rust-analyzer": {
        "command": ["rust-analyzer"],
        "settings": {
            "inlayHints": {
                "bindingModeHints": {
                    "enable": False,
                },
                "closingBraceHints": {
                    "minLines": 10,
                },
                "closureReturnTypeHints": {
                    "enable": "with_block",
                },
                "discriminantHints": {
                    "enable": "fieldless",
                },
                "lifetimeElisionHints": {
                    "enable": "skip_trivial",
                },
                "typeHints": {
                    "hideClosureInitialization": False,
                },
            },
            "files": {
                "watcher": "server",
            },
        },
    },
    "typescript-language-server": {
        "command": ["typescript-language-server", "--stdio"],
        "settings": {
            "hostInfo": "euporie",
            "typescript": {
                "inlayHints": {
                    "includeInlayEnumMemberValueHints": True,
                    "includeInlayFunctionLikeReturnTypeHints": True,
                    "includeInlayFunctionParameterTypeHints": True,
                    "includeInlayParameterNameHints": "all",
                    "includeInlayParameterNameHintsWhenArgumentMatchesName": True,
                    "includeInlayPropertyDeclarationTypeHints": True,
                    "includeInlayVariableTypeHints": True,
                },
            },
            "javascript": {
                "inlayHints": {
                    "includeInlayEnumMemberValueHints": True,
                    "includeInlayFunctionLikeReturnTypeHints": True,
                    "includeInlayFunctionParameterTypeHints": True,
                    "includeInlayParameterNameHints": "all",
                    "includeInlayParameterNameHintsWhenArgumentMatchesName": True,
                    "includeInlayPropertyDeclarationTypeHints": True,
                    "includeInlayVariableTypeHints": True,
                },
            },
        },
    },
    "svelteserver": {
        "command": ["svelteserver", "--stdio"],
        "settings": {
            "configuration": {
                "typescript": {
                    "inlayHints": {
                        "parameterTypes": {
                            "enabled": True,
                        },
                        "variableTypes": {
                            "enabled": True,
                        },
                        "propertyDeclarationTypes": {
                            "enabled": True,
                        },
                        "functionLikeReturnTypes": {
                            "enabled": True,
                        },
                        "enumMemberValues": {
                            "enabled": True,
                        },
                        "parameterNames": {
                            "enabled": "all",
                        },
                    },
                },
                "javascript": {
                    "inlayHints": {
                        "parameterTypes": {
                            "enabled": True,
                        },
                        "variableTypes": {
                            "enabled": True,
                        },
                        "propertyDeclarationTypes": {
                            "enabled": True,
                        },
                        "functionLikeReturnTypes": {
                            "enabled": True,
                        },
                        "enumMemberValues": {
                            "enabled": True,
                        },
                        "parameterNames": {
                            "enabled": "all",
                        },
                    },
                },
            },
        },
    },
    "vscode-eslint-language-server": {
        "command": ["vscode-eslint-language-server", "--stdio"],
        "settings": {
            "validate": "on",
            "experimental": {
                "useFlatConfig": False,
            },
            "rulesCustomizations": [],
            "run": "onType",
            "problems": {
                "shortenToSingleLine": False,
            },
            "nodePath": "",
            "codeAction": {
                "disableRuleComment": {
                    "enable": True,
                    "location": "separateLine",
                },
                "showDocumentation": {
                    "enable": True,
                },
            },
            "workingDirectory": {
                "mode": "location",
            },
        },
    },
    "clarinet": {
        "command": ["clarinet", "lsp"],
    },
    "docker-language-server": {
        "command": ["docker-language-server", "start", "--stdio"],
    },
    "kcl-lsp": {
        "command": ["kcl-language-server", "server", "--stdio"],
    },
    "drools-lsp": {
        "command": ["drools-lsp"],
    },
}

KNOWN_FORMATTERS: dict[str, dict[str, Any]] = {
    "txtpbfmt": {
        "command": ["txtpbfmt"],
    },
    "fnlfmt": {
        "command": ["fnlfmt", "-"],
    },
    "fish_indent": {
        "command": ["fish_indent"],
    },
    "pixi": {
        "command": ["pixi", "run", "mojo", "format", "-q", "-"],
    },
    "janet-format": {
        "command": ["janet-format"],
    },
    "crystal": {
        "command": ["crystal", "tool", "format", "-"],
    },
    "nixfmt": {
        "command": ["nixfmt"],
    },
    "bibtex-tidy": {
        "command": [
            "bibtex-tidy",
            "-",
            "--curly",
            "--drop-all-caps",
            "--remove-empty-fields",
            "--sort-fields",
            "--sort=year,author,id",
            "--strip-enclosing-braces",
            "--trailing-commas",
        ],
    },
    "dune": {
        "command": ["dune", "format-dune-file"],
    },
    "yamlfmt": {
        "command": ["yamlfmt", "-"],
    },
    "purs-tidy": {
        "command": ["purs-tidy", "format"],
    },
    "zig": {
        "command": ["zig", "fmt", "--stdin"],
    },
    "dockerfmt": {
        "command": ["dockerfmt"],
    },
    "swift-format": {
        "command": ["swift-format"],
    },
    "gdformat": {
        "command": ["gdformat", "-"],
    },
    "nufmt": {
        "command": ["nufmt", "--stdin"],
    },
    "odinfmt": {
        "command": ["odinfmt", "-stdin"],
    },
    "cue": {
        "command": ["cue", "fmt", "-"],
    },
    "dfmt": {
        "command": ["dfmt"],
    },
    "kdlfmt": {
        "command": ["kdlfmt", "format", "-"],
    },
    "inko": {
        "command": ["inko", "fmt", "-"],
    },
    "dhall": {
        "command": ["dhall", "format"],
    },
    "hurlfmt": {
        "command": ["hurlfmt"],
    },
    "gn": {
        "command": ["gn", "format", "--stdin"],
    },
    "sort": {
        "command": ["sort"],
    },
    "prettier": {
        "command": ["prettier", "--parser", "glimmer"],
    },
    "snakefmt": {
        "command": ["snakefmt", "-"],
    },
    "koto": {
        "command": ["koto", "--format"],
    },
    "tlafmt": {
        "command": ["tlafmt", "--stdin"],
    },
    "caddy": {
        "command": ["caddy", "fmt", "-"],
    },
    "zoo": {
        "command": ["zoo", "kcl", "fmt", "-"],
    },
    "buildifier": {
        "command": ["buildifier"],
    },
    "drools-fmt": {
        "command": ["drools-fmt"],
    },
}
