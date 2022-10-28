"""Style related functions."""

from __future__ import annotations

import logging
from colorsys import hls_to_rgb, rgb_to_hls
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.styles.base import DEFAULT_ATTRS, BaseStyle
from prompt_toolkit.styles.defaults import default_ui_style
from prompt_toolkit.styles.style import Style, _parse_style_str, merge_styles

if TYPE_CHECKING:
    from typing import Any, Hashable, Optional

    from prompt_toolkit.styles.base import Attrs
    from prompt_toolkit.styles.style import _MergedStyle

log = logging.getLogger(__name__)


KERNEL_STATUS_REPR = {
    "stopped": "⨂",
    "starting": "◍",
    "idle": "○",
    "busy": "●",
    "error": "☹",
}


DEFAULT_COLORS = {
    "bg": "#232627",
    "fg": "#fcfcfc",
    "ansiblack": "#000000",
    "ansired": "#cc0403",
    "ansigreen": "#19cb00",
    "ansiyellow": "#cecb00",
    "ansiblue": "#0d73cc",
    "ansipurple": "#cb1ed1",
    "ansimagenta": "#cb1ed1",
    "ansicyan": "#0dcdcd",
    "ansiwhite": "#dddddd",
    "ansibrightblack": "#767676",
    "ansigray": "#767676",
    "ansibrightred": "#f2201f",
    "ansibrightgreen": "#23fd00",
    "ansibrightyellow": "#fffd00",
    "ansibrightblue": "#1a8fff",
    "ansibrightpurple": "#fd28ff",
    "ansibrightmagenta": "#fd28ff",
    "ansibrightcyan": "#14ffff",
    "ansibrightwhite": "#ffffff",
}


MIME_STYLE = [
    ("mime.stream.stderr", "fg:ansired"),
]

HTML_STYLE = [
    ("html h1", "bold underline"),
    ("html h1 border", "fg:ansiyellow nounderline"),
    ("html h2", "bold"),
    ("html h2 border", "fg:grey nobold"),
    ("html h3", "bold"),
    ("html h4", "bold italic"),
    ("html h5", "underline"),
    ("html h6", "italic"),
    ("html code", "bg:#333"),
    ("html kbd", "fg:#fff bg:#333"),
    ("html samp", "fg:#fff bg:#333"),
    ("html b", "bold"),
    ("html strong", "bold"),
    ("html i", "italic"),
    ("html em", "italic"),
    ("html cite", "italic"),
    ("html dfn", "italic"),
    ("html var", "italic"),
    ("html u", "underline"),
    ("html ins", "underline"),
    ("html s", "strike"),
    ("html del", "strike"),
    ("html mark", "fg:black bg:ansiyellow"),
    ("html hr", "fg:ansired"),
    ("html ul ul.bullet", "fg:ansiyellow"),
    ("html ol ol.bullet", "fg:ansicyan"),
    ("html blockquote", "fg:ansipurple"),
    ("html blockquote margin", "fg:grey"),
    ("html th", "bold"),
    ("html a", "underline fg:ansibrightblue"),
    ("html img", "bg:cyan fg:black"),
    ("html img border", "fg:cyan bg:default"),
    ("html caption", "italic"),
    ("html summary", "bold"),
]


LOG_STYLE = [
    ("log.level.nonset", "fg:ansigray"),
    ("log.level.debug", "fg:ansigreen"),
    ("log.level.info", "fg:ansiblue"),
    ("log.level.warning", "fg:ansiyellow"),
    ("log.level.error", "fg:ansired"),
    ("log.level.critical", "fg:ansiwhite bg:ansired bold"),
]

IPYWIDGET_STYLE = [
    ("ipywidget", "bg:default"),
    ("ipywidget focused", ""),
    ("ipywidget button face success", "bg:ansigreen"),
    ("ipywidget button face", "fg:black bg:#d4d0c8"),
    ("ipywidget button face success", "bg:ansigreen"),
    ("ipywidget button face info", "bg:ansicyan"),
    ("ipywidget button face warning", "bg:ansiyellow"),
    ("ipywidget button face danger", "bg:ansired"),
    ("ipywidget button border right", "fg:#606060"),
    ("ipywidget button border bottom", "fg:#606060"),
    ("ipywidget button border left", "fg:#ffffff"),
    ("ipywidget button border top", "fg:#ffffff"),
    ("ipywidget button face disabled", "fg:#888888"),
    ("ipywidget selection border right", "fg:#ffffff"),
    ("ipywidget selection border bottom", "fg:#ffffff"),
    ("ipywidget selection border left", "fg:#606060"),
    ("ipywidget selection border top", "fg:#606060"),
    ("ipywidget success border left", "fg:ansibrightgreen"),
    ("ipywidget success border top", "fg:ansibrightgreen"),
    ("ipywidget info border left", "fg:ansibrightcyan"),
    ("ipywidget info border top", "fg:ansibrightcyan"),
    ("ipywidget warning border left", "fg:ansibrightyellow"),
    ("ipywidget warning border top", "fg:ansibrightyellow"),
    ("ipywidget danger border left", "fg:ansibrightred"),
    ("ipywidget danger border top", "fg:ansibrightred"),
    ("ipywidget selection border left", "fg:#606060"),
    ("ipywidget selection border top", "fg:#606060"),
    ("ipywidget selection success border right", "fg:ansibrightgreen"),
    ("ipywidget selection success border bottom", "fg:ansibrightgreen"),
    ("ipywidget selection success border right", "fg:ansibrightgreen"),
    ("ipywidget selection success border bottom", "fg:ansibrightgreen"),
    ("ipywidget selection info border right", "fg:ansibrightcyan"),
    ("ipywidget selection info border bottom", "fg:ansibrightcyan"),
    ("ipywidget selection danger border right", "fg:ansibrightred"),
    ("ipywidget selection danger border bottom", "fg:ansibrightred"),
    ("ipywidget text text-area", "fg:black bg:white"),
    ("ipywidget text placeholder", "fg:#AAAAAA bg:white"),
    ("ipywidget text border right", "fg:#E9E7E3"),
    ("ipywidget text border top", "fg:#606060"),
    ("ipywidget text border bottom", "fg:#E9E7E3"),
    ("ipywidget text border left", "fg:#606060"),
    ("ipywidget text border top invalid", "fg:ansidarkred"),
    ("ipywidget text border right invalid", "fg:ansired"),
    ("ipywidget text border bottom invalid", "fg:ansired"),
    ("ipywidget text border left invalid", "fg:ansidarkred"),
    ("ipywidget slider track selection", "fg:ansiblue"),
    ("ipywidget slider handle focused", "fg:white"),
    ("ipywidget slider handle selection", ""),
    ("ipywidget slider handle selection focused", "fg:ansiblue"),
    ("ipywidget progress", "fg:ansidarkblue bg:#d4d0c8"),
    ("ipywidget progress success", "fg:ansigreen"),
    ("ipywidget progress info", "fg:ansicyan"),
    ("ipywidget progress warning", "fg:ansiyellow"),
    ("ipywidget progress danger", "fg:ansired"),
    ("ipywidget progress border", "bg:default"),
    ("ipywidget progress border top", "fg:#606060"),
    ("ipywidget progress border right", "fg:#E9E7E3"),
    ("ipywidget progress border bottom", "fg:#E9E7E3"),
    ("ipywidget progress border left", "fg:#606060"),
    ("ipywidget dropdown dropdown.menu", "fg:#000000 bg:#ffffff"),
    ("ipywidget dropdown dropdown.menu hovered", "fg:#ffffff bg:ansiblue"),
    ("ipywidget checkbox selection", "fg:default"),
    ("ipywidget checkbox prefix selection", "fg:ansiblue"),
    ("ipywidget checkbox disabled", "fg:#888888"),
    ("ipywidget checkbox prefix selection disabled", "fg:#888888"),
    ("ipywidget valid prefix", "fg:ansired"),
    ("ipywidget valid prefix selection", "fg:ansigreen"),
    ("ipywidget radio-buttons selection", "fg:default"),
    ("ipywidget radio-buttons selection disabled", "fg:#888888"),
    ("ipywidget radio-buttons prefix selection", "fg:ansiblue"),
    ("ipywidget select face", "fg:black bg:white"),
    ("ipywidget select face selection", "fg:white bg:ansiblue"),
    ("ipywidget select face hovered", "fg:black bg:#f0f0f0"),
    ("ipywidget select face hovered selection", "fg:white bg:ansiblue"),
    ("ipywidget select border top", "fg:#606060"),
    ("ipywidget select border right", "fg:#E9E7E3"),
    ("ipywidget select border bottom", "fg:#E9E7E3"),
    ("ipywidget select border left", "fg:#606060"),
    ("ipywidget select disabled", "fg:#888888"),
    ("ipywidget select selection disabled", "fg:#888888"),
    ("ipywidget inset border right", "fg:#E9E7E3"),
    ("ipywidget inset border top", "fg:#606060"),
    ("ipywidget inset border bottom", "fg:#E9E7E3"),
    ("ipywidget inset border left", "fg:#606060"),
    ("ipywidget swatch border right", "fg:#E9E7E3"),
    ("ipywidget swatch border top", "fg:#606060"),
    ("ipywidget swatch border bottom", "fg:#E9E7E3"),
    ("ipywidget swatch border left", "fg:#606060"),
    ("ipywidget tabbed-split tab-bar tab active border top default", "fg:ansiblue"),
    ("ipywidget tabbed-split tab-bar tab active border top success", "fg:ansigreen"),
    ("ipywidget tabbed-split tab-bar tab active border top info", "fg:ansicyan"),
    ("ipywidget tabbed-split tab-bar tab active border top warning", "fg:ansiyellow"),
    ("ipywidget tabbed-split tab-bar tab active border top danger", "fg:ansired"),
    ("ipywidget accordion border success", "fg:ansigreen"),
    ("ipywidget accordion border info", "fg:ansicyan"),
    ("ipywidget accordion border warning", "fg:ansiyellow"),
    ("ipywidget accordion border danger", "fg:ansired"),
    ("ipywidget accordion selection", "fg:ansiblue"),
]


class ColorPaletteColor:
    """A representation of a color with adjustment methods."""

    _cache: "SimpleCache[tuple[str, float, float, float, bool], ColorPaletteColor]" = (
        SimpleCache()
    )

    def __init__(self, base: "str", _base_override: str = "") -> "None":
        """Creates a new color."""
        self.base_hex = DEFAULT_COLORS.get(base, base)
        self.base = _base_override or base

        color = self.base_hex.lstrip("#")
        self.red, self.green, self.blue = (
            int(color[0:2], 16) / 255,
            int(color[2:4], 16) / 255,
            int(color[4:6], 16) / 255,
        )

        self.hue, self.brightness, self.saturation = rgb_to_hls(
            self.red, self.green, self.blue
        )

        self.is_light = self.brightness > 0.5

    def _adjust_abs(
        self, hue: "float" = 0.0, brightness: "float" = 0.0, saturation: "float" = 0.0
    ) -> "ColorPaletteColor":
        hue = max(min(1, self.hue + hue), 0)
        brightness = max(min(1, self.brightness + brightness), 0)
        saturation = max(min(1, self.saturation + saturation), 0)

        r, g, b = hls_to_rgb(hue, brightness, saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def _adjust_rel(
        self, hue: "float" = 0.0, brightness: "float" = 0.0, saturation: "float" = 0.0
    ) -> "ColorPaletteColor":
        hue = min(max(0, hue), 1)
        brightness = min(max(-1, brightness), 1)
        saturation = min(max(-1, saturation), 1)

        new_hue = self.hue + (self.hue * (hue < 0) + (1 - self.hue) * (hue > 0)) * hue

        new_brightness = (
            self.brightness
            + (
                self.brightness * (brightness < 0)
                + (1 - self.brightness) * (brightness > 0)
            )
            * brightness
        )

        new_saturation = (
            self.saturation
            + (
                self.saturation * (saturation < 0)
                + (1 - self.saturation) * (saturation > 0)
            )
            * saturation
        )

        r, g, b = hls_to_rgb(new_hue, new_brightness, new_saturation)
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def _adjust(
        self,
        hue: "float" = 0.0,
        brightness: "float" = 0.0,
        saturation: "float" = 0.0,
        rel: "bool" = True,
    ) -> "ColorPaletteColor":
        """Performs a relative of absolute color adjustment."""
        if rel:
            return self._adjust_rel(hue, brightness, saturation)
        else:
            return self._adjust_abs(hue, brightness, saturation)

    def adjust(
        self,
        hue: "float" = 0.0,
        brightness: "float" = 0.0,
        saturation: "float" = 0.0,
        rel: "bool" = True,
    ) -> "ColorPaletteColor":
        """Adjust the hue, saturation, or brightness of the color."""
        key = (self.base_hex, hue, brightness, saturation, rel)
        return self._cache.get(
            key, partial(self._adjust, hue, brightness, saturation, rel)
        )

    def lighter(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes the color lighter."""
        return self.adjust(brightness=amount, rel=rel)

    def darker(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes the color darker."""
        return self.adjust(brightness=-amount, rel=rel)

    def more(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes bright colors darker and dark colors brighter."""
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=amount, rel=rel)

    def less(self, amount: "float", rel: "bool" = True) -> "ColorPaletteColor":
        """Makes bright colors brighter and dark colors darker."""
        if self.is_light:
            amount *= -1
        return self.adjust(brightness=-amount, rel=rel)

    def towards(
        self, other: "ColorPaletteColor", amount: "float"
    ) -> "ColorPaletteColor":
        """Interpolate between two colors."""
        amount = min(max(0, amount), 1)
        r = (other.red - self.red) * amount + self.red
        g = (other.green - self.green) * amount + self.green
        b = (other.blue - self.blue) * amount + self.blue
        new_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        return ColorPaletteColor(new_color)

    def __repr__(self) -> "str":
        """Returns a string representation of the color."""
        return self.base


class ColorPalette:
    """Defines a collection of colors."""

    def __init__(self):
        """Creates a new color-palette."""
        self.colors = {}

    def add_color(
        self, name: "str", base: "str", _base_override: str = ""
    ) -> "ColorPalette":
        """Adds a color to the palette."""
        self.colors[name] = ColorPaletteColor(base, _base_override)
        return self

    def __getattr__(self, name: "str") -> "Any":
        """Enables access of palette colors via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The color-palette color.

        """
        return self.colors.get(name)


def build_style(
    cp: "ColorPalette",
    have_term_colors: "bool" = True,
) -> "Style":
    """Create an application style based on the given color palette."""
    style_dict = {
        # The default style is merged at this point so full styles can be
        # overridden. For example, this allows us to switch off the underline
        # status of cursor-line.
        **dict(default_ui_style().style_rules),
        "default": f"fg:{cp.bg.base} bg:{cp.bg.base}",
        # Logo
        "logo": "fg:#dd0000",
        # Pattern
        "pattern": f"fg:{cp.bg.more(0.075)}",
        # Chrome
        "chrome": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "tab-padding": f"fg:{cp.bg.more(0.2)} bg:{cp.bg.base}",
        # Statusbar
        "status": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "status.field": f"fg:{cp.fg.more(0.1)} bg:{cp.bg.more(0.1)}",
        # Menus & Menu bar
        "menu": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "menu disabled": f"fg:{cp.fg.more(0.05).towards(cp.bg, 0.75)}",
        "menu shortcut": f"fg:{cp.fg.more(0.4)}",
        "menu shortcut disabled": f"fg:{cp.fg.more(0.4).towards(cp.bg, 0.5)}",
        "menu prefix": f"fg:{cp.fg.more(0.2)}",
        "menu prefix disabled": f"fg:{cp.fg.more(0.2).towards(cp.bg, 0.5)}",
        "menu selection": f"fg:{cp.hl.more(1)} bg:{cp.hl}",
        "menu selection shortcut": f"fg:{cp.hl.more(1).more(0.05)} bg:{cp.hl}",
        "menu selection prefix": f"fg:{cp.hl.more(1).more(0.05)} bg:{cp.hl}",
        "menu border": f"fg:{cp.bg.more(0.15)} bg:{cp.bg.more(0.05)}",
        "menu border selection": f"bg:{cp.hl}",
        # Tab bar
        "app-tab-bar": f"bg:{cp.bg.less(0.15)}",
        "app-tab-bar border": f"fg:{cp.bg.more(0.1)}",
        "app-tab-bar tab inactive": f"fg:{cp.fg.more(0.5)}",
        "app-tab-bar tab inactive border": f"fg:{cp.bg.more(0.15)}",
        "app-tab-bar tab active": "bold fg:default bg:default",
        "app-tab-bar tab active close": "fg:darkred",
        "app-tab-bar tab active border top": f"fg:{cp.hl} bg:{cp.bg.less(0.15)}",
        # Buffer
        "line-number": f"fg:{cp.fg.more(0.5)} bg:{cp.bg.more(0.05)}",
        "line-number.current": f"bold orange bg:{cp.bg.more(0.1)}",
        "line-number edge": f"fg:{cp.bg.darker(0.1)}",
        "line-number.current edge": f"fg:{cp.bg.darker(0.1)}",
        "cursor-line": f"bg:{cp.bg.more(0.05)}",
        "cursor-line search": f"bg:{cp.bg.more(0.02)}",
        "cursor-line search.current": f"bg:{cp.bg.more(0.02)}",
        "cursor-line incsearch": "bg:ansibrightyellow",
        "cursor-line incsearch.current": "bg:ansibrightgreen",
        "matching-bracket.cursor": "fg:yellow bold",
        "matching-bracket.other": "fg:yellow bold",
        "trailing-whitespace": f"fg:{cp.fg.more(0.66)}",
        "tab": f"fg:{cp.fg.more(0.66)}",
        # Search
        "search": f"bg:{cp.bg.more(0.05)}",
        "search.current": f"bg:{cp.bg.more(0.05)}",
        "incsearch": "bg:ansibrightyellow",
        "incsearch.current": "bg:ansibrightgreen",
        "search-toolbar": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "search-toolbar.title": f"fg:{cp.fg.more(0.1)} bg:{cp.bg.more(0.1)}",
        # Inputs
        "kernel-input": f"fg:default bg:{cp.bg.more(0.02)}",
        # Cells
        "cell.border": f"fg:{cp.bg.more(0.25)}",
        "cell.border.selected": f"fg:{cp.hl.more(0.2)}",
        "cell.border.edit": "fg:ansibrightgreen",
        "cell.output": "fg:default bg:default",
        "cell.input.prompt": "fg:blue",
        "cell.output.prompt": "fg:red",
        "cell show outputs": "bg:#888",
        "cell show inputs": "bg:#888",
        # Scrollbars
        "scrollbar": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.background": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.arrow": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.15)}",
        "scrollbar.start": "",
        # "scrollbar.start": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.25)}",
        "scrollbar.button": f"fg:{cp.bg.more(0.75)} bg:{cp.bg.more(0.75)}",
        "scrollbar.end": f"fg:{cp.bg.more(0.15)} bg:{cp.bg.more(0.75)}",
        # Overflow margin
        "overflow": f"fg:{cp.fg.more(0.5)}",
        # Dialogs
        "dialog title": f"fg:white bg:{cp.hl.darker(0.25)} bold",
        "dialog title border": "fg:ansired",
        "dialog": f"fg:{cp.fg.base} bg:{cp.bg.darker(0.1)}",
        "dialog text-area": f"bg:{cp.bg.lighter(0.05)}",
        "dialog input text text-area": f"fg:default bg:{cp.bg.less(0.1)}",
        "dialog text-area last-line": "nounderline",
        "dialog border": f"fg:{cp.bg.darker(0.1).more(0.1)}",
        # Horizontals rule
        "hr": "fg:ansired",
        # Completions menu
        "completion-menu.completion.keyword": "fg:#d700af",
        "completion-menu.completion.current.keyword": "fg:#fff bg:#d700ff",
        "completion-menu.completion.function": "fg:#005faf",
        "completion-menu.completion.current.function": "fg:#fff bg:#005fff",
        "completion-menu.completion.class": "fg:#008700",
        "completion-menu.completion.current.class": "fg:#fff bg:#00af00",
        "completion-menu.completion.statement": "fg:#5f0000",
        "completion-menu.completion.current.statement": "fg:#fff bg:#5f0000",
        "completion-menu.completion.instance": "fg:#d75f00",
        "completion-menu.completion.current.instance": "fg:#fff bg:#d78700",
        "completion-menu.completion.module": "fg:#d70000",
        "completion-menu.completion.current.module": "fg:#fff bg:#d70000",
        # Log
        "log.level.nonset": "fg:grey",
        "log.level.debug": "fg:green",
        "log.level.info": "fg:blue",
        "log.level.warning": "fg:yellow",
        "log.level.error": "fg:red",
        "log.level.critical": "fg:red bold",
        "log.ref": "fg:grey",
        "log.date": "fg:#00875f",
        # Shortcuts
        "shortcuts.group": f"bg:{cp.bg.more(0.4)} bold underline",
        # "shortcuts.row": f"bg:{cp.bg.base} nobold",
        "shortcuts.row alt": f"bg:{cp.bg.more(0.1)}",
        "shortcuts.row key": "bold",
        # Palette
        "palette.item": f"fg:{cp.fg.more(0.05)} bg:{cp.bg.more(0.05)}",
        "palette.item.alt": f"bg:{cp.bg.more(0.15)}",
        "palette.item.selected": f"fg:{cp.hl.more(1)} bg:{cp.hl}",
        # Pager
        "pager": f"bg:{cp.bg.more(0.05)}",
        "pager.border": f"fg:{cp.bg.more(0.45)}",
        # Markdown
        "html code": f"bg:{cp.bg.more(0.15)}",
        "html code block": f"bg:{cp.bg.less(0.2)}",
        "html pre border": f"fg:{cp.bg.more(0.25)}",
        "html table border": f"fg:{cp.bg.more(0.75)}",
        # Drop-shadow
        "drop-shadow.inner": f"fg:{cp.bg.darker(0.15)}",
        "drop-shadow.outer": f"fg:{cp.bg.darker(0.1)} bg:{cp.bg.darker(0.025)}",
        # Tabbed split
        "tabbed-split tab-bar tab inactive": f"fg:{cp.bg.more(0.1)}",
        "tabbed-split tab-bar tab inactive border": f"fg:{cp.bg.more(0.15)}",
        "tabbed-split tab-bar tab active": f"bold fg:{cp.fg}",
        "tabbed-split tab-bar tab active close": "fg:darkred",
        "tabbed-split border": f"fg:{cp.bg.more(0.2)}",
        # Ipywidgets
        "ipywidget focused": f"bg:{cp.bg.more(0.05)}",
        "ipywidget slider track": f"fg:{cp.fg.darker(0.5)}",
        "ipywidget slider arrow": f"fg:{cp.fg.darker(0.25)}",
        "ipywidget slider handle": f"fg:{cp.fg.darker(0.25)}",
        "ipywidget accordion border default": f"fg:{cp.bg.more(0.2)}",
        # Input widgets
        "text-area selected": "noreverse",
        "text-area selected focused": "reverse",
        # "input focused": f"bg:{cp.bg.more(0.025)}",
        # "input button face": f"fg:default bg:{cp.bg.more(0.05)}",
        # "input button face focused": f"fg:default bg:{cp.hl.darker(0.75)}",
        # "input button border top": "fg:#ffffff",
        # "input button border right": "fg:#606060",
        # "input button border bottom": "fg:#606060",
        # "input button border left": "fg:#ffffff",
        "input button border top": f"fg:{cp.bg.lighter(0.5)}",
        "input button border right": f"fg:{cp.bg.darker(0.25)}",
        "input button border bottom": f"fg:{cp.bg.darker(0.25)}",
        "input button border left": f"fg:{cp.bg.lighter(0.5)}",
        "input button border top focused": f"fg:{cp.hl.lighter(0.5)}",
        "input button border right focused": f"fg:{cp.hl.darker(0.5)}",
        "input button border bottom focused": f"fg:{cp.hl.darker(0.5)}",
        "input button border left focused": f"fg:{cp.hl.lighter(0.5)}",
        "input selection border right": "fg:#ffffff",
        "input selection border bottom": "fg:#ffffff",
        "input selection border top": "fg:#606060",
        "input selection border left": "fg:#606060",
        "input selection focused border right": f"fg:{cp.hl}",
        "input selection focused border bottom": f"fg:{cp.hl}",
        "input selection focused border top": f"fg:{cp.hl.darker(0.5)}",
        "input selection focused border left": f"fg:{cp.hl.darker(0.5)}",
        "input text placeholder": f"fg:{cp.fg.more(0.6)}",
        # "input text border top": "fg:#606060",
        # "input text border right": "fg:#E9E7E3",
        # "input text border bottom": "fg:#E9E7E3",
        # "input text border left": "fg:#606060",
        "input text text-area": f"bg:{cp.bg.lighter(0.1)}",
        "input text border top": f"fg:{cp.bg.darker(0.5)}",
        "input text border right": f"fg:{cp.bg.lighter(0.25)}",
        "input text border bottom": f"fg:{cp.bg.lighter(0.25)}",
        "input text border left": f"fg:{cp.bg.darker(0.5)}",
        "input text border top focused": f"fg:{cp.hl.darker(0.5)}",
        "input text border right focused": f"fg:{cp.hl.lighter(0.5)}",
        "input text border bottom focused": f"fg:{cp.hl.lighter(0.5)}",
        "input text border left focused": f"fg:{cp.hl.darker(0.5)}",
        "input text border top invalid": "fg:ansidarkred",
        "input text border right invalid": "fg:ansired",
        "input text border bottom invalid": "fg:ansired",
        "input text border left invalid": "fg:ansidarkred",
        "radio-buttons prefix selection focused": f"fg:{cp.hl}",
        # Dataframes
        "html table dataframe border": f"fg:{cp.bg.more(0.25)} bg:{cp.bg.more(0.05)}",
        "html table dataframe th": f"bg:{cp.bg.more(0.1)}",
    }

    return Style.from_dict(style_dict)


class ShadowStyle(BaseStyle):
    """Wraps a :py:class:`BaseStyle`, and generates opaque shadow styles for each rule."""

    def __init__(
        self,
        style: "BaseStyle",
        color_palette: "ColorPalette",
        opacity: "float" = 0.5,
        color: "Optional[ColorPaletteColor]" = None,
    ) -> "None":
        """The constructor accepts a style."""
        self.cp = color_palette
        self.color = color or color_palette.bg.darker(0.5)
        self.opacity = opacity
        self.base_style = style
        self._style: "SimpleCache[Hashable, _MergedStyle]" = SimpleCache(maxsize=1)

    @property
    def _merged_style(self) -> "_MergedStyle":
        """The `Style` object that has the other styles merged together."""

        def get() -> "_MergedStyle":
            return merge_styles([self.base_style, Style(self.shadow_rules)])

        return self._style.get(self.base_style.invalidation_hash(), get)

    @property
    def shadow_rules(self) -> "list[tuple[str, str]]":
        """Generate new shadow rules."""
        color = self.color
        opacity = self.opacity

        default_fg = self.cp.fg.towards(self.color, opacity)
        default_bg = self.cp.bg.towards(self.color, opacity)

        new_rules = [("shadow", f"fg:{default_fg} bg:{default_bg}")]
        for rule, style_str in self.base_style.style_rules:
            style_attrs = _parse_style_str(style_str)
            if "shadow" in rule.split():
                continue
            new_style_str = ""
            old_fg = style_attrs.color
            old_bg = style_attrs.bgcolor
            new_fg = (
                ColorPaletteColor(old_fg).towards(color, opacity)
                if old_fg and old_fg not in ("default", "ansidefault")
                else default_fg
            )
            new_bg = (
                ColorPaletteColor(old_bg).towards(color, opacity)
                if old_bg and old_bg not in ("default", "ansidefault")
                else default_bg
            )
            new_style_str += f"fg:{new_fg} bg:{new_bg}"
            new_rules.append((f"{rule} shadow", new_style_str))
        return new_rules

    @property
    def style_rules(self) -> "list[tuple[str, str]]":
        """The list of style rules, used to create this style."""
        return self._merged_style.style_rules

    def get_attrs_for_style_str(
        self, style_str: "str", default: "Attrs" = DEFAULT_ATTRS
    ) -> "Attrs":
        """Return :class:`.Attrs` for the given style string."""
        return self._merged_style.get_attrs_for_style_str(style_str, default)

    def invalidation_hash(self) -> "Hashable":
        """Invalidation hash for the style, which redraws everything on a change."""
        return self.base_style.invalidation_hash()
