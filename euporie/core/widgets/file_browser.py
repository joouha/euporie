"""Define a file browser widget."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.key_binding.key_bindings import KeyBindings, KeyBindingsBase
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
)
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.screen import WritePosition
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import Event

from euporie.core.app.current import get_app
from euporie.core.border import InsetGrid
from euporie.core.data_structures import DiBool
from euporie.core.ft.utils import pad
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.layout.decor import FocusedStyle
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.widgets.decor import Border
from euporie.core.widgets.forms import Button, Text

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.filters.base import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from upath.core import PT

    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)

FILE_ICONS = {
    ".3gp": ("fg:ansiyellow", ""),
    ".3mf": ("fg:ansibrightblack", "󰆧"),
    ".7z": ("fg:ansiyellow", ""),
    ".DS_Store": ("", ""),
    ".Dockerfile": ("fg:ansicyan", "󰡨"),
    ".R": ("fg:ansiblue", "󰟔"),
    ".SRCINFO": ("fg:ansicyan", "󰣇"),
    ".Xauthority": ("fg:ansired", ""),
    ".Xresources": ("fg:ansired", ""),
    ".a": ("fg:ansigray", ""),
    ".aac": ("fg:ansicyan", ""),
    ".ace": ("", ""),
    ".ada": ("fg:ansicyan", ""),
    ".adb": ("fg:ansicyan", ""),
    ".ads": ("fg:ansibrightblack", ""),
    ".ai": ("fg:ansiyellow", ""),
    ".aif": ("fg:ansicyan", ""),
    ".aiff": ("fg:ansicyan", ""),
    ".alz": ("", ""),
    ".android": ("fg:ansibrightblack", ""),
    ".ape": ("fg:ansicyan", ""),
    ".apk": ("fg:ansibrightblack", ""),
    ".apl": ("fg:ansigreen", ""),
    ".app": ("fg:ansired", ""),
    ".applescript": ("fg:ansibrightblack", ""),
    ".arc": ("", ""),
    ".arj": ("", ""),
    ".asc": ("fg:ansibrightblack", "󰦝"),
    ".asf": ("", ""),
    ".asm": ("fg:ansicyan", ""),
    ".ass": ("fg:ansiyellow", "󰨖"),
    ".astro": ("fg:ansibrightblack", ""),
    ".au": ("", ""),
    ".avi": ("", ""),
    ".avif": ("fg:ansibrightblack", ""),
    ".awk": ("fg:ansibrightblack", ""),
    ".azcli": ("fg:ansicyan", ""),
    ".babelrc": ("fg:ansiyellow", ""),
    ".bak": ("fg:ansibrightblack", "󰁯"),
    ".bash": ("fg:ansiyellow", ""),
    ".bash_profile": ("fg:ansiyellow", ""),
    ".bashprofile": ("", ""),
    ".bashrc": ("fg:ansiyellow", ""),
    ".bat": ("fg:ansiyellow", ""),
    ".bazel": ("fg:ansiyellow", ""),
    ".bib": ("fg:ansiyellow", "󱉟"),
    ".bicep": ("fg:ansibrightblack", ""),
    ".bicepparam": ("fg:ansibrightblack", ""),
    ".bin": ("fg:ansired", ""),
    ".blade.php": ("fg:ansibrightred", ""),
    ".blend": ("fg:ansiyellow", "󰂫"),
    ".blp": ("fg:ansicyan", "󰺾"),
    ".bmp": ("fg:ansibrightblack", ""),
    ".bqn": ("fg:ansigreen", ""),
    ".brep": ("fg:ansibrightblack", "󰻫"),
    ".bz": ("fg:ansiyellow", ""),
    ".bz2": ("fg:ansiyellow", ""),
    ".bz3": ("fg:ansiyellow", ""),
    ".bzl": ("fg:ansiyellow", ""),
    ".c": ("fg:ansicyan", ""),
    ".c++": ("fg:ansimagenta", ""),
    ".cab": ("", ""),
    ".cache": ("fg:ansiwhite", ""),
    ".cast": ("fg:ansiyellow", ""),
    ".cbl": ("fg:ansiblue", ""),
    ".cc": ("fg:ansimagenta", ""),
    ".ccm": ("fg:ansimagenta", ""),
    ".cfg": ("fg:ansibrightblack", ""),
    ".cgm": ("", ""),
    ".cjs": ("fg:ansiyellow", ""),
    ".clang-format": ("fg:ansibrightblack", ""),
    ".clang-tidy": ("fg:ansibrightblack", ""),
    ".clj": ("fg:ansibrightblack", ""),
    ".cljc": ("fg:ansibrightblack", ""),
    ".cljd": ("fg:ansibrightblack", ""),
    ".cljs": ("fg:ansibrightblack", ""),
    ".cmake": ("fg:ansigray", ""),
    ".cob": ("fg:ansiblue", ""),
    ".cobol": ("fg:ansiblue", ""),
    ".codespellrc": ("fg:ansigreen", "󰓆"),
    ".coffee": ("fg:ansiyellow", ""),
    ".conda": ("fg:ansigreen", ""),
    ".condarc": ("fg:ansigreen", ""),
    ".conf": ("fg:ansibrightblack", ""),
    ".config.ru": ("fg:ansired", ""),
    ".cow": ("fg:ansibrightblack", "󰆚"),
    ".cp": ("fg:ansibrightblack", ""),
    ".cpio": ("", ""),
    ".cpp": ("fg:ansibrightblack", ""),
    ".cppm": ("fg:ansibrightblack", ""),
    ".cpy": ("fg:ansiblue", ""),
    ".cr": ("fg:ansigray", ""),
    ".crdownload": ("fg:ansicyan", ""),
    ".cs": ("fg:ansibrightblack", "󰌛"),
    ".csh": ("fg:ansibrightblack", ""),
    ".cshtml": ("fg:ansiblue", "󱦗"),
    ".cson": ("fg:ansiyellow", ""),
    ".csproj": ("fg:ansiblue", "󰪮"),
    ".css": ("fg:ansibrightblack", ""),
    ".csv": ("fg:ansiyellow", ""),
    ".cts": ("fg:ansibrightblack", ""),
    ".cu": ("fg:ansiyellow", ""),
    ".cue": ("fg:ansigray", "󰲹"),
    ".cuh": ("fg:ansibrightblack", ""),
    ".cxx": ("fg:ansibrightblack", ""),
    ".cxxm": ("fg:ansibrightblack", ""),
    ".d": ("fg:ansired", ""),
    ".d.ts": ("fg:ansibrightblack", ""),
    ".dart": ("fg:ansiblue", ""),
    ".db": ("fg:ansigray", ""),
    ".dconf": ("fg:ansiwhite", ""),
    ".deb": ("", ""),
    ".desktop": ("fg:ansibrightblack", ""),
    ".diff": ("fg:ansibrightblack", ""),
    ".dl": ("", ""),
    ".dll": ("fg:ansired", ""),
    ".doc": ("fg:ansiblue", "󰈬"),
    ".dockerignore": ("fg:ansicyan", "󰡨"),
    ".docx": ("fg:ansiblue", "󰈬"),
    ".dot": ("fg:ansibrightblack", "󱁉"),
    ".download": ("fg:ansicyan", ""),
    ".drl": ("fg:ansigray", ""),
    ".dropbox": ("fg:ansibrightblue", ""),
    ".ds_store": ("fg:ansibrightblack", ""),
    ".dump": ("fg:ansigray", ""),
    ".dwg": ("fg:ansibrightblack", "󰻫"),
    ".dwm": ("", ""),
    ".dxf": ("fg:ansibrightblack", "󰻫"),
    ".dz": ("", ""),
    ".ear": ("", ""),
    ".ebook": ("fg:ansiyellow", ""),
    ".ebuild": ("fg:ansibrightblack", ""),
    ".editorconfig": ("fg:ansiwhite", ""),
    ".edn": ("fg:ansibrightblack", ""),
    ".eex": ("fg:ansibrightblack", ""),
    ".ejs": ("fg:ansiyellow", ""),
    ".el": ("fg:ansibrightblack", ""),
    ".elc": ("fg:ansibrightblack", ""),
    ".elf": ("fg:ansired", ""),
    ".elm": ("fg:ansibrightblack", ""),
    ".eln": ("fg:ansibrightblack", ""),
    ".emf": ("", ""),
    ".env": ("fg:ansibrightyellow", ""),
    ".eot": ("fg:ansigray", ""),
    ".epp": ("fg:ansiyellow", ""),
    ".epub": ("fg:ansiyellow", ""),
    ".erb": ("fg:ansired", ""),
    ".erl": ("fg:ansimagenta", ""),
    ".esd": ("", ""),
    ".eslintignore": ("fg:ansiblue", ""),
    ".eslintrc": ("fg:ansiblue", ""),
    ".ex": ("fg:ansibrightblack", ""),
    ".exe": ("fg:ansired", ""),
    ".exs": ("fg:ansibrightblack", ""),
    ".f#": ("fg:ansibrightblack", ""),
    ".f3d": ("fg:ansibrightblack", "󰻫"),
    ".f90": ("fg:ansibrightblack", "󱈚"),
    ".fbx": ("fg:ansibrightblack", "󰆧"),
    ".fcbak": ("fg:ansired", ""),
    ".fcmacro": ("fg:ansired", ""),
    ".fcmat": ("fg:ansired", ""),
    ".fcparam": ("fg:ansired", ""),
    ".fcscript": ("fg:ansired", ""),
    ".fcstd": ("fg:ansired", ""),
    ".fcstd1": ("fg:ansired", ""),
    ".fctb": ("fg:ansired", ""),
    ".fctl": ("fg:ansired", ""),
    ".fdmdownload": ("fg:ansicyan", ""),
    ".feature": ("fg:ansigreen", ""),
    ".fish": ("fg:ansibrightblack", ""),
    ".flac": ("fg:ansicyan", ""),
    ".flc": ("fg:ansigray", ""),
    ".flf": ("fg:ansigray", ""),
    ".fli": ("", ""),
    ".flv": ("", ""),
    ".fnl": ("fg:ansigray", ""),
    ".fodg": ("fg:ansibrightyellow", ""),
    ".fodp": ("fg:ansiyellow", ""),
    ".fods": ("fg:ansiyellow", ""),
    ".fodt": ("fg:ansicyan", ""),
    ".fs": ("fg:ansibrightblack", ""),
    ".fsi": ("fg:ansibrightblack", ""),
    ".fsscript": ("fg:ansibrightblack", ""),
    ".fsx": ("fg:ansibrightblack", ""),
    ".gcode": ("fg:ansicyan", "󰐫"),
    ".gd": ("fg:ansibrightblack", ""),
    ".gemspec": ("fg:ansired", ""),
    ".gif": ("fg:ansibrightblack", ""),
    ".git": ("fg:ansibrightred", ""),
    ".git-blame-ignore-revs": ("fg:ansibrightred", ""),
    ".gitattributes": ("fg:ansibrightred", ""),
    ".gitconfig": ("fg:ansibrightred", ""),
    ".gitignore": ("fg:ansibrightred", ""),
    ".gitlab-ci.yml": ("fg:ansired", ""),
    ".gitmodules": ("fg:ansibrightred", ""),
    ".gl": ("", ""),
    ".glb": ("fg:ansiyellow", ""),
    ".gleam": ("fg:ansigray", ""),
    ".gnumakefile": ("fg:ansibrightblack", ""),
    ".go": ("fg:ansicyan", ""),
    ".godot": ("fg:ansibrightblack", ""),
    ".gpr": ("fg:ansibrightblack", ""),
    ".gql": ("fg:ansimagenta", ""),
    ".gradle": ("fg:ansiblue", ""),
    ".graphql": ("fg:ansimagenta", ""),
    ".gresource": ("fg:ansiwhite", ""),
    ".gtkrc-2.0": ("fg:ansiwhite", ""),
    ".gv": ("fg:ansibrightblack", "󱁉"),
    ".gvimrc": ("fg:ansigreen", ""),
    ".gz": ("fg:ansiyellow", ""),
    ".h": ("fg:ansibrightblack", ""),
    ".haml": ("fg:ansigray", ""),
    ".hbs": ("fg:ansiyellow", ""),
    ".heex": ("fg:ansibrightblack", ""),
    ".hex": ("fg:ansibrightblue", ""),
    ".hh": ("fg:ansibrightblack", ""),
    ".hpp": ("fg:ansibrightblack", ""),
    ".hrl": ("fg:ansimagenta", ""),
    ".hs": ("fg:ansibrightblack", ""),
    ".htm": ("fg:ansired", ""),
    ".html": ("fg:ansired", ""),
    ".http": ("fg:ansicyan", ""),
    ".huff": ("fg:ansiblue", "󰡘"),
    ".hurl": ("fg:ansimagenta", ""),
    ".hx": ("fg:ansiyellow", ""),
    ".hxx": ("fg:ansibrightblack", ""),
    ".ical": ("fg:ansiblue", ""),
    ".icalendar": ("fg:ansiblue", ""),
    ".ico": ("fg:ansiyellow", ""),
    ".ics": ("fg:ansiblue", ""),
    ".ifb": ("fg:ansiblue", ""),
    ".ifc": ("fg:ansibrightblack", "󰻫"),
    ".ige": ("fg:ansibrightblack", "󰻫"),
    ".iges": ("fg:ansibrightblack", "󰻫"),
    ".igs": ("fg:ansibrightblack", "󰻫"),
    ".image": ("fg:ansigray", ""),
    ".img": ("fg:ansigray", ""),
    ".import": ("fg:ansigray", ""),
    ".info": ("fg:ansigray", ""),
    ".ini": ("fg:ansibrightblack", ""),
    ".ino": ("fg:ansicyan", ""),
    ".ipynb": ("fg:orange", ""),
    ".iso": ("fg:ansigray", ""),
    ".ixx": ("fg:ansibrightblack", ""),
    ".jar": ("", ""),
    ".java": ("fg:ansired", ""),
    ".jl": ("fg:ansibrightblack", ""),
    ".jpeg": ("fg:ansibrightblack", ""),
    ".jpg": ("fg:ansibrightblack", ""),
    ".js": ("fg:ansiyellow", ""),
    ".json": ("fg:ansiyellow", ""),
    ".json5": ("fg:ansiyellow", ""),
    ".jsonc": ("fg:ansiyellow", ""),
    ".jsx": ("fg:ansicyan", ""),
    ".justfile": ("fg:ansibrightblack", ""),
    ".jwmrc": ("fg:ansicyan", ""),
    ".jxl": ("fg:ansibrightblack", ""),
    ".kbx": ("fg:ansibrightblack", "󰯄"),
    ".kdb": ("fg:ansibrightblack", ""),
    ".kdbx": ("fg:ansibrightblack", ""),
    ".kdenlive": ("fg:ansigray", ""),
    ".kdenlivetitle": ("fg:ansigray", ""),
    ".kicad_dru": ("fg:ansiwhite", ""),
    ".kicad_mod": ("fg:ansiwhite", ""),
    ".kicad_pcb": ("fg:ansiwhite", ""),
    ".kicad_prl": ("fg:ansiwhite", ""),
    ".kicad_pro": ("fg:ansiwhite", ""),
    ".kicad_sch": ("fg:ansiwhite", ""),
    ".kicad_sym": ("fg:ansiwhite", ""),
    ".kicad_wks": ("fg:ansiwhite", ""),
    ".ko": ("fg:ansigray", ""),
    ".kpp": ("fg:ansibrightmagenta", ""),
    ".kra": ("fg:ansibrightmagenta", ""),
    ".krz": ("fg:ansibrightmagenta", ""),
    ".ksh": ("fg:ansibrightblack", ""),
    ".kt": ("fg:ansimagenta", ""),
    ".kts": ("fg:ansimagenta", ""),
    ".lck": ("fg:ansigray", ""),
    ".leex": ("fg:ansibrightblack", ""),
    ".less": ("fg:ansibrightblack", ""),
    ".lff": ("fg:ansigray", ""),
    ".lha": ("", ""),
    ".lhs": ("fg:ansibrightblack", ""),
    ".lib": ("fg:ansired", ""),
    ".license": ("fg:ansiyellow", ""),
    ".liquid": ("fg:ansibrightblack", ""),
    ".lock": ("fg:ansigray", ""),
    ".log": ("fg:ansigray", "󰌱"),
    ".lrc": ("fg:ansiyellow", "󰨖"),
    ".lrz": ("", ""),
    ".lua": ("fg:ansicyan", ""),
    ".luac": ("fg:ansicyan", ""),
    ".luacheckrc": ("fg:ansicyan", ""),
    ".luau": ("fg:ansicyan", ""),
    ".luaurc": ("fg:ansicyan", ""),
    ".lz": ("", ""),
    ".lz4": ("", ""),
    ".lzh": ("", ""),
    ".lzma": ("", ""),
    ".lzo": ("", ""),
    ".m": ("fg:ansicyan", ""),
    ".m2v": ("", ""),
    ".m3u": ("fg:ansigray", "󰲹"),
    ".m3u8": ("fg:ansigray", "󰲹"),
    ".m4a": ("fg:ansicyan", ""),
    ".m4v": ("fg:ansiyellow", ""),
    ".magnet": ("fg:ansired", ""),
    ".mailmap": ("fg:ansibrightred", "󰊢"),
    ".makefile": ("fg:ansibrightblack", ""),
    ".markdown": ("fg:ansigray", ""),
    ".material": ("fg:ansimagenta", ""),
    ".md": ("fg:ansigray", ""),
    ".md5": ("fg:ansibrightblack", "󰕥"),
    ".mdx": ("fg:ansibrightblack", ""),
    ".mid": ("", ""),
    ".midi": ("", ""),
    ".mint": ("fg:ansibrightblack", "󰌪"),
    ".mjpeg": ("", ""),
    ".mjpg": ("", ""),
    ".mjs": ("fg:ansibrightyellow", ""),
    ".mk": ("fg:ansibrightblack", ""),
    ".mka": ("", ""),
    ".mkv": ("fg:ansiyellow", ""),
    ".ml": ("fg:ansiyellow", ""),
    ".mli": ("fg:ansiyellow", ""),
    ".mm": ("fg:ansibrightblack", ""),
    ".mng": ("", ""),
    ".mo": ("fg:ansibrightblack", ""),
    ".mobi": ("fg:ansiyellow", ""),
    ".mojo": ("fg:ansibrightred", ""),
    ".mov": ("fg:ansiyellow", ""),
    ".mp3": ("fg:ansicyan", ""),
    ".mp4": ("fg:ansiyellow", ""),
    ".mp4v": ("", ""),
    ".mpc": ("", ""),
    ".mpeg": ("", ""),
    ".mpg": ("", ""),
    ".mpp": ("fg:ansibrightblack", ""),
    ".msf": ("fg:ansicyan", ""),
    ".mts": ("fg:ansibrightblack", ""),
    ".mustache": ("fg:ansiyellow", ""),
    ".nanorc": ("fg:ansiblue", ""),
    ".nfo": ("fg:ansigray", ""),
    ".nim": ("fg:ansiyellow", ""),
    ".nix": ("fg:ansigray", ""),
    ".norg": ("fg:ansibrightblack", ""),
    ".npmignore": ("fg:ansibrightred", ""),
    ".npmrc": ("fg:ansibrightred", ""),
    ".nswag": ("fg:ansiyellow", ""),
    ".nu": ("fg:ansibrightblack", ""),
    ".nuv": ("", ""),
    ".nuxtrc": ("fg:ansicyan", "󱄆"),
    ".nvmrc": ("fg:ansibrightblack", ""),
    ".o": ("fg:ansired", ""),
    ".obj": ("fg:ansibrightblack", "󰆧"),
    ".odf": ("fg:ansimagenta", ""),
    ".odg": ("fg:ansibrightyellow", ""),
    ".odin": ("fg:ansicyan", "󰟢"),
    ".odp": ("fg:ansiyellow", ""),
    ".ods": ("fg:ansiyellow", ""),
    ".odt": ("fg:ansicyan", ""),
    ".oga": ("fg:ansicyan", ""),
    ".ogg": ("fg:ansicyan", ""),
    ".ogm": ("", ""),
    ".ogv": ("fg:ansiyellow", ""),
    ".ogx": ("fg:ansiyellow", ""),
    ".opus": ("fg:ansicyan", ""),
    ".org": ("fg:ansibrightblack", ""),
    ".otf": ("fg:ansigray", ""),
    ".out": ("fg:ansired", ""),
    ".part": ("fg:ansicyan", ""),
    ".patch": ("fg:ansibrightblack", ""),
    ".pbm": ("", ""),
    ".pck": ("fg:ansibrightblack", ""),
    ".pcm": ("fg:ansicyan", ""),
    ".pcx": ("", ""),
    ".pdf": ("fg:ansired", ""),
    ".pem": ("", ""),
    ".pgm": ("", ""),
    ".php": ("fg:ansibrightblack", ""),
    ".pl": ("fg:ansibrightblack", ""),
    ".pls": ("fg:ansigray", "󰲹"),
    ".ply": ("fg:ansibrightblack", "󰆧"),
    ".pm": ("fg:ansibrightblack", ""),
    ".png": ("fg:ansibrightblack", ""),
    ".po": ("fg:ansicyan", ""),
    ".pot": ("fg:ansicyan", ""),
    ".pp": ("fg:ansiyellow", ""),
    ".ppm": ("fg:ansiyellow", ""),
    ".ppt": ("fg:ansired", "󰈧"),
    ".pptx": ("fg:ansired", "󰈧"),
    ".pre-commit-config.yaml": ("fg:ansiyellow", "󰛢"),
    ".prettierignore": ("fg:ansicyan", ""),
    ".prettierrc": ("fg:ansicyan", ""),
    ".prettierrc.cjs": ("fg:ansicyan", ""),
    ".prettierrc.js": ("fg:ansicyan", ""),
    ".prettierrc.json": ("fg:ansicyan", ""),
    ".prettierrc.json5": ("fg:ansicyan", ""),
    ".prettierrc.mjs": ("fg:ansicyan", ""),
    ".prettierrc.toml": ("fg:ansicyan", ""),
    ".prettierrc.yaml": ("fg:ansicyan", ""),
    ".prettierrc.yml": ("fg:ansicyan", ""),
    ".prisma": ("fg:ansibrightblack", ""),
    ".pro": ("fg:ansiyellow", ""),
    ".ps1": ("fg:ansibrightblack", "󰨊"),
    ".psb": ("fg:ansibrightblack", ""),
    ".psd": ("fg:ansibrightblack", ""),
    ".psd1": ("fg:ansibrightblack", "󰨊"),
    ".psm1": ("fg:ansibrightblack", "󰨊"),
    ".pub": ("fg:ansigray", "󰷖"),
    ".pxd": ("fg:ansicyan", ""),
    ".pxi": ("fg:ansicyan", ""),
    ".py": ("fg:ansiyellow", ""),
    ".pyc": ("fg:ansigray", ""),
    ".pyd": ("fg:ansigray", ""),
    ".pyi": ("fg:ansiyellow", ""),
    ".pylintrc": ("fg:ansibrightblack", ""),
    ".pyo": ("fg:ansigray", ""),
    ".pyw": ("fg:ansicyan", ""),
    ".pyx": ("fg:ansicyan", ""),
    ".qm": ("fg:ansicyan", ""),
    ".qml": ("fg:ansigreen", ""),
    ".qrc": ("fg:ansigreen", ""),
    ".qss": ("fg:ansigreen", ""),
    ".qt": ("", ""),
    ".query": ("fg:ansibrightblack", ""),
    ".r": ("fg:ansiblue", "󰟔"),
    ".ra": ("", ""),
    ".rake": ("fg:ansired", ""),
    ".rar": ("fg:ansiyellow", ""),
    ".razor": ("fg:ansiblue", "󱦘"),
    ".rb": ("fg:ansired", ""),
    ".res": ("fg:ansired", ""),
    ".resi": ("fg:ansimagenta", ""),
    ".rlib": ("fg:ansibrightblack", ""),
    ".rm": ("", ""),
    ".rmd": ("fg:ansibrightblack", ""),
    ".rmvb": ("", ""),
    ".rpm": ("", ""),
    ".rproj": ("fg:ansibrightblack", "󰗆"),
    ".rs": ("fg:ansibrightblack", ""),
    ".rss": ("fg:ansiyellow", ""),
    ".rz": ("", ""),
    ".s": ("fg:ansicyan", ""),
    ".sar": ("", ""),
    ".sass": ("fg:ansimagenta", ""),
    ".sbt": ("fg:ansired", ""),
    ".sc": ("fg:ansired", ""),
    ".scad": ("fg:ansibrightyellow", ""),
    ".scala": ("fg:ansired", ""),
    ".scm": ("fg:ansigray", "󰘧"),
    ".scss": ("fg:ansimagenta", ""),
    ".settings.json": ("fg:ansibrightblack", ""),
    ".sh": ("fg:ansibrightblack", ""),
    ".sha1": ("fg:ansibrightblack", "󰕥"),
    ".sha224": ("fg:ansibrightblack", "󰕥"),
    ".sha256": ("fg:ansibrightblack", "󰕥"),
    ".sha384": ("fg:ansibrightblack", "󰕥"),
    ".sha512": ("fg:ansibrightblack", "󰕥"),
    ".sig": ("fg:ansiyellow", "󰘧"),
    ".signature": ("fg:ansiyellow", "󰘧"),
    ".skp": ("fg:ansibrightblack", "󰻫"),
    ".sldasm": ("fg:ansibrightblack", "󰻫"),
    ".sldprt": ("fg:ansibrightblack", "󰻫"),
    ".slim": ("fg:ansired", ""),
    ".sln": ("fg:ansibrightblack", ""),
    ".slnx": ("fg:ansibrightblack", ""),
    ".slvs": ("fg:ansibrightblack", "󰻫"),
    ".sml": ("fg:ansiyellow", "󰘧"),
    ".so": ("fg:ansigray", ""),
    ".sol": ("fg:ansibrightblack", ""),
    ".spec.js": ("fg:ansiyellow", ""),
    ".spec.jsx": ("fg:ansicyan", ""),
    ".spec.ts": ("fg:ansibrightblack", ""),
    ".spec.tsx": ("fg:ansiblue", ""),
    ".spx": ("fg:ansicyan", ""),
    ".sql": ("fg:ansigray", ""),
    ".sqlite": ("fg:ansigray", ""),
    ".sqlite3": ("fg:ansigray", ""),
    ".srt": ("fg:ansiyellow", "󰨖"),
    ".ssa": ("fg:ansiyellow", "󰨖"),
    ".ste": ("fg:ansibrightblack", "󰻫"),
    ".step": ("fg:ansibrightblack", "󰻫"),
    ".stl": ("fg:ansibrightblack", "󰆧"),
    ".stories.js": ("fg:ansimagenta", ""),
    ".stories.jsx": ("fg:ansimagenta", ""),
    ".stories.mjs": ("fg:ansimagenta", ""),
    ".stories.svelte": ("fg:ansimagenta", ""),
    ".stories.ts": ("fg:ansimagenta", ""),
    ".stories.tsx": ("fg:ansimagenta", ""),
    ".stories.vue": ("fg:ansimagenta", ""),
    ".stp": ("fg:ansibrightblack", "󰻫"),
    ".strings": ("fg:ansicyan", ""),
    ".styl": ("fg:ansibrightblack", ""),
    ".sub": ("fg:ansiyellow", "󰨖"),
    ".sublime": ("fg:ansiyellow", ""),
    ".suo": ("fg:ansibrightblack", ""),
    ".sv": ("fg:ansigreen", "󰍛"),
    ".svelte": ("fg:ansibrightred", ""),
    ".svg": ("fg:ansiyellow", "󰜡"),
    ".svgz": ("fg:ansiyellow", "󰜡"),
    ".svh": ("fg:ansigreen", "󰍛"),
    ".swift": ("fg:ansiyellow", ""),
    ".swm": ("", ""),
    ".t": ("fg:ansibrightblack", ""),
    ".t7z": ("", ""),
    ".tar": ("", ""),
    ".taz": ("", ""),
    ".tbc": ("fg:ansiblue", "󰛓"),
    ".tbz": ("", ""),
    ".tbz2": ("", ""),
    ".tcl": ("fg:ansiblue", "󰛓"),
    ".templ": ("fg:ansiyellow", ""),
    ".terminal": ("fg:ansigreen", ""),
    ".test.js": ("fg:ansiyellow", ""),
    ".test.jsx": ("fg:ansicyan", ""),
    ".test.ts": ("fg:ansibrightblack", ""),
    ".test.tsx": ("fg:ansiblue", ""),
    ".tex": ("fg:ansigreen", ""),
    ".tf": ("fg:ansibrightblue", ""),
    ".tfvars": ("fg:ansibrightblue", ""),
    ".tga": ("", ""),
    ".tgz": ("fg:ansiyellow", ""),
    ".tif": ("", ""),
    ".tiff": ("", ""),
    ".tlz": ("", ""),
    ".tmpl": ("fg:ansiyellow", ""),
    ".tmux": ("fg:ansigreen", ""),
    ".toml": ("fg:ansired", ""),
    ".torrent": ("fg:ansicyan", ""),
    ".tres": ("fg:ansibrightblack", ""),
    ".ts": ("fg:ansibrightblack", ""),
    ".tscn": ("fg:ansibrightblack", ""),
    ".tsconfig": ("fg:ansiyellow", ""),
    ".tsx": ("fg:ansiblue", ""),
    ".ttf": ("fg:ansigray", ""),
    ".twig": ("fg:ansibrightblack", ""),
    ".txt": ("fg:ansiyellow", "󰈙"),
    ".txz": ("fg:ansiyellow", ""),
    ".typ": ("fg:ansicyan", ""),
    ".typoscript": ("fg:ansiyellow", ""),
    ".tz": ("", ""),
    ".tzo": ("", ""),
    ".tzst": ("", ""),
    ".ui": ("fg:ansibrightblue", ""),
    ".v": ("fg:ansigreen", "󰍛"),
    ".vala": ("fg:ansibrightblack", ""),
    ".vh": ("fg:ansigreen", "󰍛"),
    ".vhd": ("fg:ansigreen", "󰍛"),
    ".vhdl": ("fg:ansigreen", "󰍛"),
    ".vi": ("fg:ansiyellow", ""),
    ".vim": ("fg:ansigreen", ""),
    ".vimrc": ("fg:ansigreen", ""),
    ".vob": ("", ""),
    ".vsh": ("fg:ansibrightblack", ""),
    ".vsix": ("fg:ansibrightblack", ""),
    ".vue": ("fg:ansibrightblack", ""),
    ".war": ("", ""),
    ".wasm": ("fg:ansibrightblack", ""),
    ".wav": ("fg:ansicyan", ""),
    ".webm": ("fg:ansiyellow", ""),
    ".webmanifest": ("fg:ansibrightyellow", ""),
    ".webp": ("fg:ansibrightblack", ""),
    ".webpack": ("fg:ansibrightblack", "󰜫"),
    ".wim": ("", ""),
    ".wma": ("fg:ansicyan", ""),
    ".wmv": ("", ""),
    ".woff": ("fg:ansigray", ""),
    ".woff2": ("fg:ansigray", ""),
    ".wrl": ("fg:ansibrightblack", "󰆧"),
    ".wrz": ("fg:ansibrightblack", "󰆧"),
    ".wv": ("fg:ansicyan", ""),
    ".wvc": ("fg:ansicyan", ""),
    ".x": ("fg:ansicyan", ""),
    ".xaml": ("fg:ansiblue", "󰙳"),
    ".xbm": ("", ""),
    ".xcf": ("fg:ansibrightblack", ""),
    ".xcplayground": ("fg:ansiyellow", ""),
    ".xcstrings": ("fg:ansicyan", ""),
    ".xinitrc": ("fg:ansired", ""),
    ".xls": ("fg:ansibrightblack", "󰈛"),
    ".xlsx": ("fg:ansibrightblack", "󰈛"),
    ".xm": ("fg:ansibrightblack", ""),
    ".xml": ("fg:ansiyellow", "󰗀"),
    ".xpi": ("fg:ansibrightred", ""),
    ".xpm": ("", ""),
    ".xsession": ("fg:ansired", ""),
    ".xspf": ("", ""),
    ".xul": ("fg:ansiyellow", ""),
    ".xwd": ("", ""),
    ".xz": ("fg:ansiyellow", ""),
    ".yaml": ("fg:ansibrightblack", ""),
    ".yml": ("fg:ansibrightblack", ""),
    ".yuv": ("", ""),
    ".z": ("", ""),
    ".zig": ("fg:ansiyellow", ""),
    ".zip": ("fg:ansiyellow", ""),
    ".zoo": ("", ""),
    ".zprofile": ("fg:ansiyellow", ""),
    ".zsh": ("fg:ansiyellow", ""),
    ".zshenv": ("fg:ansiyellow", ""),
    ".zshrc": ("fg:ansiyellow", ""),
    ".zst": ("fg:ansiyellow", ""),
    ".🔥": ("fg:ansibrightred", ""),
    "AUTHORS": ("fg:ansimagenta", ""),
    "AUTHORS.txt": ("fg:ansimagenta", ""),
    "CMakeLists.txt": ("", ""),
    "Directory.Build.props": ("fg:ansicyan", ""),
    "Directory.Build.targets": ("fg:ansicyan", ""),
    "Directory.Packages.props": ("fg:ansicyan", ""),
    "Docker-compose.yml": ("", ""),
    "Dockerfile": ("fg:ansicyan", "󰡨"),
    "Dropbox": ("", ""),
    "FreeCAD.conf": ("fg:ansired", ""),
    "Gemfile": ("fg:ansired", ""),
    "Gruntfile.coffee": ("", ""),
    "Gruntfile.js": ("", ""),
    "Gruntfile.ls": ("", ""),
    "Gulpfile.coffee": ("", ""),
    "Gulpfile.js": ("", ""),
    "Gulpfile.ls": ("", ""),
    "LICENSE": ("", ""),
    "Makefile": ("", ""),
    "PKGBUILD": ("fg:ansicyan", ""),
    "Procfile": ("", ""),
    "PrusaSlicer.ini": ("fg:ansiyellow", ""),
    "PrusaSlicerGcodeViewer.ini": ("fg:ansiyellow", ""),
    "QtProject.conf": ("fg:ansigreen", ""),
    "Rakefile": ("", ""),
    "React.jsx": ("", ""),
    "Vagrantfile": ("", ""),
    "__dir": ("", ""),
    "__file": ("", ""),
    "_gvimrc": ("fg:ansigreen", ""),
    "_vimrc": ("fg:ansigreen", ""),
    "angular.min.js": ("", ""),
    "backbone.min.js": ("", ""),
    "brewfile": ("fg:ansired", ""),
    "bspwmrc": ("fg:ansiblack", ""),
    "build": ("fg:ansiyellow", ""),
    "build.gradle": ("fg:ansiblue", ""),
    "build.zig.zon": ("fg:ansiyellow", ""),
    "bun.lock": ("fg:ansigray", ""),
    "bun.lockb": ("fg:ansigray", ""),
    "cantorrc": ("fg:ansicyan", ""),
    "checkhealth": ("fg:ansigray", "󰓙"),
    "cmakelists.txt": ("fg:ansigray", ""),
    "code_of_conduct": ("fg:ansired", ""),
    "code_of_conduct.md": ("fg:ansired", ""),
    "commit_editmsg": ("fg:ansibrightred", ""),
    "commitlint.config.js": ("fg:ansibrightblack", "󰜘"),
    "commitlint.config.ts": ("fg:ansibrightblack", "󰜘"),
    "compose.yaml": ("fg:ansicyan", "󰡨"),
    "compose.yml": ("fg:ansicyan", "󰡨"),
    "config": ("fg:ansibrightblack", ""),
    "config.ru": ("", ""),
    "containerfile": ("fg:ansicyan", "󰡨"),
    "copying": ("fg:ansiyellow", ""),
    "copying.lesser": ("fg:ansiyellow", ""),
    "docker-compose.yaml": ("fg:ansicyan", "󰡨"),
    "docker-compose.yml": ("fg:ansicyan", "󰡨"),
    "dockerfile": ("fg:ansicyan", "󰡨"),
    "dropbox": ("", ""),
    "eslint.config.cjs": ("fg:ansiblue", ""),
    "eslint.config.js": ("fg:ansiblue", ""),
    "eslint.config.mjs": ("fg:ansiblue", ""),
    "eslint.config.ts": ("fg:ansiblue", ""),
    "ext_typoscript_setup.txt": ("fg:ansiyellow", ""),
    "favicon.ico": ("fg:ansiyellow", ""),
    "fp-info-cache": ("fg:ansiwhite", ""),
    "fp-lib-table": ("fg:ansiwhite", ""),
    "gemfile": ("", ""),
    "gnumakefile": ("fg:ansibrightblack", ""),
    "go.mod": ("fg:ansicyan", ""),
    "go.sum": ("fg:ansicyan", ""),
    "go.work": ("fg:ansicyan", ""),
    "gradle-wrapper.properties": ("fg:ansiblue", ""),
    "gradle.properties": ("fg:ansiblue", ""),
    "gradlew": ("fg:ansiblue", ""),
    "groovy": ("fg:ansibrightblack", ""),
    "gruntfile.babel.js": ("fg:ansiyellow", ""),
    "gruntfile.coffee": ("fg:ansiyellow", ""),
    "gruntfile.js": ("fg:ansiyellow", ""),
    "gruntfile.ls": ("", ""),
    "gruntfile.ts": ("fg:ansiyellow", ""),
    "gtkrc": ("fg:ansiwhite", ""),
    "gulpfile.babel.js": ("fg:ansired", ""),
    "gulpfile.coffee": ("fg:ansired", ""),
    "gulpfile.js": ("fg:ansired", ""),
    "gulpfile.ls": ("", ""),
    "gulpfile.ts": ("fg:ansired", ""),
    "hypridle.conf": ("fg:ansicyan", ""),
    "hyprland.conf": ("fg:ansicyan", ""),
    "hyprlandd.conf": ("fg:ansicyan", ""),
    "hyprlock.conf": ("fg:ansicyan", ""),
    "hyprpaper.conf": ("fg:ansicyan", ""),
    "i18n.config.js": ("fg:ansibrightblack", "󰗊"),
    "i18n.config.ts": ("fg:ansibrightblack", "󰗊"),
    "i3blocks.conf": ("fg:ansigray", ""),
    "i3status.conf": ("fg:ansigray", ""),
    "index.theme": ("fg:ansibrightblack", ""),
    "ionic.config.json": ("fg:ansicyan", ""),
    "jquery.min.js": ("", ""),
    "justfile": ("fg:ansibrightblack", ""),
    "kalgebrarc": ("fg:ansicyan", ""),
    "kdeglobals": ("fg:ansicyan", ""),
    "kdenlive-layoutsrc": ("fg:ansigray", ""),
    "kdenliverc": ("fg:ansigray", ""),
    "kritadisplayrc": ("fg:ansibrightmagenta", ""),
    "kritarc": ("fg:ansibrightmagenta", ""),
    "license": ("fg:ansiyellow", ""),
    "license.md": ("fg:ansiyellow", ""),
    "lxde-rc.xml": ("fg:ansibrightblack", ""),
    "lxqt.conf": ("fg:ansicyan", ""),
    "makefile": ("fg:ansibrightblack", ""),
    "materialize.min.css": ("", ""),
    "materialize.min.js": ("", ""),
    "mix.lock": ("fg:ansibrightblack", ""),
    "mootools.min.js": ("", ""),
    "mpv.conf": ("fg:ansibrightblack", ""),
    "node_modules": ("fg:ansibrightred", ""),
    "nuxt.config.cjs": ("fg:ansicyan", "󱄆"),
    "nuxt.config.js": ("fg:ansicyan", "󱄆"),
    "nuxt.config.mjs": ("fg:ansicyan", "󱄆"),
    "nuxt.config.ts": ("fg:ansicyan", "󱄆"),
    "package-lock.json": ("fg:ansired", ""),
    "package.json": ("fg:ansibrightred", ""),
    "platformio.ini": ("fg:ansiyellow", ""),
    "pom.xml": ("fg:ansired", ""),
    "prettier.config.cjs": ("fg:ansicyan", ""),
    "prettier.config.js": ("fg:ansicyan", ""),
    "prettier.config.mjs": ("fg:ansicyan", ""),
    "prettier.config.ts": ("fg:ansicyan", ""),
    "procfile": ("fg:ansibrightblack", ""),
    "py.typed": ("fg:ansiyellow", ""),
    "rakefile": ("fg:ansired", ""),
    "react.jsx": ("", ""),
    "readme": ("fg:ansigray", "󰂺"),
    "readme.md": ("fg:ansigray", "󰂺"),
    "require.min.js": ("", ""),
    "rmd": ("fg:ansibrightblack", ""),
    "robots.txt": ("fg:ansibrightblack", "󰚩"),
    "security": ("fg:ansigray", "󰒃"),
    "security.md": ("fg:ansigray", "󰒃"),
    "settings.gradle": ("fg:ansiblue", ""),
    "svelte.config.js": ("fg:ansibrightred", ""),
    "sxhkdrc": ("fg:ansiblack", ""),
    "sym-lib-table": ("fg:ansiwhite", ""),
    "tailwind.config.js": ("fg:ansicyan", "󱏿"),
    "tailwind.config.mjs": ("fg:ansicyan", "󱏿"),
    "tailwind.config.ts": ("fg:ansicyan", "󱏿"),
    "tmux.conf": ("fg:ansigreen", ""),
    "tmux.conf.local": ("fg:ansigreen", ""),
    "tsconfig.json": ("fg:ansibrightblack", ""),
    "unlicense": ("fg:ansiyellow", ""),
    "vagrantfile": ("fg:ansibrightblue", ""),
    "vercel.json": ("fg:ansiwhite", ""),
    "vimrc": ("", ""),
    "vlcrc": ("fg:ansiyellow", "󰕼"),
    "webpack": ("fg:ansibrightblack", "󰜫"),
    "weston.ini": ("fg:ansiyellow", ""),
    "workspace": ("fg:ansiyellow", ""),
    "wrangler.jsonc": ("fg:ansiyellow", ""),
    "wrangler.toml": ("fg:ansiyellow", ""),
    "xmobarrc": ("fg:ansibrightred", ""),
    "xmobarrc.hs": ("fg:ansibrightred", ""),
    "xmonad.hs": ("fg:ansibrightred", ""),
    "xorg.conf": ("fg:ansired", ""),
    "xsettingsd.conf": ("fg:ansired", ""),
}


def is_dir(path: str | Path) -> bool | None:
    """Check if a path is a directory."""
    from upath import UPath

    test_path = UPath(path)
    try:
        return test_path.is_dir()
    except (ValueError, PermissionError, TypeError):
        return None


class FileBrowserControl(UIControl):
    """A control for browsing a filesystem."""

    def __init__(
        self,
        path: Path
        | Callable[[], Path]
        | list[Path]
        | Callable[[], list[Path]]
        | None = None,
        on_chdir: Callable[[FileBrowserControl], None] | None = None,
        on_select: Callable[[FileBrowserControl], None] | None = None,
        on_open: Callable[[FileBrowserControl], None] | None = None,
        window: Window | None = None,
        show_icons: FilterOrBool = False,
        show_hidden: FilterOrBool = False,
    ) -> None:
        """Initialize a new file browser instance."""
        from upath import UPath

        self.show_icons = to_filter(show_icons)
        self.show_hidden = to_filter(show_hidden)
        if path is None:
            path = UPath(".")
        self.dir = path
        self.hovered: int | None = None
        self.selected: int | None = None
        self._dir_cache: FastDictCache[tuple[Path, bool], list[tuple[bool, Path]]] = (
            FastDictCache(get_value=self.load_path, size=1)
        )
        self.on_select = Event(self, on_select)
        self.on_chdir = Event(self, on_chdir)
        self.on_open = Event(self, on_open)

        self.window = window

        self.on_chdir.fire()

        self.key_bindings = kb = KeyBindings()

        @kb.add("up")
        @kb.add("<scroll-up>")
        def _move_up(event: KeyPressEvent) -> None:
            self.move_cursor_up()

        @kb.add("down")
        @kb.add("<scroll-down>")
        def _move_down(event: KeyPressEvent) -> None:
            self.move_cursor_down()

        @kb.add("home")
        def _home(event: KeyPressEvent) -> None:
            self.select(0)

        @kb.add("end")
        def _end(event: KeyPressEvent) -> None:
            self.select(len(self.contents) - 1)

        @kb.add("left")
        def _up(event: KeyPressEvent) -> None:
            self.dir = self.dir.parent

        @kb.add("space")
        @kb.add("enter")
        @kb.add("right")
        def _open(event: KeyPressEvent) -> None:
            return self.open_path()

    @property
    def contents(self) -> list[tuple[bool, Path]]:
        """Return the contents of the current folder."""
        if isinstance(self.dir, Path):
            return self._dir_cache[(self.dir, bool(self.show_hidden()))]
        elif isinstance(self.dir, list):
            return [(x.is_dir(), x) for x in self.dir]

    @property
    def dir(self) -> Path:
        """Return the current folder path."""
        if callable(self._dir):
            return self._dir()
        return self._dir

    @dir.setter
    def dir(self, value: PT) -> None:
        """Set the current folder path."""
        if isinstance(value, list) or callable(value):
            self._dir = value
            return

        from upath import UPath

        dir_path = UPath(value)
        try:
            dir_path = dir_path.resolve()
        except NotImplementedError:
            pass
        if is_dir(dir_path):
            self._dir = dir_path
        else:
            log.warning("'%s' is not a directory, not changing directory", value)

    @property
    def path(self) -> Path:
        """Return the current selected path."""
        return self.contents[self.selected or 0][1]

    @staticmethod
    def load_path(path: Path, show_hidden: bool) -> list[tuple[bool, Path]]:
        """Return the contents of a folder."""
        paths = [] if path.parent == path else [path / ".."]
        try:
            entries = list(path.iterdir())
            if not show_hidden:
                # Filter out names starting with dot
                entries = [e for e in entries if not e.name.startswith(".")]
            paths += entries
        except PermissionError:
            pass
        is_dirs = []
        for child in paths:
            child_is_dir = is_dir(child)
            if child_is_dir is None:
                child_is_dir = True
            is_dirs.append(child_is_dir)
        return sorted(zip(is_dirs, paths), key=lambda x: (not x[0], x[1].name))

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate the content for this user control."""
        paths = self.contents

        def get_line(i: int) -> StyleAndTextTuples:
            if i > len(paths) - 1:
                return []
            is_dir, child = paths[i]

            style = "class:row"
            if i % 2:
                style += " class:alt"
            if i == self.hovered:
                style += " class:hovered"
            if i == self.selected:
                style += " class:selection"
            row: StyleAndTextTuples = [(style, child.name)]

            if self.show_icons():
                icon = (
                    FILE_ICONS["__dir"]
                    if is_dir
                    else FILE_ICONS.get(child.suffix)
                    or FILE_ICONS.get(child.name)
                    or FILE_ICONS["__file"]
                )
                row[0:0] = [(style, " "), (f"{icon[0]} {style}", icon[1]), (style, " ")]

            return pad(row, width=width, style=style)

        return UIContent(
            get_line=get_line,
            line_count=len(paths),
            cursor_position=Point(0, self.selected or 0),
            show_cursor=False,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events."""
        row = mouse_event.position.y
        app = get_app()
        if (
            mouse_event.button == MouseButton.LEFT
            and mouse_event.event_type == MouseEventType.MOUSE_DOWN
        ):
            app.layout.current_control = self
            app.mouse_limits = None
            self.hovered = None
            return self.select(row, open_file=True)
        elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            # Mark item as hovered if mouse is over the control
            if (
                self.window is not None
                and (info := self.window.render_info) is not None
            ):
                rowcol_to_yx = info._rowcol_to_yx
                abs_mouse_pos = (
                    mouse_event.position.x + info._x_offset,
                    mouse_event.position.y + info._y_offset - info.vertical_scroll,
                )
                if abs_mouse_pos == app.mouse_position:
                    row_col_vals = rowcol_to_yx.values()
                    y_min, x_min = min(row_col_vals)
                    y_max, x_max = max(row_col_vals)
                    app.mouse_limits = WritePosition(
                        xpos=x_min,
                        ypos=y_min,
                        width=x_max - x_min + 1,
                        height=y_max - y_min + 1,
                    )
                    return self.hover(row)
                else:
                    # Clear mouse limits if mouse is outside control
                    app.mouse_limits = None
                    self.hovered = None
                    return None

        return NotImplemented

    def select(self, row: int | None, open_file: bool = False) -> NotImplementedOrNone:
        """Select a file in the browser."""
        if row is None:
            row = 0
        row = min(max(0, row), len(self.contents) - 1)
        if self.selected != row:
            self.selected = row
            self.on_select.fire()
        elif open_file:
            self.open_path()
        return None

    def hover(self, row: int | None) -> NotImplementedOrNone:
        """Hover a file in the browser."""
        if row is not None:
            row = min(max(0, row), len(self.contents) - 1)
            if self.hovered != row:
                self.hovered = row
                return None
        return NotImplemented

    def open_path(self) -> None:
        """Open the selected file."""
        if self.contents and self.selected is not None:
            is_dir, path = self.contents[self.selected]
            if is_dir:
                self.dir = path.resolve()
                self.hover(self.hovered)
                self.selected = None
                self.on_chdir.fire()
            else:
                self.on_open.fire()

    def move_cursor_down(self) -> None:
        """Request to move the cursor down."""
        index = self.selected
        if index is None:
            index = 0
        else:
            index += 1
        self.select(index)

    def move_cursor_up(self) -> None:
        """Request to move the cursor up."""
        index = self.selected
        if index is None:
            index = len(self.contents)
        else:
            index -= 1
        self.select(index)

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """Key bindings specific to this user control."""
        return self.key_bindings

    def is_focusable(self) -> bool:
        """Determine that the file_browser is focusable."""
        return True

    def __pt_status__(self) -> StatusBarFields:
        """Show the selected or hovered path in the statusbar."""
        if self.contents:
            if self.hovered is not None:
                return [[("", str(self.contents[self.hovered][1]))]], []
            elif self.selected is not None:
                return [[("", str(self.contents[self.selected][1]))]], []
        return [], []


class FileBrowser:
    """A file browser."""

    completer = PathCompleter(only_directories=True)

    def __init__(
        self,
        path: Path
        | Callable[[], Path]
        | list[Path]
        | Callable[[], list[Path]]
        | None = None,
        on_select: Callable[[Path], None] | None = None,
        on_open: Callable[[Path], None] | None = None,
        on_chdir: Callable[[Path], None] | None = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        style: str = "",
        show_address_bar: FilterOrBool = True,
        show_icons: FilterOrBool = False,
        show_hidden: FilterOrBool = False,
    ) -> None:
        """Create a new instance."""

        def _accept_path(buffer: Buffer) -> bool:
            control.dir = Path(buffer.text)
            return True

        def _validate_path(path: str) -> bool:
            return is_dir(path) or False

        text = Text(
            validation=_validate_path,
            accept_handler=_accept_path,
            completer=self.completer,
            show_borders=DiBool(top=True, right=False, bottom=True, left=True),
        )
        self.control = control = FileBrowserControl(
            path=path,
            on_chdir=lambda x: setattr(text, "text", str(x.dir)),
            show_icons=show_icons,
            show_hidden=show_hidden,
        )
        if on_select is not None:
            control.on_select += (
                lambda x: on_select(x.path) if callable(on_select) else None
            )
        if on_chdir is not None:
            control.on_chdir += (
                lambda x: on_chdir(x.path) if callable(on_chdir) else None
            )
        if on_open is not None:
            control.on_open += lambda x: on_open(x.path) if callable(on_open) else None

        self.container = HSplit(
            [
                ConditionalContainer(
                    VSplit(
                        [
                            FocusedStyle(text),
                            FocusedStyle(
                                Button(
                                    "➜",
                                    show_borders=DiBool(
                                        top=True, right=True, bottom=True, left=False
                                    ),
                                    on_click=lambda x: setattr(
                                        control, "dir", text.text
                                    ),
                                )
                            ),
                            FocusedStyle(
                                Button(
                                    "↻",
                                    on_click=lambda x: control._dir_cache.clear(),
                                )
                            ),
                        ]
                    ),
                    filter=to_filter(show_address_bar),
                ),
                FocusedStyle(
                    Border(
                        VSplit(
                            [
                                window := Window(
                                    control,
                                    style="class:face",
                                ),
                                MarginContainer(ScrollbarMargin(), target=window),
                            ],
                            style="class:input,list",
                        ),
                        border=InsetGrid,
                        style="class:input,inset,border",
                    ),
                    style_hover="",
                ),
            ],
            style=style,
            width=width,
            height=height,
        )
        # Set control's window so it can determine its position for mouse-over
        control.window = window

    def __pt_container__(self) -> AnyContainer:
        """Return the tree-view container's content."""
        return self.container

    def __pt_status__(self) -> StatusBarFields:
        """Show the selected or hovered path in the statusbar."""
        return self.control.__pt_status__()
