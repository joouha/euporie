"""Defines a file browser widget."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.key_binding.key_bindings import KeyBindings, KeyBindingsBase
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core.border import InnerEigthGrid
from euporie.core.margins import ScrollbarMargin
from euporie.core.widgets.decor import Border, FocusedStyle
from euporie.core.widgets.forms import Button, Text

if TYPE_CHECKING:
    from typing import Callable

    from prompt_toolkit.filters.base import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension
    from upath.core import PT

log = logging.getLogger(__name__)


FILE_ICONS = {
    # default
    "file": "",
    "dir": "",
    # file extensions (vim-devicons)
    ".styl": "",
    ".sass": "",
    ".scss": "",
    ".htm": "",
    ".html": "",
    ".slim": "",
    ".haml": "",
    ".ejs": "",
    ".css": "",
    ".less": "",
    ".md": "",
    ".mdx": "",
    ".markdown": "",
    ".rmd": "",
    ".json": "",
    ".webmanifest": "",
    ".js": "",
    ".mjs": "",
    ".jsx": "",
    ".rb": "",
    ".gemspec": "",
    ".rake": "",
    ".php": "",
    ".py": "",
    ".pyc": "",
    ".pyo": "",
    ".pyd": "",
    ".coffee": "",
    ".mustache": "",
    ".hbs": "",
    ".conf": "",
    ".ini": "",
    ".yml": "",
    ".yaml": "",
    ".toml": "",
    ".bat": "",
    ".mk": "",
    ".twig": "",
    ".cpp": "",
    ".c++": "",
    ".cxx": "",
    ".cc": "",
    ".cp": "",
    ".c": "",
    ".cs": "",
    ".h": "",
    ".hh": "",
    ".hpp": "",
    ".hxx": "",
    ".hs": "",
    ".lhs": "",
    ".nix": "",
    ".lua": "",
    ".java": "",
    ".sh": "",
    ".fish": "",
    ".bash": "",
    ".zsh": "",
    ".ksh": "",
    ".csh": "",
    ".awk": "",
    ".ps1": "",
    ".ml": "λ",
    ".mli": "λ",
    ".diff": "",
    ".db": "",
    ".sql": "",
    ".dump": "",
    ".clj": "",
    ".cljc": "",
    ".cljs": "",
    ".edn": "",
    ".scala": "",
    ".go": "",
    ".dart": "",
    ".xul": "",
    ".sln": "",
    ".suo": "",
    ".pl": "",
    ".pm": "",
    ".t": "",
    ".rss": "",
    ".f#": "",
    ".fsscript": "",
    ".fsx": "",
    ".fs": "",
    ".fsi": "",
    ".rs": "",
    ".rlib": "",
    ".d": "",
    ".erl": "",
    ".hrl": "",
    ".ex": "",
    ".exs": "",
    ".eex": "",
    ".leex": "",
    ".heex": "",
    ".vim": "",
    ".ai": "",
    ".psd": "",
    ".psb": "",
    ".ts": "",
    ".tsx": "",
    ".jl": "",
    ".pp": "",
    ".vue": "﵂",
    ".elm": "",
    ".swift": "",
    ".xcplayground": "",
    ".tex": "ﭨ",
    ".r": "ﳒ",
    ".rproj": "鉶",
    ".sol": "ﲹ",
    ".pem": "",
    # file names (vim-devicons) (case-insensitive not supported in lf)
    "gruntfile.coffee": "",
    "gruntfile.js": "",
    "gruntfile.ls": "",
    "gulpfile.coffee": "",
    "gulpfile.js": "",
    "gulpfile.ls": "",
    "mix.lock": "",
    "dropbox": "",
    ".ds_store": "",
    ".gitconfig": "",
    ".gitignore": "",
    ".gitattributes": "",
    ".gitlab-ci.yml": "",
    ".bashrc": "",
    ".zshrc": "",
    ".zshenv": "",
    ".zprofile": "",
    ".vimrc": "",
    ".gvimrc": "",
    "_vimrc": "",
    "_gvimrc": "",
    ".bashprofile": "",
    "favicon.ico": "",
    "license": "",
    "node_modules": "",
    "react.jsx": "",
    "procfile": "",
    "dockerfile": "",
    "docker-compose.yml": "",
    "rakefile": "",
    "config.ru": "",
    "gemfile": "",
    "makefile": "",
    "cmakelists.txt": "",
    "robots.txt": "ﮧ",
    # file names (case-sensitive adaptations)
    "Gruntfile.coffee": "",
    "Gruntfile.js": "",
    "Gruntfile.ls": "",
    "Gulpfile.coffee": "",
    "Gulpfile.js": "",
    "Gulpfile.ls": "",
    "Dropbox": "",
    ".DS_Store": "",
    "LICENSE": "",
    "React.jsx": "",
    "Procfile": "",
    "Dockerfile": "",
    "Docker-compose.yml": "",
    "Rakefile": "",
    "Gemfile": "",
    "Makefile": "",
    "CMakeLists.txt": "",
    # file patterns (file name adaptations)
    "jquery.min.js": "",
    "angular.min.js": "",
    "backbone.min.js": "",
    "require.min.js": "",
    "materialize.min.js": "",
    "materialize.min.css": "",
    "mootools.min.js": "",
    "vimrc": "",
    "Vagrantfile": "",
    # archives or compressed (extensions from dircolors defaults)
    ".tar": "",
    ".tgz": "",
    ".arc": "",
    ".arj": "",
    ".taz": "",
    ".lha": "",
    ".lz4": "",
    ".lzh": "",
    ".lzma": "",
    ".tlz": "",
    ".txz": "",
    ".tzo": "",
    ".t7z": "",
    ".zip": "",
    ".z": "",
    ".dz": "",
    ".gz": "",
    ".lrz": "",
    ".lz": "",
    ".lzo": "",
    ".xz": "",
    ".zst": "",
    ".tzst": "",
    ".bz2": "",
    ".bz": "",
    ".tbz": "",
    ".tbz2": "",
    ".tz": "",
    ".deb": "",
    ".rpm": "",
    ".jar": "",
    ".war": "",
    ".ear": "",
    ".sar": "",
    ".rar": "",
    ".alz": "",
    ".ace": "",
    ".zoo": "",
    ".cpio": "",
    ".7z": "",
    ".rz": "",
    ".cab": "",
    ".wim": "",
    ".swm": "",
    ".dwm": "",
    ".esd": "",
    # image formats (extensions from dircolors defaults)
    ".jpg": "",
    ".jpeg": "",
    ".mjpg": "",
    ".mjpeg": "",
    ".webp": "",
    ".ico": "",
    ".gif": "",
    ".bmp": "",
    ".pbm": "",
    ".pgm": "",
    ".ppm": "",
    ".tga": "",
    ".xbm": "",
    ".xpm": "",
    ".tif": "",
    ".tiff": "",
    ".png": "",
    ".svg": "",
    ".svgz": "",
    ".mng": "",
    ".pcx": "",
    ".mov": "",
    ".mpg": "",
    ".mpeg": "",
    ".m2v": "",
    ".mkv": "",
    ".webm": "",
    ".ogm": "",
    ".mp4": "",
    ".m4v": "",
    ".mp4v": "",
    ".vob": "",
    ".qt": "",
    ".nuv": "",
    ".wmv": "",
    ".asf": "",
    ".rm": "",
    ".rmvb": "",
    ".flc": "",
    ".avi": "",
    ".fli": "",
    ".flv": "",
    ".gl": "",
    ".dl": "",
    ".xcf": "",
    ".xwd": "",
    ".yuv": "",
    ".cgm": "",
    ".emf": "",
    ".ogv": "",
    ".ogx": "",
    # audio formats (extensions from dircolors defaults)
    ".aac": "",
    ".au": "",
    ".flac": "",
    ".m4a": "",
    ".mid": "",
    ".midi": "",
    ".mka": "",
    ".mp3": "",
    ".mpc": "",
    ".ogg": "",
    ".ra": "",
    ".wav": "",
    ".oga": "",
    ".opus": "",
    ".spx": "",
    ".xspf": "",
    # documents
    ".pdf": "",
    ".doc": "",
    ".docx": "",
    ".ipynb": "ﴬ",
}


def is_dir(path: "str") -> "bool|None":
    """Check if a path is a directory."""
    test_path = UPath(path)
    try:
        return test_path.is_dir()
    except (ValueError, PermissionError, TypeError):
        return None


class FileBrowserControl(UIControl):
    """A control for browsing a filesystem."""

    def __init__(
        self,
        path: "UPath" = None,
        on_chdir: "Callable[[FileBrowserControl], None]|None" = None,
        on_select: "Callable[[FileBrowserControl], None]|None" = None,
        on_open: "Callable[[FileBrowserControl], None]|None" = None,
    ) -> "None":
        """Initialize a new file browser instance."""
        self.dir = path or UPath(".")
        self.hovered: "int" = 0
        self.selected: "int|None" = None
        self._dir_cache: "FastDictCache[UPath, list[tuple[bool, UPath]]]" = (
            FastDictCache(get_value=self.load_path, size=1)
        )
        self.on_select = Event(self, on_select)
        self.on_chdir = Event(self, on_chdir)
        self.on_open = Event(self, on_open)

        self.on_chdir.fire()

        self.key_bindings = kb = KeyBindings()

        @kb.add("up")
        @kb.add("<scroll-up>")
        def _move_up(event: "KeyPressEvent") -> "None":
            self.move_cursor_up()

        @kb.add("down")
        @kb.add("<scroll-down>")
        def _move_down(event: "KeyPressEvent") -> "None":
            self.move_cursor_down()

        @kb.add("home")
        def _home(event: "KeyPressEvent") -> "None":
            self.select(0)

        @kb.add("end")
        def _end(event: "KeyPressEvent") -> "None":
            self.select(len(self.contents) - 1)

        @kb.add("left")
        def _up(event: "KeyPressEvent") -> "None":
            self.dir = self.dir.parent

        @kb.add("space")
        @kb.add("enter")
        @kb.add("right")
        def _open(event: "KeyPressEvent") -> "None":
            return self.open_path()

    @property
    def contents(self) -> "list[tuple[bool, UPath]]":
        """Return the contents of the current folder."""
        return self._dir_cache[(self.dir,)]

    @property
    def dir(self) -> "UPath":
        """Return the current folder path."""
        return self._dir

    @dir.setter
    def dir(self, value: "PT") -> "None":
        """Set the current folder path."""
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
    def path(self) -> "UPath":
        """Return the current selected path."""
        return self.contents[self.selected or 0][1]

    @staticmethod
    def load_path(path: "UPath") -> "list[tuple[bool, UPath]]":
        """Return the contents of a folder."""
        paths = [] if path.parent == path else [path / ".."]
        try:
            paths += list(path.iterdir())
        except PermissionError:
            pass
        is_dirs = []
        for child in paths:
            child_is_dir = is_dir(child)
            if child_is_dir is None:
                child_is_dir = True
            is_dirs.append(child_is_dir)
        return sorted(zip(is_dirs, paths), key=lambda x: (not x[0], x[1].name))

    def create_content(self, width: int, height: int) -> "UIContent":
        """Generate the content for this user control."""
        paths = self.contents

        def get_line(i: int) -> StyleAndTextTuples:
            if i > len(paths) - 1:
                return []
            is_dir, child = paths[i]
            icon = (
                FILE_ICONS["dir"]
                if is_dir
                else FILE_ICONS.get(child.suffix)
                or FILE_ICONS.get(child.name)
                or FILE_ICONS["file"]
            )
            style = "class:row"
            if i % 2:
                style += " class:alt-row"
            if i == self.hovered:
                style += " class:hovered"
            if i == self.selected:
                style += " class:selection"
            return [(style, f" {icon} {child.name} ".ljust(width))]

        return UIContent(
            get_line=get_line,
            line_count=len(paths),
            cursor_position=Point(0, self.selected or 0),
            show_cursor=False,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> "NotImplementedOrNone":
        """Handle mouse events."""
        row = mouse_event.position.y
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            get_app().layout.current_control = self
            return self.select(row, open_file=True)
        elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            return self.hover(row)

        return NotImplemented

    def select(
        self, row: "int|None", open_file: "bool" = False
    ) -> "NotImplementedOrNone":
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

    def hover(self, row: int) -> "NotImplementedOrNone":
        """Hover a file in the browser."""
        row = min(max(0, row), len(self.contents) - 1)
        if self.hovered != row:
            self.hovered = row
            return None
        return NotImplemented

    def open_path(self) -> "None":
        """Open the selected file."""
        if self.selected is not None:
            is_dir, path = self.contents[self.selected]
            if is_dir:
                self.dir = path.resolve()
                self.hover(self.hovered)
                self.selected = None
                self.on_chdir.fire()
            else:
                self.on_open.fire()

    def move_cursor_down(self) -> "None":
        """Request to move the cursor down."""
        index = self.selected
        if index is None:
            index = 0
        else:
            index += 1
        self.select(index)

    def move_cursor_up(self) -> "None":
        """Request to move the cursor up."""
        index = self.selected
        if index is None:
            index = len(self.contents)
        else:
            index -= 1
        self.select(index)

    def get_key_bindings(self) -> "KeyBindingsBase|None":
        """The key bindings that are specific for this user control."""
        return self.key_bindings

    def is_focusable(self) -> "bool":
        """Determines that the file_browser is focusable."""
        return True


class FileBrowser:
    """A file browser."""

    completer = PathCompleter(only_directories=True)

    def __init__(
        self,
        path: "UPath" = None,
        on_select: "Callable[[UPath], None]|None" = None,
        on_open: "Callable[[UPath], None]|None" = None,
        on_chdir: "Callable[[UPath], None]|None" = None,
        width: "AnyDimension" = None,
        height: "AnyDimension" = None,
        style: "str" = "",
        show_address_bar: "FilterOrBool" = True,
    ) -> "None":
        """Create a new instance."""

        def _accept_path(buffer: "Buffer") -> "bool":
            control.dir = buffer.text
            return True

        def _validate_path(path: "str") -> "bool":
            return is_dir(path) or False

        text = Text(
            validation=_validate_path,
            accept_handler=_accept_path,
            completer=self.completer,
        )
        self.control = control = FileBrowserControl(
            path=path,
            on_open=lambda x: log.debug(x.path),
            on_chdir=lambda x: setattr(text, "text", str(x.dir)),
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
                                    "Go",
                                    on_click=lambda x: setattr(
                                        control, "dir", text.text
                                    ),
                                )
                            ),
                        ]
                    ),
                    filter=to_filter(show_address_bar),
                ),
                Border(
                    FocusedStyle(
                        Window(
                            control,
                            style="class:face",
                            right_margins=[ScrollbarMargin()],
                        )
                    ),
                    border=InnerEigthGrid,
                    style="class:input,inset,border",
                ),
            ],
            style="class:file-browser " + style,
            width=width,
            height=height,
        )

    def __pt_container__(self) -> "AnyContainer":
        """Return the tree-view container's content."""
        return self.container
